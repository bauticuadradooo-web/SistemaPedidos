from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Jornada


def jornada_actual(db: Session) -> Jornada:
    """Devuelve la jornada abierta; si no hay ninguna, abre la siguiente fecha."""
    jornada = (
        db.query(Jornada)
        .filter(Jornada.cerrada_en.is_(None))
        .order_by(Jornada.id.desc())
        .first()
    )
    if jornada:
        return jornada

    ultima = db.query(Jornada).order_by(Jornada.id.desc()).first()
    fecha = ultima.fecha + timedelta(days=1) if ultima else date.today()
    jornada = Jornada(fecha=fecha, iniciada_en=datetime.now())
    db.add(jornada)
    db.flush()
    return jornada
