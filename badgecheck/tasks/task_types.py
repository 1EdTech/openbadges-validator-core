"""
INPUT Tasks:
Process user input
"""
DETECT_INPUT_TYPE = 'DETECT_INPUT_TYPE'


"""
GRAPH Tasks:
Fetch, store, and process nodes in the graph related to validation input.
"""
FETCH_HTTP_NODE = 'FETCH_HTTP_NODE'
JSONLD_COMPACT_DATA = 'JSONLD_COMPACT_DATA'


"""
VALIDATION Tasks:
Ensure data is in good shape for relevant Open Badges objects and links between
objects are sound.
"""
DETECT_AND_VALIDATE_NODE_CLASS = 'DETECT_AND_VALIDATE_NODE_CLASS'
VALIDATE_EXPECTED_NODE_CLASS = 'VALIDATE_EXPECTED_NODE_CLASS'
VALIDATE_ID_PROPERTY = 'VALIDATE_ID_PROPERTY'
VALIDATE_PRIMITIVE_PROPERTY = 'VALIDATE_PRIMITIVE_PROPERTY'
