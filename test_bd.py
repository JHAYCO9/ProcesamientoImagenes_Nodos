from config import URL_BD
from sqlalchemy import create_engine, text

engine = create_engine(URL_BD)

try:
    with engine.connect() as conn:
        resultado = conn.execute(text("SHOW TABLES"))
        print("Conexión exitosa. Tablas encontradas:")
        for fila in resultado:
            print(" -", fila[0])
except Exception as e:
    print("Error de conexión:", e)