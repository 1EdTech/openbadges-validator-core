from .crypto import (process_jws_input, verify_jws_signature, verify_key_ownership,
                     verify_signed_assertion_not_revoked,)
from .extensions import validate_extension_node
from .images import validate_image
from .input import detect_input_type
from .graph import fetch_http_node, flatten_refetch_embedded_resource, intake_json, jsonld_compact_data
from .object_upgrades import upgrade_1_0_node, upgrade_1_1_node
from .validation import (assertion_timestamp_checks, assertion_verification_dependencies,
                         criteria_property_dependencies, detect_and_validate_node_class,
                         identity_object_property_dependencies, issuer_property_dependencies, placeholder_task,
                         validate_expected_node_class, validate_rdf_type_property, validate_property,
                         validate_revocationlist_entries, )
from .verification import (hosted_id_in_verification_scope, verify_recipient_against_trusted_profile)
from .task_types import *


FUNCTIONS = {
    ASSERTION_TIMESTAMP_CHECKS:                assertion_timestamp_checks,
    ASSERTION_VERIFICATION_CHECK:              placeholder_task,
    ASSERTION_VERIFICATION_DEPENDENCIES:       assertion_verification_dependencies,
    DETECT_AND_VALIDATE_NODE_CLASS:            detect_and_validate_node_class,
    DETECT_INPUT_TYPE:                         detect_input_type,
    CRITERIA_PROPERTY_DEPENDENCIES:            criteria_property_dependencies,
    FETCH_HTTP_NODE:                           fetch_http_node,
    FLATTEN_EMBEDDED_RESOURCE:                 flatten_refetch_embedded_resource,
    HOSTED_ID_IN_VERIFICATION_SCOPE:           hosted_id_in_verification_scope,
    JSONLD_COMPACT_DATA:                       jsonld_compact_data,
    IDENTITY_OBJECT_PROPERTY_DEPENDENCIES:     identity_object_property_dependencies,
    INTAKE_JSON:                               intake_json,
    ISSUER_PROPERTY_DEPENDENCIES:              issuer_property_dependencies,
    PROCESS_JWS_INPUT:                         process_jws_input,
    UPGRADE_1_0_NODE:                          upgrade_1_0_node,
    UPGRADE_1_1_NODE:                          upgrade_1_1_node,
    VALIDATE_EXPECTED_NODE_CLASS:              validate_expected_node_class,
    VALIDATE_EXTENSION_NODE:                   validate_extension_node,
    IMAGE_VALIDATION:                          validate_image,
    VALIDATE_RDF_TYPE_PROPERTY:                validate_rdf_type_property,
    VALIDATE_PROPERTY:                         validate_property,
    VALIDATE_REVOCATIONLIST_ENTRIES:           validate_revocationlist_entries,
    VERIFY_JWS:                                verify_jws_signature,
    VERIFY_KEY_OWNERSHIP:                      verify_key_ownership,
    VERIFY_RECIPIENT_IDENTIFIER:               verify_recipient_against_trusted_profile,
    VERIFY_SIGNED_ASSERTION_NOT_REVOKED:       verify_signed_assertion_not_revoked,
}


def task_named(key):
    return FUNCTIONS[key]
