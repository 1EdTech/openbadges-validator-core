from ..action_types import STORE_INPUT


def store_input(badge_input):
    """
    Emits an action that encapsulates user input provided and instructs that it
    be stored in the state.
    :param badge_input: string
    :return: dict
    """
    return {
        'type': STORE_INPUT,
        'input': badge_input
    }
