from input import detect_input_type
from graph import fetch_http_node, jsonld_compact_data
from validation import (criteria_property_dependencies, detect_and_validate_node_class,
                        evidence_property_dependencies, identity_object_property_dependencies,
                        validate_expected_node_class, validate_id_property, validate_primitive_property,)
from task_types import (DETECT_AND_VALIDATE_NODE_CLASS, DETECT_INPUT_TYPE, CRITERIA_PROPERTY_DEPENDENCIES,
                        EVIDENCE_PROPERTY_DEPENDENCIES, FETCH_HTTP_NODE, JSONLD_COMPACT_DATA,
                        IDENTITY_OBJECT_PROPERTY_DEPENDENCIES, VALIDATE_EXPECTED_NODE_CLASS,
                        VALIDATE_ID_PROPERTY, VALIDATE_PRIMITIVE_PROPERTY, )


FUNCTIONS = {
    DETECT_AND_VALIDATE_NODE_CLASS: detect_and_validate_node_class,
    DETECT_INPUT_TYPE: detect_input_type,
    CRITERIA_PROPERTY_DEPENDENCIES: criteria_property_dependencies,
    EVIDENCE_PROPERTY_DEPENDENCIES: evidence_property_dependencies,
    FETCH_HTTP_NODE: fetch_http_node,
    JSONLD_COMPACT_DATA: jsonld_compact_data,
    IDENTITY_OBJECT_PROPERTY_DEPENDENCIES: identity_object_property_dependencies,
    VALIDATE_EXPECTED_NODE_CLASS: validate_expected_node_class,
    VALIDATE_ID_PROPERTY: validate_id_property,
    VALIDATE_PRIMITIVE_PROPERTY: validate_primitive_property,
}


def task_named(key):
    return FUNCTIONS[key]
