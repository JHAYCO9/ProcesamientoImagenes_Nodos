import requests
from comun.enums import EstadoImagen, NivelLog


class ClienteREST_BD:
    """
    Todas las escrituras van a la API REST del servidor BD.
    """

    def __init__(self, url_bd: str):
        self.base_url = url_bd.rstrip("/")

    # ── Logs ──────────────────────────────────────────────────

    def guardar_log(self, log) -> None:
        try:
            requests.post(f"{self.base_url}/api/logs", json={
                "id_imagen": log.id_imagen,
                "id_nodo":   log.id_nodo,
                "mensaje":   log.mensaje,
                "nivel":     log.nivel.value,
                "timestamp": log.timestamp.isoformat()
            }, timeout=5)
        except Exception as e:
            print(f"[ClienteREST_BD] Error guardando log: {e}")

    # ── Transformaciones ──────────────────────────────────────

    def guardar_transformacion(self, t) -> None:
        try:
            r = requests.post(f"{self.base_url}/api/transformaciones", json={
                "id_imagen":  t.id_imagen,
                "tipo":       t.tipo.value,
                "parametros": str(t.parametros),
                "orden":      t.orden,
                "estado":     t.estado.value
            }, timeout=5)
            data = r.json()
            if "id_transformacion" in data:
                t.id_transformacion = data["id_transformacion"]
        except Exception as e:
            print(f"[ClienteREST_BD] Error guardando transformacion: {e}")

    def actualizar_transformacion(self, t) -> None:
        if not t.id_transformacion:
            return
        try:
            requests.put(
                f"{self.base_url}/api/transformaciones/{t.id_transformacion}",
                json={
                    "estado":          t.estado.value,
                    "fecha_ejecucion": t.fecha_ejecucion.isoformat() if t.fecha_ejecucion else None
                },
                timeout=5
            )
        except Exception as e:
            print(f"[ClienteREST_BD] Error actualizando transformacion: {e}")

    # ── Imagenes ──────────────────────────────────────────────

    def actualizar_imagen(self, id_imagen: int, ruta_resultado: str,
                          formato: str, estado: EstadoImagen,
                          id_nodo: int = None) -> None:
        """
        Actualiza el estado, ruta y formato resultado de una imagen.
        Si id_nodo se proporciona, también registra qué nodo realizó el procesamiento
        y actualiza la fecha de conversión.
        Al completarse (LISTO), incrementa imagenes_completadas del lote.
        """
        try:
            payload = {
                "estado":            estado.value,
                "ruta_resultado":    ruta_resultado,
                "formato_resultado": formato,
            }
            if id_nodo is not None:
                payload["id_nodo"] = id_nodo

            requests.put(f"{self.base_url}/api/imagenes/{id_imagen}",
                         json=payload, timeout=5)

            # Si la imagen quedó LISTO o ERROR, incrementar contador del lote
            if estado in (EstadoImagen.LISTO, EstadoImagen.ERROR):
                self._incrementar_completadas(id_imagen)

        except Exception as e:
            print(f"[ClienteREST_BD] Error actualizando imagen: {e}")

    def _incrementar_completadas(self, id_imagen: int) -> None:
        """Obtiene el id_lote de la imagen y llama al endpoint de incremento."""
        try:
            r = requests.get(f"{self.base_url}/api/imagenes/{id_imagen}", timeout=5)
            if r.status_code == 200:
                id_lote = r.json().get("id_lote")
                if id_lote:
                    requests.post(
                        f"{self.base_url}/api/lotes/{id_lote}/incrementar_completadas",
                        timeout=5
                    )
        except Exception as e:
            print(f"[ClienteREST_BD] Error incrementando completadas: {e}")

    # ── Nodos ─────────────────────────────────────────────────

    def registrar_nodo(self, identificador: str, direccion_red: str, puerto: int) -> dict:
        try:
            r = requests.post(f"{self.base_url}/api/nodos", json={
                "nombre":           identificador,
                "direccion_ip":     direccion_red,
                "puerto":           puerto,
                "capacidad_maxima": 10
            }, timeout=5)

            if r.status_code not in (200, 201):
                print(f"[ClienteREST_BD] Servidor BD respondió con status {r.status_code}: {r.text[:200]}")
                return {}

            if not r.text.strip():
                print(f"[ClienteREST_BD] Servidor BD respondió vacío al registrar nodo")
                return {}

            return r.json()
        except requests.exceptions.ConnectionError:
            print(f"[ClienteREST_BD] No se pudo conectar al servidor BD en {self.base_url}")
            return {}
        except Exception as e:
            print(f"[ClienteREST_BD] Error registrando nodo: {e}")
            return {}

    def actualizar_estado_nodo(self, id_nodo: int, estado: str) -> None:
        try:
            requests.put(f"{self.base_url}/api/nodos/{id_nodo}/estado",
                         json={"estado": estado}, timeout=5)
        except Exception as e:
            print(f"[ClienteREST_BD] Error actualizando estado nodo: {e}")

    def enviar_heartbeat(self, id_nodo: int) -> None:
        self.actualizar_estado_nodo(id_nodo, "ACTIVO")