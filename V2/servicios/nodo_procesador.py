import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

import Pyro5.api
import Pyro5.server

from interfaces.i_nodo_procesador import INodoProcesador
from infra.cliente_rest_bd import ClienteREST_BD
from infra.gestor_almacenamiento import GestorAlmacenamiento
from modelos.nodo import Nodo
from modelos.transformacion import Transformacion
from modelos.log_ejecucion import LogEjecucion
from comun.enums import TipoTransformacion, EstadoImagen, NivelLog


@Pyro5.server.expose
class NodoProcesador(INodoProcesador):

    def __init__(self, info_nodo: Nodo, cliente_bd: ClienteREST_BD,
                 almacenamiento: GestorAlmacenamiento,
                 max_hilos: int = 4, parametros: dict = None,
                 servidor_uri: str = "PYRO:servidor_aplicacion@localhost:9091"):
        self.info_nodo            = info_nodo
        self.cliente_bd           = cliente_bd
        self.almacenamiento       = almacenamiento
        self.max_hilos            = max_hilos
        self.parametros           = parametros or {}
        self.servidor_uri         = servidor_uri
        self.executor             = ThreadPoolExecutor(max_workers=max_hilos)
        self._trabajos_pendientes = 0

    # ── INodoProcesador ───────────────────────────────────────

    def procesar_imagen(self, id_imagen: int, ruta_original: str, transformaciones_json: str) -> str:
        """
        transformaciones_json: JSON string de lista de dicts {tipo, parametros, orden}.
        Se recibe como string para evitar problemas de serialización de Pyro5/serpent con dicts.
        """
        import json
        if isinstance(transformaciones_json, str):
            try:
                transformaciones = json.loads(transformaciones_json)
            except Exception:
                transformaciones = []
        elif isinstance(transformaciones_json, list):
            # Compatibilidad: lista de strings
            transformaciones = [
                {"tipo": t, "parametros": {}, "orden": i}
                for i, t in enumerate(transformaciones_json)
            ]
        else:
            transformaciones = []

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
            print(f"[Nodo] Procesando imagen {id_imagen} — ruta: '{ruta_original}'")
            print(f"[Nodo] ¿Existe el archivo? {os.path.exists(ruta_original)}")

            img = Image.open(ruta_original)

            for i, entrada in enumerate(transformaciones):
                # Aceptar tanto strings como dicts
                if isinstance(entrada, dict):
                    tipo_str   = entrada.get("tipo", "")
                    parametros = entrada.get("parametros", {})
                    orden      = entrada.get("orden", i)
                else:
                    tipo_str   = entrada
                    parametros = {}
                    orden      = i

                print(f"[Nodo] Aplicando transformación [{orden}]: {tipo_str}")

                t = Transformacion(id_imagen, tipo_str, parametros, orden)
                t.estado = EstadoImagen.PROCESANDO
                self.cliente_bd.guardar_transformacion(t)

                img = self._aplicar(img, t)

                t.estado          = EstadoImagen.LISTO
                t.fecha_ejecucion = datetime.now()
                self.cliente_bd.actualizar_transformacion(t)
                self._reportar_log(id_imagen, f"Transformación {t.tipo.value} OK", NivelLog.INFO)

            # Guardar resultado
            ruta_salida   = self.almacenamiento.get_ruta_resultado(id_imagen, "PNG")
            img.save(ruta_salida)

            # Guardar ruta ABSOLUTA para que el servidor pueda encontrarla
            ruta_absoluta = os.path.abspath(ruta_salida)
            self.cliente_bd.actualizar_imagen(
                id_imagen, ruta_absoluta, img.format or "PNG", EstadoImagen.LISTO,
                id_nodo=self.info_nodo.id_nodo
            )

            # Notificar al servidor que la imagen finalizó
            self._notificar_imagen_completada(id_imagen)

            print(f"[Nodo] Imagen {id_imagen} completada → {ruta_salida}")
            return ruta_salida

        except Exception as e:
            self._reportar_log(id_imagen, f"Error: {e}", NivelLog.ERROR)
            self.cliente_bd.actualizar_imagen(
                id_imagen, "", "PNG", EstadoImagen.ERROR,
                id_nodo=self.info_nodo.id_nodo
            )
            raise
        finally:
            self.info_nodo.decrementar_trabajo()
            self._trabajos_pendientes -= 1

    def _notificar_imagen_completada(self, id_imagen: int) -> None:
        """
        Intenta notificar al servidor vía Pyro5.
        Si falla (el servidor no implementa imagen_completada o no está disponible),
        simplemente lo registra en log — no interrumpe el flujo.
        """
        try:
            print(f"[Nodo] Notificando servidor: imagen {id_imagen} completada")
            with Pyro5.api.Proxy(self.servidor_uri) as srv:
                srv.imagen_completada(id_imagen)
        except Exception as e:
            print(f"[Nodo] Notificación al servidor omitida (no crítico): {e}")

    # ── Aplicar transformación ────────────────────────────────

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

    def _a_grises(self, img):              return img.convert("L")
    def _redimensionar(self, img, w, h):   return img.resize((w, h), Image.LANCZOS)
    def _rotar(self, img, ang):            return img.rotate(ang, expand=True)
    def _reflejar(self, img, horiz):       return img.transpose(Image.FLIP_LEFT_RIGHT if horiz else Image.FLIP_TOP_BOTTOM)
    def _desenfocar(self, img, radio):     return img.filter(ImageFilter.GaussianBlur(radius=radio))
    def _perfilar(self, img):              return img.filter(ImageFilter.SHARPEN)
    def _brillo_contraste(self, img, b, c):
        img = ImageEnhance.Brightness(img).enhance(b)
        return ImageEnhance.Contrast(img).enhance(c)
    def _recortar(self, img, x, y, w, h):  return img.crop((x, y, x + w, y + h))
    def _marca_agua(self, img, texto, fuente, tam):
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(fuente, tam) if fuente else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        draw.text((10, 10), texto, fill=(255, 255, 255, 128), font=font)
        return img
    def _convertir_formato(self, img, formato, ruta_salida):
        if ruta_salida:
            img.save(ruta_salida, format=formato)
        return img

    # ── Utilidades ────────────────────────────────────────────

    def _reportar_log(self, id_imagen: int, msg: str, nivel: NivelLog) -> None:
        log = LogEjecucion(id_imagen, self.info_nodo.id_nodo, msg, nivel)
        self.cliente_bd.guardar_log(log)