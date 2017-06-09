from ..actions.action_types import (RUN_VALIDATION_REPORT, SET_OPENBADGES_VERSION, SET_VALIDATION_SUBJECT,
                                    SET_VERIFIED_PROFILE)


def verification_report_reducer(state, action):
    if state is None:
        state = {}

    action_type = action.get('type')
    if action_type == RUN_VALIDATION_REPORT:
        # TODO
        return state
    elif action_type == SET_OPENBADGES_VERSION:
        state = state.copy()
        state['openBadgesVersion'] = action.get('version')
    elif action_type == SET_VALIDATION_SUBJECT:
        state = state.copy()
        state['validationSubject'] = action.get('node_id')
    elif action_type == SET_VERIFIED_PROFILE:
        state = state.copy()
        state['recipientProfile'] = {
            action.get('identityType', 'email'): action.get('identityValue')
        }

    return state
