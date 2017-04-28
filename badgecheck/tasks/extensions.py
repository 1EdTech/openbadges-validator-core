from ..actions.tasks import add_task
from ..exceptions import TaskPrerequisitesError
from ..state import get_node_by_id
from ..utils import cast_as_list

from .task_types import VALIDATE_EXTENSION_NODE
from .utils import is_iri, filter_tasks, task_result


def extension_analysis(state, task_meta):
    try:
        node_id = task_meta['node_id']
        node = get_node_by_id(state, node_id)
    except (KeyError, IndexError,):
        raise TaskPrerequisitesError()

    actions = []
    processed_nodes = []

    def _detect_extension_validation_actions(current_node_id):
        current_node = get_node_by_id(state, current_node_id)
        if not current_node.get('type'):
            pass
        else:
            types = cast_as_list(current_node['type'])
            if 'Extension' in types and \
                    not filter_tasks(state, name=VALIDATE_EXTENSION_NODE, node_id=current_node_id) and \
                    current_node_id not in processed_nodes:
                actions.append(add_task(VALIDATE_EXTENSION_NODE, node_id=current_node_id))
                processed_nodes.append(current_node_id)

        for key in [k for k in current_node.keys() if k not in ('id', 'type')]:
            try:
                val = current_node.get(key)
                if is_iri(val) and val not in processed_nodes:
                    _detect_extension_validation_actions(val)
            except (IndexError, ValueError,):
                pass

    _detect_extension_validation_actions(node_id)
    return task_result(True, "Node {} analyzed for extension processing.".format(node_id), actions)


def validate_extension_node(state, task_meta):
    pass
