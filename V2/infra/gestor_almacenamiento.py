import os
import uuid


class GestorAlmacenamiento:
    """
    Gestiona la lectura/escritura de imágenes en disco local del nodo.
    """

    def __init__(self, ruta_base: str = "almacenamiento"):
        self.ruta_base = ruta_base
        os.makedirs(ruta_base, exist_ok=True)

    def guardar_imagen(self, id_imagen: int, datos: bytes) -> str:
        """Guarda bytes de imagen y retorna la ruta donde quedó."""
        ruta = os.path.join(self.ruta_base, f"img_{id_imagen}_{uuid.uuid4().hex[:6]}.bin")
        with open(ruta, "wb") as f:
            f.write(datos)
        return ruta

    def leer_imagen(self, ruta: str) -> bytes:
        with open(ruta, "rb") as f:
            return f.read()

    def eliminar_imagen(self, ruta: str) -> None:
        if os.path.exists(ruta):
            os.remove(ruta)

    def existe(self, ruta: str) -> bool:
        return os.path.exists(ruta)

    def get_ruta_resultado(self, id_imagen: int, formato: str) -> str:
        """Genera la ruta donde se guardará el resultado procesado."""
        ext = formato.lower().lstrip(".")
        return os.path.join(self.ruta_base, f"resultado_{id_imagen}_{uuid.uuid4().hex[:8]}.{ext}")
