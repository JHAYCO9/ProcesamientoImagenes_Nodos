from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from datetime import datetime
from comun.enums import NivelLog, EstadoImagen, TipoTransformacion
from modelos.log_ejecucion import LogEjecucion
from modelos.transformacion import Transformacion

class Base(DeclarativeBase):
    pass

class LogEjecucionORM(Base):
    __tablename__ = "logs_ejecucion"
    id_log    = Column(Integer, primary_key=True, autoincrement=True)
    id_imagen = Column(Integer, nullable=False)
    id_nodo   = Column(Integer, nullable=True)
    mensaje   = Column(String,  nullable=False)
    nivel     = Column(SAEnum(NivelLog), default=NivelLog.INFO)
    timestamp = Column(DateTime, default=datetime.now)

class TransformacionORM(Base):
    __tablename__ = "transformaciones"
    id_transformacion = Column(Integer, primary_key=True, autoincrement=True)
    id_imagen         = Column(Integer, nullable=False)
    tipo              = Column(SAEnum(TipoTransformacion), nullable=False)
    parametros        = Column(String, nullable=True)
    orden             = Column(Integer, nullable=False)
    estado            = Column(SAEnum(EstadoImagen), default=EstadoImagen.PENDIENTE)
    fecha_ejecucion   = Column(DateTime, nullable=True)

class ImagenEstadoORM(Base):
    __tablename__ = "imagenes"
    id_imagen         = Column(Integer, primary_key=True)
    estado            = Column(SAEnum(EstadoImagen), default=EstadoImagen.PENDIENTE)
    ruta_resultado    = Column(String, nullable=True)
    formato_resultado = Column(String, nullable=True)
    fecha_conversion  = Column(DateTime, nullable=True)

class SolicitudLoteEstadoORM(Base):
    __tablename__ = "solicitudes_lote"
    id_lote = Column(Integer, primary_key=True)
    estado  = Column(String, nullable=True)

class GestorBD:

    def __init__(self, url_bd: str):
        self.url_bd  = url_bd
        self.engine  = create_engine(url_bd, echo=False)
        self.Session = sessionmaker(bind=self.engine)

    def crear_tablas(self) -> None:
        Base.metadata.create_all(self.engine)

    def guardar_log(self, log: LogEjecucion) -> None:
        with self.Session() as session:
            orm = LogEjecucionORM(
                id_imagen = log.id_imagen,
                id_nodo   = log.id_nodo,
                mensaje   = log.mensaje,
                nivel     = log.nivel,
                timestamp = log.timestamp
            )
            session.add(orm)
            session.commit()

    def guardar_transformacion(self, t: Transformacion) -> None:
        with self.Session() as session:
            orm = TransformacionORM(
                id_imagen       = t.id_imagen,
                tipo            = t.tipo,
                parametros      = str(t.parametros),
                orden           = t.orden,
                estado          = t.estado,
                fecha_ejecucion = t.fecha_ejecucion
            )
            session.add(orm)
            session.commit()

    def actualizar_transformacion(self, t: Transformacion) -> None:
        with self.Session() as session:
            session.query(TransformacionORM).filter_by(
                id_transformacion=t.id_transformacion
            ).update({"estado": t.estado, "fecha_ejecucion": t.fecha_ejecucion})
            session.commit()

    def actualizar_imagen(self, id_imagen: int, ruta_resultado: str,
                          formato: str, estado: EstadoImagen) -> None:
        with self.Session() as session:
            session.query(ImagenEstadoORM).filter_by(id_imagen=id_imagen).update({
                "estado":            estado,
                "ruta_resultado":    ruta_resultado,
                "formato_resultado": formato,
                "fecha_conversion":  datetime.now()
            })
            session.commit()

    def actualizar_estado_lote(self, id_lote: int, estado: str) -> None:
        with self.Session() as session:
            session.query(SolicitudLoteEstadoORM).filter_by(id_lote=id_lote).update(
                {"estado": estado}
            )
            session.commit()
