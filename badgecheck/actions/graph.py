from action_types import ADD_NODE, PATCH_NODE, UPDATE_NODE


def add_node(node_id=None, data=None):
    if data is None:
        data = {}

    return {
        'type': ADD_NODE,
        'node_id': node_id,
        'data': data
    }


def update_node(node_id, data):
    action = {
        'type': UPDATE_NODE,
        'node_id': node_id,
        'data': data
    }
    return action


def patch_node(node_id, data):
    action = update_node(node_id, data)
    action['type'] = PATCH_NODE
    return action
