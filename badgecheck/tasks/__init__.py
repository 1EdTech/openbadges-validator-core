from input import detect_input_type
from graph import fetch_http_node, jsonld_compact_data
from task_types import (DETECT_INPUT_TYPE, FETCH_HTTP_NODE, JSONLD_COMPACT_DATA)


functions = {
    DETECT_INPUT_TYPE: detect_input_type,
    FETCH_HTTP_NODE: fetch_http_node,
    JSONLD_COMPACT_DATA: jsonld_compact_data
}


def task_named(key):
    return functions[key]
