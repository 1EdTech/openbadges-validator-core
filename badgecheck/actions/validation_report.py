from .action_types import (RUN_VALIDATION_REPORT, SET_OPENBADGES_VERSION, SET_VALIDATION_SUBJECT,
                           SET_VERIFIED_PROFILE)


def run_validation_report():
    return {
        'type': RUN_VALIDATION_REPORT
    }


def set_openbadges_version(version_string):
    """
    Set the version of the node that is the subject of the present validation request/report.
    :param version_string: One of ("0.5", "1.0", "1.1", "2.0")
    :return: dict
    """
    known_versions = ("0.5", "1.0", "1.1", "2.0")

    if version_string not in known_versions:
        raise ValueError("version {} not among known versions")

    return {
        'type': SET_OPENBADGES_VERSION,
        'version': version_string
    }


def set_validation_subject(node_id):
    """
    Set the ID of the node in the graph that is the subject of the present validation request/report.
    :param node_id: 
    :return: dict
    """
    return {
        'type': SET_VALIDATION_SUBJECT,
        'node_id': node_id
    }


def set_verified_recipient_profile(id_type, confirmed_id):
    """
    :param type: str
    :param value: str
    :return: dict
    """
    return {
        'type': SET_VERIFIED_PROFILE,
        'identityType': id_type,
        'identityValue': confirmed_id
    }
