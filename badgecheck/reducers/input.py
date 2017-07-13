from ..actions.action_types import STORE_INPUT, SET_INPUT_TYPE, STORE_ORIGINAL_RESOURCE


def input_reducer(state=None, action=None):
    if isinstance(state, dict):
        new_state = state.copy()
    else:
        new_state = {}

    if action.get('type') == STORE_INPUT:
        new_state.update({'value': action.get('input')})
    elif action.get('type') == SET_INPUT_TYPE:
        new_state.update({'input_type': action.get('input_type')})
    elif action.get('type') == STORE_ORIGINAL_RESOURCE:
        original_json = new_state.get('original_json', {})
        original_json[action['node_id']] = action.get('data')
        new_state['original_json'] = original_json

    return new_state
