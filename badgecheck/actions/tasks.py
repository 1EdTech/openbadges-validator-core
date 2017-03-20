from action_types import ADD_TASK, DELETE_TASK, RESOLVE_TASK, UPDATE_TASK
from ..tasks import task_named


def add_task(task_name, **kwargs):
    # Raises KeyError if unknown task name used.
    task_named(task_name)

    task = {
        'type': ADD_TASK,
        'name': task_name
    }
    task.update(**kwargs)
    return task


def resolve_task(task_id, success=True, result=''):
    return {
        'type': RESOLVE_TASK,
        'id': task_id,
        'success': success,
        'result': result
    }


def delete_task(task_id):
    return {
        'type': DELETE_TASK,
        'id': task_id
    }


def update_task(task_id, task_name, **kwargs):
    # Raises KeyError if unknown task name used.
    task_named(task_name)

    task = {
        'type': UPDATE_TASK,
        'id': task_id,
        'name': task_name,
    }
    task.update(**kwargs)
    return task
