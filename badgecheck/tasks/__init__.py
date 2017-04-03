from input import detect_input_type
from graph import fetch_http_node, jsonld_compact_data
from validation import validate_primitive_property
from task_types import (DETECT_INPUT_TYPE, FETCH_HTTP_NODE, JSONLD_COMPACT_DATA,
                        VALIDATE_PRIMITIVE_PROPERTY)


functions = {
    DETECT_INPUT_TYPE: detect_input_type,
    FETCH_HTTP_NODE: fetch_http_node,
    JSONLD_COMPACT_DATA: jsonld_compact_data,
    VALIDATE_PRIMITIVE_PROPERTY: validate_primitive_property,
}


def task_named(key):
    return functions[key]
