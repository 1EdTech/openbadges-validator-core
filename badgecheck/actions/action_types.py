"""
INPUT Actions:
Store and process user input via the API
"""
SET_INPUT_TYPE = 'SET_INPUT_TYPE'
SET_PROFILE_ID = 'SET_PROFILE_ID'
STORE_INPUT = 'STORE_INPUT'

"""
GRAPH Actions:
Manage the state of the known entities related to the validation subject.
"""
ADD_NODE = 'ADD_NODE'
PATCH_NODE = 'PATCH_NODE'
UPDATE_NODE = 'UPDATE_NODE'

"""
TASK Actions:
Add, update, and complete tasks.
"""
ADD_TASK = 'ADD_TASK'
UPDATE_TASK = 'UPDATE_TASK'
DELETE_TASK = 'DELETE_TASK'
RESOLVE_TASK = 'RESOLVE_TASK'
