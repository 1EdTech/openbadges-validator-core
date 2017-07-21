import re
import rfc3986
import six

URN_REGEX = r'^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'


def task_result(success=True, message='', actions=None):
    """
    Formats a response from a task so that the task caller can dispatch actions
    :param success: bool
    :param message: str
    :param actions: list(dict)
    :return:
    """
    if not actions:
        actions = []

    return (success, message, actions,)


def is_empty_list(value):
    return isinstance(value, (tuple, list,)) and len(value) == 0


def is_null_list(value):
    return isinstance(value, (tuple, list,)) and all(val is None for val in value)


def abbreviate_value(value):
    if isinstance(value, (tuple, list)):
        value = ', '.join([str(val) for val in value])

    if len(str(value)) < 48:
        return str(value)
    else:
        return str(value)[:48] + '...'


def abbreviate_node_id(node_id=None, node_path=None):
    if node_id:
        return node_id
    return abbreviate_value(node_path)


def is_iri(value):
    return bool(
        is_url(value) or
        re.match(r'_:b\d+$', value) or
        re.match(URN_REGEX, value, re.IGNORECASE)
    )


def is_url(value):
    ret = False
    try:
        if ((value and isinstance(value, six.string_types))
            and rfc3986.is_valid_uri(value, require_scheme=True)
            and rfc3986.uri_reference(value).scheme.lower() in ['http', 'https']):
            ret = True
    except ValueError as e:
        pass
    return ret


def filter_tasks(state, **kwargs):
    tasks = state.get('tasks', [])

    def _matches(val):
        return all([val.get(kwarg) == kwargs[kwarg] for kwarg in kwargs.keys()])

    return filter(_matches, tasks)
