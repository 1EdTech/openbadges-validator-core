import json
from pyld import jsonld
import re
import validators

from ..actions.input import set_input_type, store_input
from ..actions.tasks import add_task
from ..openbadges_context import OPENBADGES_CONTEXT_V2_URI
from ..utils import CachableDocumentLoader
from task_types import FETCH_HTTP_NODE, PROCESS_JWS_INPUT
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
    jws_regex = re.compile(r'^[A-z0-9\-=]+.[A-z0-9\-=]+.[A-z0-9\-_=]+$')
    return bool(jws_regex.match(user_input))


def find_id_in_jsonld(json_string):
    input_data = json.loads(json_string)
    options = {'documentLoader': CachableDocumentLoader(cachable=True)}
    result = jsonld.compact(input_data, OPENBADGES_CONTEXT_V2_URI, options=options)
    node_id = result.get('id','')
    return node_id


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
        id_url = find_id_in_jsonld(input_value)
        if input_is_url(id_url):
            detected_type = 'url'
            new_actions.append(store_input(id_url))
        else:
            detected_type = 'json'
        new_actions.append(set_input_type(detected_type))
        if detected_type == 'url':
            new_actions.append(add_task(FETCH_HTTP_NODE, url=id_url))
    elif input_is_jws(input_value):
        detected_type = 'jws'
        new_actions.append(set_input_type(detected_type))
        new_actions.append(add_task(PROCESS_JWS_INPUT, data=input_value))
    else:
        raise NotImplementedError("only URL, JSON, or JWS input implemented so far")

    return task_result(
        message="Input of type {} detected.".format(detected_type),
        actions=new_actions
    )
