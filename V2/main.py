import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import Pyro5.server
from config import URL_BD, HOST, PUERTO_PYRO5, IDENTIFICADOR, MAX_HILOS, SERVIDOR_URI

from infra.cliente_rest_bd import ClienteREST_BD
from infra.gestor_almacenamiento import GestorAlmacenamiento
from modelos.nodo import Nodo
from servicios.nodo_procesador import NodoProcesador
from servicios.registrador_nodo import RegistradorNodo


def main():
    print(f"=== Nodo Procesador: {IDENTIFICADOR} ===")

    # 1. Infraestructura
    cliente_bd      = ClienteREST_BD(URL_BD)
    almacenamiento  = GestorAlmacenamiento(ruta_base="almacenamiento")

    # 2. Info del nodo (id_nodo se actualizará tras registro)
    info_nodo = Nodo(
        id_nodo       = 0,
        identificador = IDENTIFICADOR,
        direccion_red = HOST,
        puerto_pyro5  = PUERTO_PYRO5
    )

    # 3. Registrar nodo en la BD
    registrador = RegistradorNodo(cliente_bd, info_nodo)
    registrador.registrar()

    # 4. Crear procesador
    procesador = NodoProcesador(
        info_nodo      = info_nodo,
        cliente_bd     = cliente_bd,
        almacenamiento = almacenamiento,
        max_hilos      = MAX_HILOS,
        servidor_uri   = SERVIDOR_URI
    )

    # 5. Exponer via Pyro5
    daemon = Pyro5.server.Daemon(host=HOST, port=PUERTO_PYRO5)
    uri    = daemon.register(procesador, objectId="nodo_procesador")

    print(f"[Nodo] Escuchando en {uri}")
    print("[Nodo] Presiona Ctrl+C para detener")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\n[Nodo] Apagando...")
        registrador.desregistrar()
        daemon.close()
        print("[Nodo] Apagado.")


if __name__ == "__main__":
    main()

