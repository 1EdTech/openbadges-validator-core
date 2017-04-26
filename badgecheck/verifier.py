from pydux import create_store

from .actions.input import store_input
from .actions.tasks import add_task, resolve_task
from .exceptions import SkipTask
from .reducers import main_reducer
from .state import (filter_active_tasks, filter_failed_tasks, format_message,
                    INITIAL_STATE, MESSAGE_LEVEL_ERROR, MESSAGE_LEVEL_WARNING,)
import tasks


def call_task(task_func, task_meta, store):
    """
    Calls and resolves a task function in response to a queued task. May result
    in additional actions added to the queue.
    :param task_func: func
    :param task_meta: dict (single entry in tasks state)
    :param store: pydux store
    :return:
    """
    actions = []
    try:
        success, message, actions = task_func(store.get_state(), task_meta)
    except SkipTask:
        # TODO: Implement skip handling.
        pass
    except Exception as e:
        message = "{} {}".format(e.__class__, e.message)
        store.dispatch(resolve_task(task_meta.get('task_id'), success=False, result=message))
    else:
        store.dispatch(resolve_task(task_meta.get('task_id'), success=success, result=message))

    # Make updates and queue up next tasks.
    for action in actions:
        store.dispatch(action)


def verify(badge_input):
    """
    Verify and validate Open Badges
    :param badge_input: str (url or json)
    :return: dict
    """
    store = create_store(main_reducer, INITIAL_STATE)

    store.dispatch(store_input(badge_input))
    store.dispatch(add_task(tasks.DETECT_INPUT_TYPE))

    last_task_id = 0
    while len(filter_active_tasks(store.get_state())):
        active_tasks = filter_active_tasks(store.get_state())
        task_meta = active_tasks[0]
        task_func = tasks.task_named(task_meta['name'])

        if task_meta['task_id'] == last_task_id:
            break

        last_task_id = task_meta['task_id']
        call_task(task_func, task_meta, store)

    state = store.get_state()
    failed_tasks = filter_failed_tasks(state)
    ret = {
        'messages': [],
        'graph': state['graph'],
        'input': state['input']
    }
    for task in failed_tasks:
        ret['messages'].append(format_message(task))

    ret['errorCount'] = len([m for m in ret['messages'] if m['messageLevel'] == MESSAGE_LEVEL_ERROR])
    ret['warningCount'] = len([m for m in ret['messages'] if m['messageLevel'] == MESSAGE_LEVEL_WARNING])
    ret['valid'] = not bool(ret['errorCount'])

    return ret
