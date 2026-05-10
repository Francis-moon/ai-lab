from .database import Base, engine, SessionLocal
from .models import (
    FunctionalZone,
    ZoneTopologyEdge,
    SceneNode,
    ZoneMember,
    Executor
)


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(FunctionalZone).count() == 0:
        zones = [
            FunctionalZone(
                zone_id="zone:entrance-A",
                name="A入口区",
                zone_type="entrance",
                floor="B1",
                state="normal",
                heat=1,
                capacity=20,
                occupancy=5,
                boundary_polygon=[[0, 0], [8, 0], [8, 6], [0, 6]],
                policy={
                    "illegal_parking_sla": 3,
                    "blocked_lane_sla": 2,
                    "device_fault_sla": 10,
                    "illegal_parking_fallback": "cloud_operator,robot,human"
                }
            ),
            FunctionalZone(
                zone_id="zone:lane-A-main",
                name="A区主通道",
                zone_type="lane",
                floor="B1",
                state="normal",
                heat=1,
                capacity=50,
                occupancy=15,
                boundary_polygon=[[8, 0], [30, 0], [30, 6], [8, 6]],
                policy={
                    "blocked_lane_sla": 3,
                    "blocked_lane_fallback": "human,robot,cloud_operator"
                }
            ),
            FunctionalZone(
                zone_id="zone:parking-A",
                name="A区停车区",
                zone_type="parking_area",
                floor="B1",
                state="normal",
                heat=1,
                capacity=120,
                occupancy=80,
                boundary_polygon=[[8, 6], [30, 6], [30, 20], [8, 20]],
                policy={
                    "illegal_parking_sla": 5,
                    "robot_recheck_sla": 8
                }
            ),
            FunctionalZone(
                zone_id="zone:equipment-A",
                name="A区设备房",
                zone_type="equipment_room",
                floor="B1",
                state="normal",
                heat=1,
                capacity=0,
                occupancy=0,
                boundary_polygon=[[0, 6], [8, 6], [8, 12], [0, 12]],
                policy={
                    "device_fault_sla": 10,
                    "device_fault_fallback": "human,cloud_operator"
                }
            )
        ]
        db.add_all(zones)
        db.commit()

    if db.query(ZoneTopologyEdge).count() == 0:
        edges = [
            ZoneTopologyEdge(
                edge_id="zt:entrance-A:flow_to:lane-A-main",
                source_zone_id="zone:entrance-A",
                target_zone_id="zone:lane-A-main",
                relation_type="flow_to",
                distance=1.0,
                bidirectional=True
            ),
            ZoneTopologyEdge(
                edge_id="zt:lane-A-main:adjacent_to:parking-A",
                source_zone_id="zone:lane-A-main",
                target_zone_id="zone:parking-A",
                relation_type="adjacent_to",
                distance=1.5,
                bidirectional=True
            ),
            ZoneTopologyEdge(
                edge_id="zt:lane-A-main:adjacent_to:equipment-A",
                source_zone_id="zone:lane-A-main",
                target_zone_id="zone:equipment-A",
                relation_type="adjacent_to",
                distance=2.0,
                bidirectional=True
            )
        ]
        db.add_all(edges)
        db.commit()

    if db.query(SceneNode).count() == 0:
        nodes = [
            SceneNode(
                node_id="camera:A-cam-01",
                node_type="camera",
                name="A区主通道摄像头",
                zone_id="zone:lane-A-main",
                floor="B1",
                state="online",
                confidence=95
            ),
            SceneNode(
                node_id="slot:A-003",
                node_type="slot",
                name="A-003车位",
                zone_id="zone:parking-A",
                floor="B1",
                state="occupied",
                confidence=100
            ),
            SceneNode(
                node_id="gate:A-entrance",
                node_type="barrier_gate",
                name="A入口道闸",
                zone_id="zone:entrance-A",
                floor="B1",
                state="online",
                confidence=100
            ),
            SceneNode(
                node_id="device:A-powerbox",
                node_type="device",
                name="A区设备箱",
                zone_id="zone:equipment-A",
                floor="B1",
                state="online",
                confidence=100
            )
        ]
        db.add_all(nodes)
        db.commit()

    if db.query(ZoneMember).count() == 0:
        members = [
            ZoneMember(zone_id="zone:lane-A-main", node_id="camera:A-cam-01", role="sensor"),
            ZoneMember(zone_id="zone:parking-A", node_id="slot:A-003", role="target"),
            ZoneMember(zone_id="zone:entrance-A", node_id="gate:A-entrance", role="device"),
            ZoneMember(zone_id="zone:equipment-A", node_id="device:A-powerbox", role="device")
        ]
        db.add_all(members)
        db.commit()

    if db.query(Executor).count() == 0:
        executors = [
            Executor(
                executor_id="robot-A-1",
                executor_type="robot",
                zone_id="zone:lane-A-main",
                status="idle",
                battery_level=80,
                can_handle="robot_recheck,capture_evidence,clear_blocked_lane",
                online=True
            ),
            Executor(
                executor_id="cloud-A-1",
                executor_type="cloud_operator",
                zone_id="zone:entrance-A",
                status="idle",
                can_handle="remote_verify,notify_property,manual_review,device_diagnosis",
                online=True
            ),
            Executor(
                executor_id="human-A-1",
                executor_type="human",
                zone_id="zone:lane-A-main",
                status="idle",
                can_handle="clear_blocked_lane,robot_recheck,capture_evidence,repair_dispatch,device_diagnosis",
                online=True
            )
        ]
        db.add_all(executors)
        db.commit()

    db.close()
    print("Seed completed.")


if __name__ == "__main__":
    seed_data()