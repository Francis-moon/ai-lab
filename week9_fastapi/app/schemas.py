from pydantic import BaseModel


class SlotBase(BaseModel):
    slot_id: str
    zone: str
    state: str


class SlotCreate(BaseModel):
    slot_id: str
    zone: str
    state: str = "free"


class SlotUpdateState(BaseModel):
    state: str


class SlotResponse(SlotBase):
    id: int

    class Config:
        from_attributes = True