from abc import ABC, abstractmethod

class INodoProcesador(ABC):

    @abstractmethod
    def procesar_imagen(self, ruta_original: str, transformaciones: list) -> str:
        pass

    @abstractmethod
    def ping(self) -> bool:
        pass

    @abstractmethod
    def get_estado(self) -> dict:
        pass

    @abstractmethod
    def get_trabajos_pendientes(self) -> int:
        pass
