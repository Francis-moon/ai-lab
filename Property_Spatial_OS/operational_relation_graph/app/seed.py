from .database import Base, engine, SessionLocal
from .models import SceneNode, SceneEdge, Executor


def seed_data():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    if db.query(SceneNode).count() == 0:
        db.add_all([
            SceneNode(
                node_id="zone:A",
                node_type="zone",
                name="A区",
                zone="A",
                state="normal",
                confidence=100,
                attrs={}
            ),
            SceneNode(
                node_id="lane:A-main",
                node_type="lane",
                name="A区主通道",
                zone="A",
                state="normal",
                confidence=100,
                attrs={}
            ),
            SceneNode(
                node_id="slot:A-003",
                node_type="slot",
                name="A-003车位",
                zone="A",
                state="occupied",
                confidence=90,
                attrs={}
            ),
            SceneNode(
                node_id="camera:A-cam-01",
                node_type="camera",
                name="A区摄像头01",
                zone="A",
                state="online",
                confidence=90,
                attrs={}
            ),
            SceneNode(
                node_id="robot:robot-A-1",
                node_type="robot",
                name="A区机器人1",
                zone="A",
                state="idle",
                confidence=90,
                attrs={"battery": 80}
            ),
        ])

    if db.query(SceneEdge).count() == 0:
        db.add_all([
            SceneEdge(
                edge_id="zone:A--contains--lane:A-main",
                source_node_id="zone:A",
                target_node_id="lane:A-main",
                relation_type="contains",
                relation_state="confirmed",
                confidence=100,
                evidence_count=1,
                created_by="manual_config",
                attrs={}
            ),
            SceneEdge(
                edge_id="lane:A-main--near--slot:A-003",
                source_node_id="lane:A-main",
                target_node_id="slot:A-003",
                relation_type="near",
                relation_state="confirmed",
                confidence=95,
                evidence_count=1,
                created_by="manual_config",
                attrs={}
            ),
            SceneEdge(
                edge_id="camera:A-cam-01--observes--slot:A-003",
                source_node_id="camera:A-cam-01",
                target_node_id="slot:A-003",
                relation_type="observes",
                relation_state="hypothesis",
                confidence=70,
                evidence_count=1,
                created_by="manual_config",
                attrs={}
            ),
            SceneEdge(
                edge_id="robot:robot-A-1--reachable_by--slot:A-003",
                source_node_id="slot:A-003",
                target_node_id="robot:robot-A-1",
                relation_type="reachable_by",
                relation_state="hypothesis",
                confidence=70,
                evidence_count=1,
                created_by="manual_config",
                attrs={}
            ),
        ])

    if db.query(Executor).count() == 0:
        db.add_all([
            Executor(
                executor_id="cloud-A-1",
                executor_type="cloud_operator",
                zone="A",
                status="idle",
                can_handle="remote_verify,notify_property",
                online=True,
            ),
            Executor(
                executor_id="robot:robot-A-1",
                executor_type="robot",
                zone="A",
                status="idle",
                can_handle="robot_recheck,capture_evidence",
                online=True,
            ),
            Executor(
                executor_id="human-A-1",
                executor_type="human",
                zone="A",
                status="idle",
                can_handle="manual_review,clear_blocked_lane",
                online=True,
            ),
        ])

    db.commit()
    db.close()

    print("Seed completed.")


if __name__ == "__main__":
    seed_data()