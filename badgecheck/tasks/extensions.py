import jsonschema

from ..actions.tasks import add_task
from ..exceptions import TaskPrerequisitesError
from ..extensions import ALL_KNOWN_EXTENSIONS
from ..state import get_node_by_id
from ..utils import cast_as_list

from .task_types import VALIDATE_EXTENSION_NODE
from .utils import abbreviate_value, is_iri, filter_tasks, task_result


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


def _validate_single_extension(node, extension_type):
    # Load extension
    extension = ALL_KNOWN_EXTENSIONS[extension_type]

    # Establish node structure to test
    this_thing = node

    # Validate against JSON-schema
    context = extension.context_json
    for validation in context.get('obi:validation', []):
        schema_url = validation.get('obi:validationSchema', '')
    try:
        schema = extension.validation_schema[schema_url]
    except KeyError:
        # TODO: Fail
        raise NotImplementedError()

    try:
        result = jsonschema.validate(node, schema)
    except jsonschema.ValidationError as e:
        return task_result(
            False, "Extension {} did not validate on node {}: {}".format(
                extension_type, node.get('id'), e.message
            )
        )
        # Issue: Schema that expect a nested result won't be able to
        # handle our flat graph structure. How to determine how much
        # to reassemble the node?

    return task_result(True, "Extension {} validated on node {}".format(
        extension_type, node.get('id')
    ))


def validate_extension_node(state, task_meta):
    try:
        node_id = task_meta['node_id']
        node = get_node_by_id(state, node_id)
        node_type = cast_as_list(node['type'])
    except (KeyError, ValueError):
        raise TaskPrerequisitesError()

    try:
        types_to_test = [task_meta['type_to_test']]
    except KeyError:
        types_to_test = []
        for t in ALL_KNOWN_EXTENSIONS.keys():
            if t in node_type:
                types_to_test.append(t)

    if not types_to_test:
        return task_result(False, "Could not determine extension type to test")
    elif len(types_to_test) > 1:
        # If there is more than one extension, return each validation as a separate task
        actions = [
            add_task(VALIDATE_EXTENSION_NODE, node_id=node_id, type_to_test=t)
            for t in types_to_test
        ]
        return task_result(
            True, "Multiple extension types {} discovered in node {}".format(
                abbreviate_value(types_to_test), node_id
            ), actions)
    else:
        return _validate_single_extension(node, types_to_test[0])
