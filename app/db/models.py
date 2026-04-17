"""
app/db/models.py
SQLAlchemy ORM models.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    key = Column(String, nullable=False)
    version = Column(Float, default=3.3)
    persist = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)

    # Runtime metadata (updated by bridge)
    last_seen = Column(DateTime, nullable=True)
    last_status = Column(Text, nullable=True)   # JSON blob of DPS values
    is_online = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "ip": self.ip,
            "key": self.key,
            "version": self.version,
            "persist": self.persist,
            "enabled": self.enabled,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "last_status": self.last_status,
            "is_online": self.is_online,
        }

    def __repr__(self):
        return f"<Device {self.name} ({self.device_id}) @ {self.ip}>"
