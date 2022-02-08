"""
INPUT Tasks:
Process user input
"""
DETECT_INPUT_TYPE = 'DETECT_INPUT_TYPE'
PROCESS_BAKED_RESOURCE = 'PROCESS_BAKED_RESOURCE'

"""
GRAPH Tasks:
Fetch, store, and process nodes in the graph related to validation input.
"""
FETCH_HTTP_NODE = 'FETCH_HTTP_NODE'
INTAKE_JSON = 'INTAKE_JSON'
JSONLD_COMPACT_DATA = 'JSONLD_COMPACT_DATA'
PROCESS_JWS_INPUT = 'PROCESS_JWS_INPUT'
PROCESS_410_GONE = 'PROCESS_410_GONE'


"""
OPENBADGES OBJECT Tasks
"""
UPGRADE_0_5_NODE = 'UPGRADE_0_5_NODE'
UPGRADE_1_0_NODE = 'UPGRADE_1_0_NODE'
UPGRADE_1_1_NODE = 'UPGRADE_1_1_NODE'

UPGRADE_TASKS = [UPGRADE_0_5_NODE, UPGRADE_1_0_NODE, UPGRADE_1_1_NODE]


"""
VALIDATION Tasks:
Ensure data is in good shape for relevant Open Badges objects and links between
objects are sound.
"""
DETECT_AND_VALIDATE_NODE_CLASS = 'DETECT_AND_VALIDATE_NODE_CLASS'
VALIDATE_EXPECTED_NODE_CLASS = 'VALIDATE_EXPECTED_NODE_CLASS'
VALIDATE_RDF_TYPE_PROPERTY = 'VALIDATE_RDF_TYPE_PROPERTY'
VALIDATE_PROPERTY = 'VALIDATE_PROPERTY'

# Class Level Validation Tasks
ASSERTION_TIMESTAMP_CHECKS = 'ASSERTION_TIMESTAMP_CHECKS'
ASSERTION_VERIFICATION_CHECK = 'ASSERTION_VERIFICATION_CHECK'
ASSERTION_VERIFICATION_DEPENDENCIES = 'ASSERTION_VERIFICATION_DEPENDENCIES'
CRITERIA_PROPERTY_DEPENDENCIES = 'CRITERIA_PROPERTY_DEPENDENCIES'
FLATTEN_EMBEDDED_RESOURCE = 'FLATTEN_EMBEDDED_RESOURCE'
IDENTITY_OBJECT_PROPERTY_DEPENDENCIES = 'IDENTITY_OBJECT_PROPERTY_DEPENDENCIES'
IMAGE_VALIDATION = 'IMAGE_VALIDATION'
ISSUER_PROPERTY_DEPENDENCIES = 'ISSUER_PROPERTY_DEPENDENCIES'
VALIDATE_EXTENSION_NODE = 'VALIDATE_EXTENSION_NODE'
VALIDATE_EXTENSION_SINGLE = 'VALIDATE_EXTENSION_SINGLE'
VALIDATE_REVOCATIONLIST_ENTRIES = 'VALIDATE_REVOCATIONLIST_ENTRIES'
VERIFY_JWS = 'VERIFY_JWS'
VERIFY_KEY_OWNERSHIP = 'VERIFY_KEY_OWNERSHIP'


"""
VERIFICATION Tasks:
Ensure values are congruent with one another and that relevant verification
rules in the Open Badges Specification are met.
"""
HOSTED_ID_IN_VERIFICATION_SCOPE = 'HOSTED_ID_IN_VERIFICATION_SCOPE'
VERIFY_RECIPIENT_IDENTIFIER = 'VERIFY_RECIPIENT_IDENTIFIER'
VERIFY_SIGNED_ASSERTION_NOT_REVOKED = 'VERIFY_SIGNED_ASSERTION_NOT_REVOKED'


CLASS_VALIDATION_TASKS = (ASSERTION_TIMESTAMP_CHECKS, ASSERTION_VERIFICATION_CHECK,
                          ASSERTION_VERIFICATION_DEPENDENCIES, CRITERIA_PROPERTY_DEPENDENCIES,
                          FLATTEN_EMBEDDED_RESOURCE, IDENTITY_OBJECT_PROPERTY_DEPENDENCIES,
                          IMAGE_VALIDATION, ISSUER_PROPERTY_DEPENDENCIES,
                          VALIDATE_REVOCATIONLIST_ENTRIES, VERIFY_RECIPIENT_IDENTIFIER)


"""
TRIGGERED CONDITIONS
These conditions may be used as prerequisites in other tasks.
"""
SIGNING_KEY_FETCHED = 'SIGNING_KEY_FETCHED'
