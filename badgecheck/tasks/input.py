import json
import re
import validators

from ..actions.input import set_input_type
from ..actions.tasks import add_task
from task_types import FETCH_HTTP_NODE
from utils import task_result


"""
Helpful utils
"""
def input_is_url(user_input):
    return validators.url(user_input)


def input_is_json(user_input):
    try:
        value = json.loads(user_input)
        return True
    except ValueError:
        return False


def input_is_jws(user_input):
    jws_regex = re.compile(r'^[A-z0-9-]+.[A-z0-9-]+.[A-z0-9-_]+$')
    return bool(jws_regex.match(user_input))


"""
Input-processing tasks
"""
def detect_input_type(state, task_meta=None):
    """
    Detects what data format user has provided and saves to the store.
    """
    input_value = state.get('input').get('value')
    detected_type = None
    new_actions = []

    if input_is_url(input_value):
        detected_type = 'url'
        new_actions.append(set_input_type(detected_type))
        new_actions.append(add_task(FETCH_HTTP_NODE, url=input_value))
    elif input_is_json(input_value):
        detected_type = 'json'
        new_actions.append(set_input_type(detected_type))
    elif input_is_json(input_value):
        detected_type = 'jws'
        new_actions.append(set_input_type(detected_type))
    else:
        raise NotImplementedError("only URL, JSON, or JWS input implemented so far")

    return task_result(
        message="Input of type {} detected.".format(detected_type),
        actions=new_actions
    )
