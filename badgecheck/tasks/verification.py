import rfc3986

from ..actions.tasks import report_message
from ..actions.validation_report import set_verified_recipient_profile
from ..exceptions import TaskPrerequisitesError
from ..state import get_node_by_id, get_node_by_path
from ..utils import identity_hash, list_of

from .utils import abbreviate_value as abv, task_result


def _default_allowed_origins_for_issuer_id(issuer_id):
    return rfc3986.uri_reference(issuer_id).authority


def _default_verification_policy(issuer_node):
    issuer_id = issuer_node.get('id')
    return {
        'type': 'VerificationObject',
        'allowedOrigins': _default_allowed_origins_for_issuer_id(issuer_id),
        'verificationProperty': 'id'
    }


def hosted_id_in_verification_scope(state, task_meta, **options):
    try:
        assertion_id = task_meta.get('node_id')
        assertion_node = get_node_by_id(state, assertion_id)

        badgeclass_node = get_node_by_id(state, assertion_node['badge'])
        issuer_node = get_node_by_id(state, badgeclass_node['issuer'])
    except IndexError:
        raise TaskPrerequisitesError()

    try:
        verification_policy = get_node_by_id(state, issuer_node.get('verification'))
    except IndexError:
        verification_policy = _default_verification_policy(issuer_node)

    if verification_policy.get('startsWith'):
        starts_with = list_of(verification_policy['startsWith'])
        if not any([assertion_id.startswith(i) for i in starts_with]):
            return task_result(
                False, "Assertion id {}".format(assertion_id) +
                "does not start with any permitted values in its issuer's verification policy."
            )

    allowed_origins = list_of(
        verification_policy.get(
            'allowedOrigins', _default_allowed_origins_for_issuer_id(issuer_node.get('id')))
    )
    if allowed_origins and rfc3986.uri_reference(assertion_id).authority not in allowed_origins:
        return task_result(
            False, 'Assertion {} not hosted in allowed origins {}'.format(
                abv(assertion_id), abv(allowed_origins))
        )

    return task_result(
        True, 'Assertion {} origin matches allowed value in issuer verification policy {}.'.format(
            abv(assertion_id), abv(allowed_origins))
    )


def _matches_hash(profile_identifier, id_hash, salt=''):
    if id_hash.startswith('md5'):
        return identity_hash(profile_identifier, salt, alg='md5') == id_hash
    elif id_hash.startswith('sha256'):
        return identity_hash(profile_identifier, salt, alg='sha256') == id_hash

    raise TypeError("Cannot interpret hash type of {}".format(id_hash))


def verify_recipient_against_trusted_profile(state, task_meta, **options):
    try:
        # Use the ID of the first Assertion found in current state
        assertion_id = [n for n in state['graph'] if n.get('type') == 'Assertion'][0]['id']

        identity_node = get_node_by_path(state, [assertion_id, 'recipient'])
        profile_id = task_meta['node_id']
        profile_node = get_node_by_id(state, profile_id)
    except (IndexError, KeyError):
        raise TaskPrerequisitesError()

    actions = []

    a = identity_node['identity']  # Recipient value in (a)ssertion
    recipient_type = identity_node['type']
    if recipient_type not in ['id', 'email', 'url', 'telephone']:
        actions += [report_message(
            "Recipient identifier type {} in assertion {} is not one of the recommended types".format(
                recipient_type, assertion_id))]

    try:
        p = list_of(profile_node[recipient_type])  # matching type recipient value in submitted (p)rofile
    except KeyError:
        return task_result(
            False, "Profile identifier property of type {} not found in submitted profile {}".format(
                recipient_type, profile_id
            ), actions)

    if identity_node['hashed']:
        salt = identity_node.get('salt', '')
        for possible_id in p:
            if _matches_hash(possible_id, a, salt):
                confirmed_id = possible_id
                break
        else:
            # If no identifier in the profile matches, return failure
            return task_result(
                False,
                "Profile {} identifier(s) {} of type {} did not match assertion {} recipient hash {}.".format(
                    abv(profile_id), abv(p), recipient_type, abv(assertion_id), a),
                actions)
    elif a in p:
        confirmed_id = a
    else:
        return task_result(
            False,
            "Profile {} identifier {} of type {} did not match assertion {} recipient value {}".format(
                abv(profile_id), p, recipient_type, abv(assertion_id), a),
            actions)

    actions.append(set_verified_recipient_profile(recipient_type, confirmed_id))
    return task_result(True, "Assertion {} awarded to trusted profile identifier {} of type {}".format(
        abv(assertion_id), confirmed_id, recipient_type), actions)
