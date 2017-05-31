import copy

from ..actions.action_types import ADD_NODE, PATCH_NODE, SCRUB_REVOCATION_LIST, UPDATE_NODE
from ..state import get_node_by_id
from ..utils import list_of


current_node_number = -1
def get_next_blank_node_id():
    global current_node_number
    current_node_number += 1
    return "_:b{}".format(current_node_number)
    # TODO: Handle case where current blank node id is already in the node list


def _flatten_node(node, node_id=None):
    if node.get('id') is None:
        node['id'] = node_id or get_next_blank_node_id()
    node_list = []

    for prop in node:
        if isinstance(node[prop], dict):
            prop_id = node[prop].get('id', get_next_blank_node_id())
            node_list.extend(_flatten_node(node[prop], prop_id))
            node[prop] = prop_id
        elif isinstance(node[prop], list):
            current_list = node[prop]
            dict_indices = [i for i in range(len(current_list)) if isinstance(current_list[i], dict)]
            for index in dict_indices:
                prop_id = current_list[index].get('id', get_next_blank_node_id())
                node_list.extend(_flatten_node(current_list[index], prop_id))
                current_list[index] = prop_id

    node_list.append(node)
    return node_list


def _scrub_revocation_list_node(state, node_id, safe_ids=None):
    """ Return a copy of state that does not include the revocationList or any assertions referenced from it."""
    if not node_id:
        return state
    if safe_ids is None:
        safe_ids = []

    try:
        target_node = [node for node in state if node.get('id') == node_id][0]
    except IndexError:
        return state

    new_state = []

    ids_to_exclude = [node_id] + list_of(target_node.get('revokedAssertions', []))

    for node in state:
        if node.get('id') in safe_ids or node.get('id') not in ids_to_exclude:
            new_state.append(node)

    return new_state


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
    elif action.get('type') == PATCH_NODE:
        try:
            existing_node = get_node_by_id({'graph': state}, action.get('node_id'))
            state = list(state)
            updated_node = copy.copy(existing_node)
            updated_node.update(action.get('data'))
            state = [node for node in state if node is not existing_node]
            state.append(updated_node)
        except IndexError:
            pass
    elif action.get('type') == SCRUB_REVOCATION_LIST:
        state = _scrub_revocation_list_node(state, action.get('node_id'), action.get('safe_ids'))

    return state
