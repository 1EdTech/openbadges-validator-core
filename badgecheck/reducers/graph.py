import copy

from ..actions.action_types import ADD_NODE, UPDATE_NODE

current_node_number = -1
def _get_next_blank_node_id():
    global current_node_number
    current_node_number += 1
    return "_:b{}".format(current_node_number)
    # TODO: Handle case where current blank node id is already in the node list


def _flatten_node(node, node_id=None):
    if node.get('id') is None:
        node['id'] = node_id or _get_next_blank_node_id()
    node_list = []

    for prop in node:
        if isinstance(node[prop], dict):
            prop_id = node[prop].get('id', _get_next_blank_node_id())
            node_list.extend(_flatten_node(node[prop], prop_id))
            node[prop] = prop_id
        elif isinstance(node[prop], list):
            current_list = node[prop]
            for index in [i for i in range(len(current_list)) if isinstance(current_list[i], dict)]:
                prop_id = current_list[i].get('id', _get_next_blank_node_id())
                node_list.extend(_flatten_node(current_list[i], prop_id))
                current_list[i] = prop_id

    node_list.append(node)
    return node_list


def graph_reducer(state=None, action=None):
    if state is None:
        state = []

    if action.get('type') == ADD_NODE:
        state = list(state)  # copy state instead of mutating original
        new_node = copy.deepcopy(action.get('data'))
        new_nodes = _flatten_node(new_node, action.get('node_id'))
        state.extend(new_nodes)
    elif action.get('type') == UPDATE_NODE:
        # TODO
        raise NotImplementedError("TODO: Implement updating nodes.")

    return state
