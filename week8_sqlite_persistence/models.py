from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from db import Base


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(String, unique=True, nullable=False, index=True)
    zone_id = Column(String, nullable=False, index=True)
    lane_id = Column(String, nullable=False, index=True)
    slot_type = Column(String, default="NORMAL", nullable=False)
    state = Column(String, default="FREE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    histories = relationship("SlotHistory", back_populates="slot", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"Slot(id={self.id}, slot_id='{self.slot_id}', zone_id='{self.zone_id}', "
            f"lane_id='{self.lane_id}', type='{self.slot_type}', state='{self.state}')"
        )


class SlotHistory(Base):
    __tablename__ = "slot_history"

    id = Column(Integer, primary_key=True, index=True)
    slot_id_fk = Column(Integer, ForeignKey("slots.id"), nullable=False, index=True)
    slot_id = Column(String, nullable=False, index=True)
    from_state = Column(String, nullable=False)
    to_state = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    event_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    slot = relationship("Slot", back_populates="histories")

    def __repr__(self):
        return (
            f"SlotHistory(id={self.id}, slot_id='{self.slot_id}', "
            f"{self.from_state} -> {self.to_state}, reason='{self.reason}')"
        )