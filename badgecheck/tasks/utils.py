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


def is_empty_list(prop_value):
    return isinstance(prop_value, (tuple, list,)) and len(prop_value) == 0
