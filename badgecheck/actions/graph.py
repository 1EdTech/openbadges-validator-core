from .action_types import ADD_NODE, PATCH_NODE, PATCH_NODE_REFERENCE, UPDATE_NODE
import sys


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


def patch_node_reference(node_path, new_id):
    """
    When a reference to another node in the graph needs to be updated
    after discovering that it has a different canonical id, use this.
    :param node_path: list
    :param new_id: str
    :return: dict
    """
    return {
        'type': PATCH_NODE_REFERENCE,
        'node_path': node_path,
        'new_id': new_id
    }
