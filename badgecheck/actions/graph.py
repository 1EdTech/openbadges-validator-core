from action_types import ADD_NODE, UPDATE_NODE


def add_node(node_id=None, data=None):
    if data is None:
        data = {}

    return {
        'type': ADD_NODE,
        'node_id': node_id,
        'data': data
    }


def update_node(node_id, data, new_node_id=None):
    action ={
        'type': UPDATE_NODE,
        'node_id': node_id,
        'data': data
    }
    if new_node_id:
        action.update({'node_id': new_node_id})
    return action
