from comun.enums import TipoTransformacion, EstadoImagen

class Transformacion:

    def __init__(self, id_imagen: int, tipo: str,
                 parametros: dict, orden: int):
        self.id_transformacion = None
        self.id_imagen         = id_imagen
        self.tipo              = TipoTransformacion(tipo)
        self.parametros        = parametros
        self.orden             = orden
        self.estado            = EstadoImagen.PENDIENTE
        self.fecha_ejecucion   = None

    def get_tipo_enum(self) -> TipoTransformacion:
        return self.tipo

    def get_descripcion(self) -> str:
        return f"{self.tipo.value} — params: {self.parametros}"
