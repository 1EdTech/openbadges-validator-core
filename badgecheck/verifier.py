import json
from openbadges_bakery import unbake
from pydux import create_store
import traceback

from .actions.input import set_input_type, store_input
from .actions.tasks import add_task, resolve_task, trigger_condition
from .exceptions import SkipTask, TaskPrerequisitesError
from .logger import logger
from .openbadges_context import OPENBADGES_CONTEXT_V2_URI
from .reducers import main_reducer
from .state import (filter_active_tasks, filter_messages_for_report, format_message,
                    INITIAL_STATE, MESSAGE_LEVEL_ERROR, MESSAGE_LEVEL_WARNING,)
import tasks
from tasks.task_types import JSONLD_COMPACT_DATA
from tasks.validation import OBClasses
from .utils import list_of, CachableDocumentLoader, jsonld_use_cache



DEFAULT_OPTIONS = {
    'include_original_json': False,  # Return the original JSON strings fetched from HTTP
    'use_cache': True,
    'cache_backend': 'memory',
    'cache_expire_after': 300,
    'jsonld_options': jsonld_use_cache
}


def _get_options(options):
    if options:
        selected = DEFAULT_OPTIONS.copy()
        selected.update(options)
    else:
        selected = DEFAULT_OPTIONS

    if selected['use_cache']:
        doc_loader = CachableDocumentLoader(
            use_cache=selected['use_cache'],
            backend=selected['cache_backend'],
            expire_after=selected['cache_expire_after']
        )
    else:
        doc_loader = CachableDocumentLoader(use_cache=False)

    selected['jsonld_options'] = {'documentLoader': doc_loader}
    return selected


def call_task(task_func, task_meta, store, options=DEFAULT_OPTIONS):
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
        success, message, actions = task_func(store.get_state(), task_meta, **options)
    except SkipTask:
        raise NotImplemented("Implement SkipTask handling in call_task")
    except TaskPrerequisitesError:
        message = "Task could not run due to unmet prerequisites."
        store.dispatch(resolve_task(task_meta.get('task_id'), success=False, result=message))
    except Exception as e:
        logger.error(traceback.format_exc())
        message = "{} {}".format(e.__class__, e.message)
        store.dispatch(resolve_task(task_meta.get('task_id'), success=False, result=message))
    else:
        store.dispatch(resolve_task(task_meta.get('task_id'), success=success, result=message))
        if success:
            for trigger in list_of(task_meta.get('triggers_completion', [])):
                store.dispatch(trigger_condition(trigger, 'Completed by {}: {}'.format(
                    task_meta.get('task_id'), task_meta.get('name')
                )))

    # Make updates and queue up next tasks.
    for action in actions:
        store.dispatch(action)


def verification_store(badge_input, recipient_profile=None, store=None, options=DEFAULT_OPTIONS):
    if store is None:
        store = create_store(main_reducer, INITIAL_STATE)
    try:
        if hasattr(badge_input, 'read') and hasattr(badge_input, 'seek'):
            badge_input.seek(0)
            badge_data = unbake(badge_input)
            if not badge_data:
                raise ValueError("Could not find Open Badges metadata in file.")
        else:
            badge_data = badge_input
    except ValueError as e:
        # Could not obtain badge data from input. Set the result as a failed DETECT_INPUT_TYPE task.
        store.dispatch(store_input(badge_input.name))
        store.dispatch(add_task(tasks.DETECT_INPUT_TYPE))
        store.dispatch(set_input_type('file'))
        task = store.get_state()['tasks'][0]
        store.dispatch(resolve_task(task.get('task_id'), success=False, result=e.message))
    else:
        store.dispatch(store_input(badge_data))
        store.dispatch(add_task(tasks.DETECT_INPUT_TYPE))

    if recipient_profile:
        profile_id = recipient_profile.get('id')
        recipient_profile['@context'] = recipient_profile.get('@context', OPENBADGES_CONTEXT_V2_URI)
        task = add_task(
            JSONLD_COMPACT_DATA,
            data=json.dumps(recipient_profile),
            expected_class=OBClasses.ExpectedRecipientProfile)
        if profile_id:
            task['node_id'] = profile_id
        store.dispatch(task)

    last_task_id = 0
    while len(filter_active_tasks(store.get_state())):
        active_tasks = filter_active_tasks(store.get_state())
        task_meta = active_tasks[0]
        task_func = tasks.task_named(task_meta['name'])

        if task_meta['task_id'] == last_task_id:
            break

        last_task_id = task_meta['task_id']
        call_task(task_func, task_meta, store, options)

    return store


def generate_report(store, options=DEFAULT_OPTIONS):
    """
    Returns a report of validity information based on a store and its tasks.
    """
    state = store.get_state()

    processed_input = state['input'].copy()
    if not options.get('include_original_json'):
        try:
            del processed_input['original_json']
        except KeyError:
            pass

    tasks_for_messages_list = filter_messages_for_report(state)
    report = state['report'].copy()
    report['messages'] = []
    for task in tasks_for_messages_list:
        report['messages'].append(format_message(task))

    report['errorCount'] = len([m for m in report['messages'] if m['messageLevel'] == MESSAGE_LEVEL_ERROR])
    report['warningCount'] = len([m for m in report['messages'] if m['messageLevel'] == MESSAGE_LEVEL_WARNING])
    report['valid'] = not bool(report['errorCount'])

    ret = {
        'graph': state['graph'],
        'input': processed_input,
        'report': report
    }
    return ret


def verify(badge_input, recipient_profile=None, **options):
    """
    Verify and validate Open Badges
    :param badge_input: str (url or json) or python file-like object (baked badge image)
    :param recipient_profile: dict of a trusted Profile describing the entity assumed to be recipient
    :param options: dict of options. See DEFAULT_OPTIONS for values
    :return: dict
    """
    selected_options = _get_options(options)
    store = verification_store(badge_input, recipient_profile, options=selected_options)
    return generate_report(store, options=selected_options)
