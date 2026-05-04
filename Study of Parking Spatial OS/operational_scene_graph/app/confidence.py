SOURCE_WEIGHT = {
    "ai_box": 0.60,
    "camera": 0.60,
    "entrance_camera": 0.75,
    "robot": 0.90,
    "cloud_operator": 0.85,
    "human": 0.95,
    "iot": 0.80,
    "system": 0.70,
}


def normalize_confidence(raw_confidence: int, source: str) -> int:
    weight = SOURCE_WEIGHT.get(source, 0.60)
    return int(raw_confidence * weight)


def fuse_confidence(existing: int, incoming: int) -> int:
    """
    简化版概率融合：
    两个独立证据共同支持时，置信度上升。
    """
    a = existing / 100
    b = incoming / 100

    fused = 1 - (1 - a) * (1 - b)
    return min(99, int(fused * 100))


def reduce_confidence(existing: int, negative_signal: int) -> int:
    """
    负反馈降低置信度。
    """
    return max(0, existing - int(negative_signal * 0.5))
