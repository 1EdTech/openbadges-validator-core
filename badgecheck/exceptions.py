"""
Custom exceptions for the function of Open Badges verification
"""

class SkipTask(Exception):
    """
    This exception indicates that the present task is not ready to be executed
    and should be shuffled to the back of the stack.
    """
    pass


class TaskPrerequisitesError(Exception):
    """
    This exception indicates that the present task has prerequisites better
    expressed in other tasks that were not met in order to run.
    """
    pass


class ValidationError(Exception):
    """
    This exception is used in tasks to indicate that a requirement has not been met.
    """
    pass
