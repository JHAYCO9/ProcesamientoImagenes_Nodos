import subprocess
import sys
import os
import time
import signal
import shutil

NODOS = [
    {"env": "nodo_1.env", "nombre": "nodo_1"},
    {"env": "nodo_2.env", "nombre": "nodo_2"},
    {"env": "nodo_3.env", "nombre": "nodo_3"},
]

procesos = []


def iniciar_nodos():
    python = shutil.which("python") or shutil.which("python3") or sys.executable
    script = os.path.join(os.path.dirname(__file__), "main.py")

    for cfg in NODOS:
        env_path = os.path.join(os.path.dirname(__file__), cfg["env"])
        if not os.path.exists(env_path):
            print(f"⚠️  No se encontró {cfg['env']} — cópialo desde .env.ejemplo")
            continue

        # Cada nodo hereda el entorno del sistema + su propio .env
        env = os.environ.copy()
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

        proc = subprocess.Popen(
            [python, script],
            env=env,
            cwd=os.path.dirname(__file__)
        )
        procesos.append((cfg["nombre"], proc))
        print(f"✅ {cfg['nombre']} iniciado (PID {proc.pid})")
        time.sleep(0.5)   # pequeña pausa para que no colisionen al arrancar

    print(f"\n🚀 {len(procesos)} nodos corriendo. Presiona Ctrl+C para detener todos.\n")

    def apagar(sig, frame):
        print("\n🛑 Apagando nodos...")
        for nombre, proc in procesos:
            proc.terminate()
            print(f"   {nombre} detenido")
        sys.exit(0)

    signal.signal(signal.SIGINT, apagar)
    signal.signal(signal.SIGTERM, apagar)

    # Monitorear que sigan vivos
    while True:
        time.sleep(5)
        for nombre, proc in procesos:
            if proc.poll() is not None:
                print(f"⚠️  {nombre} se detuvo inesperadamente (código {proc.returncode})")


if __name__ == "__main__":
    iniciar_nodos()
