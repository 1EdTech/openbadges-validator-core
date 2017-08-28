import uuid


def generate_task_key():
    return uuid.uuid4().hex
