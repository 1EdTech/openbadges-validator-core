from input import detect_input_type
from graph import fetch_http_node, jsonld_compact_data
from validation import (detect_and_validate_node_class, validate_expected_node_class,
                        validate_id_property, validate_primitive_property,)
from task_types import (DETECT_AND_VALIDATE_NODE_CLASS, DETECT_INPUT_TYPE,
                        FETCH_HTTP_NODE, JSONLD_COMPACT_DATA, VALIDATE_EXPECTED_NODE_CLASS,
                        VALIDATE_ID_PROPERTY, VALIDATE_PRIMITIVE_PROPERTY,)


functions = {
    DETECT_AND_VALIDATE_NODE_CLASS: detect_and_validate_node_class,
    DETECT_INPUT_TYPE: detect_input_type,
    FETCH_HTTP_NODE: fetch_http_node,
    JSONLD_COMPACT_DATA: jsonld_compact_data,
    VALIDATE_EXPECTED_NODE_CLASS: validate_expected_node_class,
    VALIDATE_ID_PROPERTY: validate_id_property,
    VALIDATE_PRIMITIVE_PROPERTY: validate_primitive_property,
}


def task_named(key):
    return functions[key]
