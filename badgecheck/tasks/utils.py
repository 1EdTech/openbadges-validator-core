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
    if len(str(value)) < 48:
        return str(value)
    else:
        return str(value)[:48] + '...'
