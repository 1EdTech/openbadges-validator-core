from .extensions import validate_extension_node
from .input import detect_input_type
from .graph import fetch_http_node, jsonld_compact_data
from .validation import (assertion_timestamp_checks, assertion_verification_dependencies,
                        criteria_property_dependencies, detect_and_validate_node_class,
                        identity_object_property_dependencies, issuer_property_dependencies,
                        validate_expected_node_class, validate_rdf_type_property, validate_property,)
from .verification import (hosted_id_in_verification_scope,)
from .task_types import *


FUNCTIONS = {
    ASSERTION_TIMESTAMP_CHECKS:                assertion_timestamp_checks,
    ASSERTION_VERIFICATION_DEPENDENCIES:       assertion_verification_dependencies,
    DETECT_AND_VALIDATE_NODE_CLASS:            detect_and_validate_node_class,
    DETECT_INPUT_TYPE:                         detect_input_type,
    CRITERIA_PROPERTY_DEPENDENCIES:            criteria_property_dependencies,
    FETCH_HTTP_NODE:                           fetch_http_node,
    HOSTED_ID_IN_VERIFICATION_SCOPE:           hosted_id_in_verification_scope,
    JSONLD_COMPACT_DATA:                       jsonld_compact_data,
    IDENTITY_OBJECT_PROPERTY_DEPENDENCIES:     identity_object_property_dependencies,
    ISSUER_PROPERTY_DEPENDENCIES:              issuer_property_dependencies,
    VALIDATE_EXPECTED_NODE_CLASS:              validate_expected_node_class,
    VALIDATE_EXTENSION_NODE:                   validate_extension_node,
    VALIDATE_RDF_TYPE_PROPERTY:                validate_rdf_type_property,
    VALIDATE_PROPERTY:                         validate_property,
}


def task_named(key):
    return FUNCTIONS[key]
