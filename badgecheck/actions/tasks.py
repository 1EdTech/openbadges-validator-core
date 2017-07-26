from ..utils import MESSAGE_LEVEL_INFO, MESSAGE_LEVELS

from .utils import generate_task_key
from .action_types import ADD_TASK, DELETE_TASK, REPORT_MESSAGE, RESOLVE_TASK, TRIGGER_CONDITION, UPDATE_TASK


def add_task(task_name, **kwargs):
    # Ensure task is of a known type
    from ..tasks import task_types
    assert task_name in dir(task_types), '{} is not a known task'.format(task_name)

    task = {
        'type': ADD_TASK,
        'name': task_name,
        'task_key': kwargs.get('task_key', generate_task_key())
    }
    task.update(**kwargs)
    return task


def resolve_task(task_id, success=True, result=''):
    return {
        'type': RESOLVE_TASK,
        'task_id': task_id,
        'success': success,
        'result': result
    }


def trigger_condition(condition_key, result=''):
    return {
        'type': TRIGGER_CONDITION,
        'name': condition_key,
        'success': True,
        'result': result
    }


def delete_task(task_id):
    return {
        'type': DELETE_TASK,
        'task_id': task_id
    }


def update_task(task_id, task_name, **kwargs):
    # Ensure task is of a known type
    from ..tasks import task_types
    assert task_name in dir(task_types), '{} is not a known task'.format(task_name)

    task = {
        'type': UPDATE_TASK,
        'task_id': task_id,
        'name': task_name,
    }
    task.update(**kwargs)
    return task


def report_message(msg, message_level=MESSAGE_LEVEL_INFO):
    if message_level not in MESSAGE_LEVELS:
        raise TypeError("message")
    return {
        'type': REPORT_MESSAGE,
        'message': msg,
        'messageLevel': message_level
    }
