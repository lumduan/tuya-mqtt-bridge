"""
app/db/database.py
SQLite database engine, session factory, and CRUD helpers.
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session

from app.db.models import Base, Device
from app.config import config

logger = logging.getLogger(__name__)

# ── Engine & Session ──────────────────────────────────────────────────────────
DB_PATH = Path(config.db_path).expanduser()

try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except OSError as exc:  # pragma: no cover - depends on the host filesystem
    raise RuntimeError(
        f"Cannot create the directory for DB_PATH={DB_PATH}: {exc}. "
        f"This process runs as uid {os.getuid()}. If DB_PATH is inside a bind-mounted "
        f"volume, note that `docker compose up` creates a missing host directory owned "
        f"by root, which this uid cannot write to."
    ) from exc

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

# expire_on_commit=False is required, not a preference. get_session() commits and
# closes on exit, so with the default True every object returned by the helpers
# below would be expired AND detached, and the first attribute access in the UI
# would raise DetachedInstanceError.
SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def init_db():
    """Create all tables if they don't exist. Idempotent — safe to call repeatedly."""
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        raise RuntimeError(
            f"Cannot create the database schema at {DB_PATH}: {exc}. "
            f"This process runs as uid {os.getuid()} and needs write access to that "
            f"file and its directory."
        ) from exc
    logger.info("Database ready at %s", DB_PATH)


# Create the schema when this module is imported, not only from a lifecycle hook.
# It previously ran solely from the NiceGUI @app.on_startup handler in app/main.py,
# and a failure there was logged while the app carried on serving. Reproduced for
# issue #1: when devices.db exists but is not writable by the container user,
# create_all fails once at startup with "attempt to write a readonly database",
# then every page render runs a SELECT that opens the file fine and reports
# "no such table: devices". The visible, repeating error names the table while the
# real cause has already scrolled past. Creating the schema here, and raising, makes
# the real cause fatal and first. create_all is a no-op once the tables exist.
init_db()


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
