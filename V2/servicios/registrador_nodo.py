import threading
import time
from infra.cliente_rest_bd import ClienteREST_BD
from modelos.nodo import Nodo


class RegistradorNodo:
    """
    Al iniciar se registra en el servidor BD via REST.
    Envía heartbeat periódico para mantener el nodo como ACTIVO.
    """

    INTERVALO_HEARTBEAT = 30  # segundos

    def __init__(self, cliente_bd: ClienteREST_BD, info_nodo: Nodo):
        self.cliente_bd  = cliente_bd
        self.info_nodo   = info_nodo
        self._hilo_hb    = None
        self._activo     = False

    def registrar(self) -> bool:
        """Registra el nodo en la BD y guarda el id_nodo asignado."""
        try:
            data = self.cliente_bd.registrar_nodo(
                identificador = self.info_nodo.identificador,
                direccion_red = self.info_nodo.direccion_red,
                puerto        = self.info_nodo.puerto_pyro5
            )
            if data and "id_nodo" in data:
                self.info_nodo.id_nodo = data["id_nodo"]
                print(f"[RegistradorNodo] Registrado con id_nodo={self.info_nodo.id_nodo}")
            else:
                print(f"[RegistradorNodo] Registrado (sin id en respuesta), usando id local")

            # arrancar heartbeat
            self._activo  = True
            self._hilo_hb = threading.Thread(target=self._loop_heartbeat, daemon=True)
            self._hilo_hb.start()
            return True
        except Exception as e:
            print(f"[RegistradorNodo] Error al registrar: {e}")
            return False

    def desregistrar(self) -> None:
        self._activo = False
        self.cliente_bd.actualizar_estado_nodo(self.info_nodo.id_nodo, "INACTIVO")
        print("[RegistradorNodo] Nodo marcado como INACTIVO")

    def enviar_heartbeat(self) -> None:
        self.cliente_bd.enviar_heartbeat(self.info_nodo.id_nodo)

    def _loop_heartbeat(self) -> None:
        while self._activo:
            time.sleep(self.INTERVALO_HEARTBEAT)
            try:
                self.enviar_heartbeat()
                print(f"[RegistradorNodo] Heartbeat enviado")
            except Exception as e:
                print(f"[RegistradorNodo] Error en heartbeat: {e}")
