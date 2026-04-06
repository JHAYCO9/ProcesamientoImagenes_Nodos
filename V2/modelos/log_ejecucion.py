from datetime import datetime
from comun.enums import NivelLog

class LogEjecucion:
    def __init__(self, id_imagen: int, id_nodo: int,
                 mensaje: str, nivel: NivelLog = NivelLog.INFO):
        self.id_log    = None
        self.id_imagen = id_imagen
        self.id_nodo   = id_nodo
        self.mensaje   = mensaje
        self.nivel     = nivel
        self.timestamp = datetime.now()
