from typing import Optional, Dict, Any
from pydantic import BaseModel


class SceneNodeCreate(BaseModel):
    node_id: str
    node_type: str
    name: str
    zone: Optional[str] = None
    floor: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    state: Optional[str] = None     # free、occupied、cleaning 等
    confidence: int = 100
    attrs: Dict[str, Any] = {}


class SceneEdgeCreate(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str      # adjacent、belongs_to、near、has_robot 等
    confidence: int = 100
    attrs: Dict[str, Any] = {}


from typing import Optional, Dict, Any
from pydantic import BaseModel


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
    note: Optional[str] = None
    created_by: str = "cloud_operator"


class RelationHypothesisCreate(BaseModel):
    source_node_id: str
    relation_type: str
    target_node_id: str
    confidence: int = 50
    created_by: str = "system"
    source_type: str = "manual_config"
    source_id: str = "manual"
    detail: str = ""


class RelationUpdateRequest(BaseModel):
    source_type: str = "manual"
    source_id: str = "manual"
    created_by: str = "operator"
    confidence: int = 90
    detail: str = ""


class FeedbackCreate(BaseModel):
    feedback_id: str
    case_id: str
    task_id: Optional[str] = None
    feedback_type: str
    root_cause: Optional[str] = None
    note: Optional[str] = None
    created_by: str = "operator"
    attrs: Dict[str, Any] = {}


class MapPatchCreate(BaseModel):
    patch_id: str
    target_node_id: str
    patch_type: str
    payload: Dict[str, Any] = {}
    source_case_id: Optional[str] = None
    proposed_by: str = "system"
