from enum import Enum

class TipoTransformacion(Enum):
    GRISES             = "GRISES"
    REDIMENSIONAR      = "REDIMENSIONAR"
    RECORTAR           = "RECORTAR"
    ROTAR              = "ROTAR"
    REFLEJAR           = "REFLEJAR"
    DESENFOCAR         = "DESENFOCAR"
    PERFILAR           = "PERFILAR"
    BRILLO_CONTRASTE   = "BRILLO_CONTRASTE"
    MARCA_AGUA         = "MARCA_AGUA"
    CONVERSION_FORMATO = "CONVERSION_FORMATO"

class EstadoImagen(Enum):
    PENDIENTE  = "PENDIENTE"
    PROCESANDO = "PROCESANDO"
    LISTO      = "LISTO"
    ERROR      = "ERROR"

class EstadoNodo(Enum):
    ACTIVO   = "ACTIVO"
    INACTIVO = "INACTIVO"
    ERROR    = "ERROR"

class NivelLog(Enum):
    INFO  = "INFO"
    WARN  = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
