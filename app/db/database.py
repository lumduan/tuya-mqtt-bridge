"""
app/db/database.py
SQLite database engine, session factory, and CRUD helpers.
"""
import logging
from contextlib import contextmanager
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.models import Base, Device
from app.config import config

logger = logging.getLogger(__name__)

# ── Engine & Session ──────────────────────────────────────────────────────────
engine = create_engine(
    f"sqlite:///{config.db_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", config.db_path)


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_all_devices() -> list[Device]:
    with get_session() as s:
        return s.query(Device).all()


def get_device(device_id: str) -> Optional[Device]:
    with get_session() as s:
        return s.query(Device).filter(Device.device_id == device_id).first()


def add_device(
    device_id: str,
    name: str,
    ip: str,
    key: str,
    version: float = 3.3,
    persist: bool = True,
) -> Device:
    with get_session() as s:
        device = Device(
            device_id=device_id,
            name=name,
            ip=ip,
            key=key,
            version=version,
            persist=persist,
        )
        s.add(device)
        logger.info("Added device: %s (%s)", name, device_id)
        return device


def update_device(device_id: str, **kwargs) -> Optional[Device]:
    with get_session() as s:
        device = s.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return None
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        logger.info("Updated device %s: %s", device_id, kwargs)
        return device


def delete_device(device_id: str) -> bool:
    with get_session() as s:
        device = s.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return False
        s.delete(device)
        logger.info("Deleted device %s", device_id)
        return True


def update_device_status(device_id: str, is_online: bool, status_json: str = None):
    """Called by the bridge to update runtime state."""
    from datetime import datetime
    with get_session() as s:
        device = s.query(Device).filter(Device.device_id == device_id).first()
        if device:
            device.is_online = is_online
            device.last_seen = datetime.utcnow() if is_online else device.last_seen
            if status_json:
                device.last_status = status_json
