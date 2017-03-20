"""
Custom exceptions for the function of Open Badges verification
"""

class SkipTask(Exception):
    """
    This exception indicates that the present task is not ready to be executed
    and should be shuffled to the back of the stack.
    """
    pass
