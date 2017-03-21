from actions.action_types import ADD_NODE, UPDATE_NODE


def input_reducer(state=None, action=None):
    if state is None:
        state = []

    if action.get('type') == ADD_NODE:
        state = state.copy()
        new_node = action.get('data')
        if action.get('node_id') and action.get('data', {}).get('id'):
            new_node['id'] = action.get('node_id')
        state.append(new_node)
    elif action.get('type') == UPDATE_NODE:
        # TODO
        raise NotImplementedError("TODO: Implement updating nodes.")

    return state
