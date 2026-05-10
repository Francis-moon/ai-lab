from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ZoneCreate(BaseModel):
    zone_id: str
    name: str
    zone_type: str

    site_id: str = "default_site"
    floor: Optional[str] = None
    parent_zone_id: Optional[str] = None

    state: str = "normal"
    heat: int = 1
    risk_score: float = 0.0

    capacity: int = 0
    occupancy: int = 0

    boundary_polygon: List[List[float]] = Field(default_factory=list)
    policy: Dict[str, Any] = Field(default_factory=dict)
    attrs: Dict[str, Any] = Field(default_factory=dict)


class ZoneTopologyCreate(BaseModel):
    edge_id: str
    source_zone_id: str
    target_zone_id: str
    relation_type: str = "adjacent_to"
    distance: float = 1.0
    bidirectional: bool = True
    confidence: int = 100
    attrs: Dict[str, Any] = Field(default_factory=dict)


class SceneNodeCreate(BaseModel):
    node_id: str
    node_type: str
    name: str

    zone_id: Optional[str] = None
    floor: Optional[str] = None

    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

    state: Optional[str] = None
    confidence: int = 100

    attrs: Dict[str, Any] = Field(default_factory=dict)


class ZoneMemberCreate(BaseModel):
    zone_id: str
    node_id: str
    role: str
    confidence: int = 100
    attrs: Dict[str, Any] = Field(default_factory=dict)


class EventCreate(BaseModel):
    event_id: str
    event_type: str

    source: str
    zone_id: str

    source_node_id: Optional[str] = None
    target_node_id: Optional[str] = None

    confidence: int = 60


class TaskOutcomeCreate(BaseModel):
    outcome_id: str
    task_id: str

    outcome_type: str
    confidence: int = 80

    note: Optional[str] = None
    evidence_url: Optional[str] = None
    created_by: str = "cloud_operator"