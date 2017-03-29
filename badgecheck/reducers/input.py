from ..actions.action_types import STORE_INPUT, SET_INPUT_TYPE


def input_reducer(state=None, action=None):
    if state is None:
        state = {}

    if action.get('type') == STORE_INPUT:
        return {'value': action.get('input')}
    elif action.get('type') == SET_INPUT_TYPE:
        new_state = state.copy()
        new_state.update({'input_type': action.get('input_type')})
        return new_state

    return state
