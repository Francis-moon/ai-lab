from .database import Base, engine, SessionLocal
from .models import SceneNode, SceneEdge, Executor
from .constants import EDGE_CONFIRMED


def seed_data():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    if db.query(SceneNode).count() == 0:
        nodes = [
            SceneNode(
                node_id="zone:A",
                node_type="zone",
                name="A区",
                zone="A",
                floor="B1",
                state="normal",
                confidence=100,
                attrs={}
            ),
            SceneNode(
                node_id="lane:A-main",
                node_type="lane",
                name="A区主通道",
                zone="A",
                floor="B1",
                state="normal",
                confidence=100,
                attrs={}
            ),
            SceneNode(
                node_id="slot:A-003",
                node_type="slot",
                name="A-003车位",
                zone="A",
                floor="B1",
                x=10,
                y=20,
                z=0,
                state="occupied",
                confidence=100,
                attrs={
                    "slot_type": "normal"
                }
            ),
            SceneNode(
                node_id="camera:A-cam-01",
                node_type="camera",
                name="A区摄像头01",
                zone="A",
                floor="B1",
                state="online",
                confidence=95,
                attrs={
                    "rtsp": "mock://camera-a-01"
                }
            ),
            SceneNode(
                node_id="executor:robot-A-1",
                node_type="executor",
                name="A区机器人1",
                zone="A",
                floor="B1",
                state="idle",
                confidence=100,
                attrs={
                    "executor_type": "robot",
                    "battery": 80
                }
            ),
            SceneNode(
                node_id="executor:cloud-A-1",
                node_type="executor",
                name="A区云岗亭坐席1",
                zone="A",
                floor="cloud",
                state="idle",
                confidence=100,
                attrs={
                    "executor_type": "cloud_operator"
                }
            ),
            SceneNode(
                node_id="executor:human-A-1",
                node_type="executor",
                name="A区人工巡检员1",
                zone="A",
                floor="B1",
                state="idle",
                confidence=100,
                attrs={
                    "executor_type": "human"
                }
            )
        ]

        db.add_all(nodes)
        db.commit()

    if db.query(SceneEdge).count() == 0:
        edges = [
            SceneEdge(
                edge_id="edge:zone:A|contains|lane:A-main",
                source_node_id="zone:A",
                target_node_id="lane:A-main",
                relation_type="contains",
                relation_state=EDGE_CONFIRMED,
                confidence=100,
                evidence_count=1,
                positive_count=1,
                created_by="manual_config",
                attrs={}
            ),
            SceneEdge(
                edge_id="edge:lane:A-main|near|slot:A-003",
                source_node_id="lane:A-main",
                target_node_id="slot:A-003",
                relation_type="near",
                relation_state=EDGE_CONFIRMED,
                confidence=100,
                evidence_count=1,
                positive_count=1,
                created_by="manual_config",
                attrs={}
            ),
            SceneEdge(
                edge_id="edge:camera:A-cam-01|observes|slot:A-003",
                source_node_id="camera:A-cam-01",
                target_node_id="slot:A-003",
                relation_type="observes",
                relation_state=EDGE_CONFIRMED,
                confidence=85,
                evidence_count=1,
                positive_count=1,
                created_by="manual_config",
                attrs={
                    "calibration": "manual"
                }
            ),
            SceneEdge(
                edge_id="edge:executor:robot-A-1|operates_in|zone:A",
                source_node_id="executor:robot-A-1",
                target_node_id="zone:A",
                relation_type="operates_in",
                relation_state=EDGE_CONFIRMED,
                confidence=100,
                evidence_count=1,
                positive_count=1,
                created_by="manual_config",
                attrs={}
            )
        ]

        db.add_all(edges)
        db.commit()

    if db.query(Executor).count() == 0:
        executors = [
            Executor(
                executor_id="robot-A-1",
                executor_type="robot",
                zone="A",
                status="idle",
                battery_level=80,
                can_handle="robot_recheck,capture_evidence,clear_blocked_lane",
                current_task_id=None,
                online=True
            ),
            Executor(
                executor_id="cloud-A-1",
                executor_type="cloud_operator",
                zone="A",
                status="idle",
                battery_level=None,
                can_handle="remote_verify,notify_property,manual_review",
                current_task_id=None,
                online=True
            ),
            Executor(
                executor_id="human-A-1",
                executor_type="human",
                zone="A",
                status="idle",
                battery_level=None,
                can_handle="clear_blocked_lane,robot_recheck,capture_evidence,supervisor_escalation",
                current_task_id=None,
                online=True
            )
        ]

        db.add_all(executors)
        db.commit()

    db.close()
    print("Seed completed.")


if __name__ == "__main__":
    seed_data()