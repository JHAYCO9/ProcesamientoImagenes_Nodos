from comun.enums import EstadoNodo

class Nodo:

    def __init__(self, id_nodo: int, identificador: str,
                 direccion_red: str, puerto_pyro5: int):
        self.id_nodo          = id_nodo
        self.identificador    = identificador
        self.direccion_red    = direccion_red
        self.puerto_pyro5     = puerto_pyro5
        self.estado           = EstadoNodo.ACTIVO
        self.trabajos_activos = 0

    def esta_disponible(self) -> bool:
        return self.estado == EstadoNodo.ACTIVO and self.trabajos_activos < 5

    def incrementar_trabajo(self) -> None:
        self.trabajos_activos += 1

    def decrementar_trabajo(self) -> None:
        if self.trabajos_activos > 0:
            self.trabajos_activos -= 1
