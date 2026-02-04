import uuid


def generate_video_id() -> str:
    return uuid.uuid4().hex
