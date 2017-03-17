from ..action_types import STORE_INPUT


def input_reducer(state=None, action=None):
    if action.get('type') == STORE_INPUT:
        return {'url': action.get('input')}
    elif state is None:
        return {}
    return state
