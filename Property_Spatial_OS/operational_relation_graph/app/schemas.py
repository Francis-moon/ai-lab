from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SceneNodeCreate(BaseModel):
    node_id: str
    node_type: str
    name: str

    zone: Optional[str] = None
    floor: Optional[str] = None

    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

    state: Optional[str] = None
    confidence: int = 100

    attrs: Dict[str, Any] = Field(default_factory=dict)


class SceneEdgeCreate(BaseModel):
    source_node_id: str
    target_node_id: str
    relation_type: str

    relation_state: str = "hypothesis"
    confidence: int = 60

    created_by: str = "manual_config"
    source_event_id: Optional[str] = None

    attrs: Dict[str, Any] = Field(default_factory=dict)


class EventCreate(BaseModel):
    event_id: str
    event_type: str

    source: str
    source_node_id: Optional[str] = None

    target_node_id: Optional[str] = None
    zone: str

    confidence: int = 60


class TaskOutcomeCreate(BaseModel):
    outcome_id: str
    task_id: str

    outcome_type: str
    confidence: int = 80

    evidence_url: Optional[str] = None
    note: Optional[str] = None

    created_by: str = "cloud_operator"


class RelationEvidenceCreate(BaseModel):
    edge_id: str
    evidence_id: str

    signal_type: str
    source_type: str

    source_id: Optional[str] = None
    event_id: Optional[str] = None
    task_id: Optional[str] = None
    case_id: Optional[str] = None

    confidence_delta: int = 0
    note: Optional[str] = None