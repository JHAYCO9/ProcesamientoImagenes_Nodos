import Pyro5.server
from config import URL_BD, HOST, PUERTO_PYRO5, IDENTIFICADOR, MAX_HILOS
from repositorio.gestor_bd import GestorBD
from modelos.nodo import Nodo
from servicios.nodo_procesador import NodoProcesador

def main():
    gestor_bd = GestorBD(URL_BD)
    gestor_bd.crear_tablas()

    info_nodo = Nodo(
        id_nodo       = 1,
        identificador = IDENTIFICADOR,
        direccion_red = HOST,
        puerto_pyro5  = PUERTO_PYRO5
    )

    procesador = NodoProcesador(
        info_nodo = info_nodo,
        gestor_bd = gestor_bd,
        max_hilos = MAX_HILOS
    )

    daemon = Pyro5.server.Daemon(host="localhost", port=PUERTO_PYRO5)
    uri    = daemon.register(procesador, objectId="nodo_procesador")

    print(f"[Nodo] {IDENTIFICADOR} escuchando en {uri}")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("[Nodo] Apagado.")
        daemon.close()

if __name__ == "__main__":
    main()
