from action_types import SET_INPUT_TYPE, SET_PROFILE_ID, STORE_INPUT, STORE_ORIGINAL_RESOURCE


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
    if type_string not in ['file', 'json', 'jws', 'url']:
        raise TypeError("Only 'file', 'json', 'jws' or 'url' input types supported.")

    return {
        'type': SET_INPUT_TYPE,
        'input_type': type_string
    }


def store_expected_profile_id(profile_id):
    return {
        'type': SET_PROFILE_ID,
        'node_id': profile_id
    }


def store_original_resource(node_id, data=None, file=None):
    """
    Store a fetched blob of JSON, a JWS string, or an image file
    :param data: string
    :param file: file-like object
    :param node_id: string
    :return: dict
    """
    return {
        'type': STORE_ORIGINAL_RESOURCE,
        'data': data,
        'file': file,
        'node_id': node_id
    }
