from .database import Base, engine, SessionLocal
from .models import SceneNode, SceneEdge, Executor


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
                attrs={}
            ),
            SceneNode(
                node_id="lane:A-main",
                node_type="lane",
                name="A区主通道",
                zone="A",
                floor="B1",
                state="normal",
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
                attrs={"slot_type": "normal"}
            ),
            SceneNode(
                node_id="camera:A-cam-01",
                node_type="camera",
                name="A区摄像头01",
                zone="A",
                floor="B1",
                state="online",
                attrs={"rtsp": "mock://camera-a-01"}
            ),
            SceneNode(
                node_id="robot:robot-A-1",
                node_type="robot",
                name="A区机器人1",
                zone="A",
                floor="B1",
                state="idle",
                attrs={"battery": 80}
            )
        ]

        db.add_all(nodes)

        edges = [
            SceneEdge(
                edge_id="zone:A-contains-lane:A-main",
                source_node_id="zone:A",
                target_node_id="lane:A-main",
                relation_type="contains"
            ),
            SceneEdge(
                edge_id="lane:A-main-near-slot:A-003",
                source_node_id="lane:A-main",
                target_node_id="slot:A-003",
                relation_type="near"
            ),
            SceneEdge(
                edge_id="camera:A-cam-01-observes-slot:A-003",
                source_node_id="camera:A-cam-01",
                target_node_id="slot:A-003",
                relation_type="observes"
            ),
            SceneEdge(
                edge_id="robot:robot-A-1-operates-in-zone:A",
                source_node_id="robot:robot-A-1",
                target_node_id="zone:A",
                relation_type="operates_in"
            )
        ]

        db.add_all(edges)

    if db.query(Executor).count() == 0:
        db.add_all([
            Executor(
                executor_id="cloud-A-1",
                executor_type="cloud_operator",
                zone="A",
                status="idle",
                can_handle="remote_verify,notify_property,manual_review",
                online=True
            ),
            Executor(
                executor_id="robot-A-1",
                executor_type="robot",
                zone="A",
                status="idle",
                battery_level=80,
                can_handle="robot_recheck,capture_evidence,clear_blocked_lane",
                online=True
            ),
            Executor(
                executor_id="human-A-1",
                executor_type="human",
                zone="A",
                status="idle",
                can_handle="clear_blocked_lane,robot_recheck,capture_evidence,supervisor_escalation",
                online=True
            )
        ])

    db.commit()
    db.close()

    print("Seed completed.")


if __name__ == "__main__":
    seed_data()