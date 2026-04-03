import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

from interfaces.i_nodo_procesador import INodoProcesador
from repositorio.gestor_bd import GestorBD
from modelos.nodo import Nodo
from modelos.transformacion import Transformacion
from modelos.log_ejecucion import LogEjecucion
from comun.enums import TipoTransformacion, EstadoImagen, NivelLog

import Pyro5.api
import Pyro5.server

@Pyro5.server.expose
class NodoProcesador(INodoProcesador):

    def __init__(self, info_nodo: Nodo, gestor_bd: GestorBD,
                 max_hilos: int = 4, parametros: dict = None):
        self.info_nodo            = info_nodo
        self.gestor_bd            = gestor_bd
        self.max_hilos            = max_hilos
        self.parametros           = parametros or {}
        self.executor             = ThreadPoolExecutor(max_workers=max_hilos)
        self._trabajos_pendientes = 0
        # URI del servidor (ajusta el puerto si es diferente)
        self.servidor_uri = "PYRO:servidor_aplicacion@localhost:9091"

    # ── INodoProcesador ───────────────────────────────────────

    def procesar_imagen(self, id_imagen: int, ruta_original: str, transformaciones: list) -> str:
        self.info_nodo.incrementar_trabajo()
        self._trabajos_pendientes += 1
        future = self.executor.submit(
            self._ejecutar_pipeline, id_imagen, ruta_original, transformaciones
        )
        return future.result()

    def ping(self) -> bool:
        return True

    def get_estado(self) -> dict:
        return {
            "id_nodo":          self.info_nodo.id_nodo,
            "identificador":    self.info_nodo.identificador,
            "estado":           self.info_nodo.estado.value,
            "trabajos_activos": self.info_nodo.trabajos_activos,
            "max_hilos":        self.max_hilos
        }

    def get_trabajos_pendientes(self) -> int:
        return self._trabajos_pendientes

    # ── Pipeline interno ──────────────────────────────────────

    def _ejecutar_pipeline(self, id_imagen: int, ruta_original: str, transformaciones: list) -> str:
        try:
            from comun.enums import TipoTransformacion, EstadoImagen, NivelLog
            
            print(f"[Nodo] Recibida ruta: '{ruta_original}'")
            print(f"[Nodo] ¿Existe el archivo? {os.path.exists(ruta_original)}")
            print(f"[Nodo] Transformaciones recibidas: {transformaciones}")
            
            img = Image.open(ruta_original)
            
            for i, tipo_str in enumerate(transformaciones):
                print(f"[Nodo] Procesando transformación: {tipo_str}")
                
                # Convertir string a enum
                tipo_enum = TipoTransformacion(tipo_str)
                
                # Crear objeto Transformacion con el enum
                t = Transformacion(id_imagen, tipo_enum, {}, i)
                t.estado = EstadoImagen.PROCESANDO
                self.gestor_bd.guardar_transformacion(t)
                
                # Aplicar la transformación
                img = self._aplicar(img, t)
                
                t.estado = EstadoImagen.LISTO
                t.fecha_ejecucion = datetime.now()
                self.gestor_bd.actualizar_transformacion(t)
                self._reportar_log(id_imagen, f"Transformación {t.tipo.value} OK", NivelLog.INFO)
            
            ruta_salida = self._ruta_salida(ruta_original)
            img.save(ruta_salida)
            self.gestor_bd.actualizar_imagen(id_imagen, ruta_salida, img.format or "PNG", EstadoImagen.LISTO)
            
            # ✅ NOTIFICAR AL SERVIDOR QUE ESTA IMAGEN SE COMPLETÓ
            self._notificar_imagen_completada(id_imagen)
            
            return ruta_salida
        
        except Exception as e:
            self._reportar_log(id_imagen, f"Error: {e}", NivelLog.ERROR)
            raise
        finally:
            self.info_nodo.decrementar_trabajo()
            self._trabajos_pendientes -= 1

    # ✅ NUEVO MÉTODO: Notificar al servidor que una imagen terminó
    def _notificar_imagen_completada(self, id_imagen: int) -> None:
        try:
            print(f"[Nodo] Notificando al servidor: imagen {id_imagen} completada")
            with Pyro5.api.Proxy(self.servidor_uri) as servidor:
                servidor.imagen_completada(id_imagen)
            print(f"[Nodo] Notificación enviada correctamente")
        except Exception as e:
            print(f"[Nodo] Error al notificar al servidor: {e}")

    def _aplicar(self, img: Image.Image, t: Transformacion) -> Image.Image:
        tipo = t.get_tipo_enum()
        p    = t.parametros
        acciones = {
            TipoTransformacion.GRISES:             lambda: self._a_grises(img),
            TipoTransformacion.REDIMENSIONAR:      lambda: self._redimensionar(img, p.get("ancho", 800), p.get("alto", 600)),
            TipoTransformacion.ROTAR:              lambda: self._rotar(img, p.get("angulo", 90)),
            TipoTransformacion.REFLEJAR:           lambda: self._reflejar(img, p.get("horizontal", True)),
            TipoTransformacion.DESENFOCAR:         lambda: self._desenfocar(img, p.get("radio", 2)),
            TipoTransformacion.PERFILAR:           lambda: self._perfilar(img),
            TipoTransformacion.BRILLO_CONTRASTE:   lambda: self._brillo_contraste(img, p.get("brillo", 1.0), p.get("contraste", 1.0)),
            TipoTransformacion.RECORTAR:           lambda: self._recortar(img, p.get("x", 0), p.get("y", 0), p.get("w", 100), p.get("h", 100)),
            TipoTransformacion.MARCA_AGUA:         lambda: self._marca_agua(img, p.get("texto", ""), p.get("fuente", None), p.get("tam", 24)),
            TipoTransformacion.CONVERSION_FORMATO: lambda: self._convertir_formato(img, p.get("formato", "PNG"), p.get("ruta_salida", "")),
        }
        return acciones.get(tipo, lambda: img)()

    # ── Transformaciones Pillow ────────────────────────────────

    def _a_grises(self, img: Image.Image) -> Image.Image:
        return img.convert("L")

    def _redimensionar(self, img: Image.Image, ancho: int, alto: int) -> Image.Image:
        return img.resize((ancho, alto), Image.LANCZOS)

    def _rotar(self, img: Image.Image, angulo: float) -> Image.Image:
        return img.rotate(angulo, expand=True)

    def _reflejar(self, img: Image.Image, horizontal: bool) -> Image.Image:
        return img.transpose(Image.FLIP_LEFT_RIGHT if horizontal else Image.FLIP_TOP_BOTTOM)

    def _desenfocar(self, img: Image.Image, radio: int) -> Image.Image:
        return img.filter(ImageFilter.GaussianBlur(radius=radio))

    def _perfilar(self, img: Image.Image) -> Image.Image:
        return img.filter(ImageFilter.SHARPEN)

    def _brillo_contraste(self, img: Image.Image, brillo: float, contraste: float) -> Image.Image:
        img = ImageEnhance.Brightness(img).enhance(brillo)
        return ImageEnhance.Contrast(img).enhance(contraste)

    def _recortar(self, img: Image.Image, x: int, y: int, w: int, h: int) -> Image.Image:
        return img.crop((x, y, x + w, y + h))

    def _marca_agua(self, img: Image.Image, texto: str, fuente, tam: int) -> Image.Image:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(fuente, tam) if fuente else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        draw.text((10, 10), texto, fill=(255, 255, 255, 128), font=font)
        return img

    def _convertir_formato(self, img: Image.Image, formato: str, ruta_salida: str) -> Image.Image:
        if ruta_salida:
            img.save(ruta_salida, format=formato)
        return img

    # ── Utilidades ────────────────────────────────────────────

    def _ruta_salida(self, ruta_original: str) -> str:
        directorio = os.path.dirname(ruta_original)
        nombre     = f"resultado_{uuid.uuid4().hex[:8]}.png"
        return os.path.join(directorio, nombre)

    def _reportar_log(self, id_imagen: int, msg: str, nivel: NivelLog) -> None:
        log = LogEjecucion(id_imagen, self.info_nodo.id_nodo, msg, nivel)
        self.gestor_bd.guardar_log(log)