from action_types import SET_INPUT_TYPE, SET_PROFILE_ID, STORE_INPUT


def store_input(badge_input):
    """
    Emits an action that encapsulates user input provided and instructs that it
    be stored in the state.
    :param badge_input: string
    :return: dict
    """
    return {
        'type': STORE_INPUT,
        'input': badge_input
    }


def set_input_type(type_string):
    """
    Emits an action that indicates the type of input provided.
    Options: "url", "json", "jws"
    :param input_type: string
    :return: dict
    """
    if type_string not in ['url', 'json', 'jws']:
        raise TypeError("Only 'url', 'json', or 'jws' input types supported.")

    return {
        'type': SET_INPUT_TYPE,
        'input_type': type_string
    }


def store_expected_profile_id(profile_id):
    return {
        'type': SET_PROFILE_ID,
        'node_id': profile_id
    }