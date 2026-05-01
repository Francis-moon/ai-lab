from sqlalchemy import Column, Integer, String
from .db import Base


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(String, unique=True, index=True, nullable=False)
    zone = Column(String, index=True, nullable=False)
    state = Column(String, nullable=False, default="free")  # free / occupied / illegal / blocked