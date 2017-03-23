def task_result(success=True, message='', actions=[]):
    """
    Formats a response from a task so that the task caller can dispatch actions
    :param success: bool
    :param message: str
    :param actions: list(dict)
    :return:
    """
    return (success, message, actions,)
