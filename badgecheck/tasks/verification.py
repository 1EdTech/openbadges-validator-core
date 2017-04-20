import rfc3986

from ..state import get_node_by_id
from ..utils import cast_as_list

from .utils import abbreviate_value, task_result


def _default_allowed_origins_for_issuer_id(issuer_id):
    return rfc3986.uri_reference(issuer_id).authority


def _default_verification_policy(issuer_node):
    issuer_id = issuer_node.get('id')
    return {
        'type': 'VerificationObject',
        'allowedOrigins': _default_allowed_origins_for_issuer_id(issuer_id),
        'verificationProperty': 'id'
    }


def hosted_id_in_verification_scope(state, task_meta):
    assertion_id = task_meta.get('node_id')
    assertion_node = get_node_by_id(state, assertion_id)

    badgeclass_node = get_node_by_id(state, assertion_node['badge'])
    issuer_node = get_node_by_id(state, badgeclass_node['issuer'])

    try:
        verification_policy = get_node_by_id(state, issuer_node.get('verification'))
    except IndexError:
        verification_policy = _default_verification_policy(issuer_node)

    if verification_policy.get('startsWith'):
        starts_with = cast_as_list(verification_policy['startsWith'])
        if not any([assertion_id.startswith(i) for i in starts_with]):
            return task_result(
                False, "Assertion id {}".format(assertion_id) +
                "does not start with any permitted values in its issuer's verification policy."
            )

    allowed_origins = cast_as_list(
        verification_policy.get(
            'allowedOrigins', _default_allowed_origins_for_issuer_id(issuer_node.get('id')))
    )
    if allowed_origins and rfc3986.uri_reference(assertion_id).authority not in allowed_origins:
        return task_result(
            False, 'Assertion {} not hosted in allowed origins {}'.format(
                abbreviate_value(assertion_id), abbreviate_value(allowed_origins))
        )

    return task_result(
        True, 'Assertion {} origin matches allowed value in issuer verification policy {}.'.format(
            abbreviate_value(assertion_id), abbreviate_value(allowed_origins))
    )


