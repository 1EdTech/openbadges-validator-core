from Crypto.PublicKey import RSA
from jose import jwk, jws, exceptions as joseexceptions
import json
import six

from ..actions.graph import patch_node
from ..actions.tasks import add_task
from ..actions.validation_report import set_validation_subject
from ..exceptions import TaskPrerequisitesError
from ..state import get_node_by_id, get_node_by_path
from ..utils import list_of, make_string_from_bytes

from .utils import task_result
from .task_types import (ISSUER_PROPERTY_DEPENDENCIES, INTAKE_JSON, SIGNING_KEY_FETCHED, VERIFY_JWS,
                         VERIFY_KEY_OWNERSHIP, VALIDATE_PROPERTY, VALIDATE_REVOCATIONLIST_ENTRIES,
                         VERIFY_SIGNED_ASSERTION_NOT_REVOKED)
from .validation import OBClasses, ValueTypes


def process_jws_input(state, task_meta, **options):
    try:
        data = task_meta['data']
    except KeyError:
        raise TaskPrerequisitesError()

    node_json = jws.get_unverified_claims(data).decode('utf-8')
    node_data = json.loads(node_json)
    node_id = task_meta.get('node_id', node_data.get('id'))
    depth = task_meta.get('depth')

    actions = [
        add_task(INTAKE_JSON, data=node_json, node_id=node_id, depth=depth),
        add_task(VERIFY_JWS, node_id=node_id, data=data, prerequisites=SIGNING_KEY_FETCHED, depth=depth)
    ]
    if node_id:
        actions.append(set_validation_subject(node_id))
    return task_result(True, "Processed JWS-signed data and queued signature verification task", actions)


def verify_jws_signature(state, task_meta, **options):
    try:
        data = task_meta['data']
        node_id = task_meta['node_id']
        key_node = get_node_by_path(state, [node_id, 'verification', 'creator'])
        public_pem = key_node['publicKeyPem']
        depth = task_meta['depth']
    except (KeyError, IndexError,):
        raise TaskPrerequisitesError()

    actions = [
        add_task(VERIFY_KEY_OWNERSHIP, node_id=node_id, depth=depth),
        add_task(
            VALIDATE_PROPERTY, node_path=[node_id, 'badge', 'issuer'], prop_name='revocationList',
            prop_type=ValueTypes.ID, expected_class=OBClasses.RevocationList, fetch=True, required=False,
            prerequisites=[ISSUER_PROPERTY_DEPENDENCIES], depth=depth
        ),
    ]

    key = RSA.import_key(public_pem)
    jwkkey = jwk.construct(key, 'RS256').to_dict()

    try:
        jws.verify(data, jwkkey, None)
    except (joseexceptions.JWSError, joseexceptions.JWSSignatureError,) as e:
        return task_result(
            False, "Signature for node {} failed verification".format(node_id) + " :: " + str(e), actions)

    return task_result(
        True, "Signature for node {} passed verification".format(node_id), actions)


def verify_key_ownership(state, task_meta, **options):
    try:
        node_id = task_meta['node_id']
        issuer_node = get_node_by_path(state, [node_id, 'badge', 'issuer'])
        key_node = get_node_by_path(state, [node_id, 'verification', 'creator'])
        key_id = key_node['id']
        depth = task_meta['depth']
    except (KeyError, IndexError,):
        raise TaskPrerequisitesError()

    actions = []
    if issuer_node.get('revocationList'):
        actions.append(add_task(
            VERIFY_SIGNED_ASSERTION_NOT_REVOKED,
            node_id=node_id,
            prerequisites=[VALIDATE_REVOCATIONLIST_ENTRIES],
            depth=depth
        ))

    issuer_keys = list_of(issuer_node.get('publicKey'))
    if key_id not in issuer_keys:
        return task_result(
            False,
            "Assertion signed by a key {} other than those authorized by issuer profile".format(key_id),
            actions)

    return task_result(
        True, "Assertion signing key {} is properly declared in issuer profile".format(key_id), actions)


def verify_signed_assertion_not_revoked(state, task_meta, **options):
    try:
        assertion_id = task_meta['node_id']
        issuer = get_node_by_path(state, [assertion_id, 'badge', 'issuer'])
    except (IndexError, KeyError, TypeError,):
        raise TaskPrerequisitesError()

    if not issuer.get('revocationList'):
        return task_result(True, 'Assertion {} is not revoked. Issuer {} has no revocation list'.format(
            assertion_id, issuer.get('id')
        ))

    revocation_list = get_node_by_id(state, issuer['revocationList'])
    revoked_assertions = revocation_list['revokedAssertions']

    def _is_match(term, container):
        if isinstance(container, six.string_types):
            return term == container
        return container.get('id') == term

    revoked_match = [a for a in revoked_assertions if _is_match(assertion_id, a)]

    actions = [patch_node(revocation_list['id'], {'revokedAssertions': revoked_match})]

    if len(revoked_match):
        assertion_records = [i for i in state['graph'] if i.get('id') == assertion_id]
        msg = ''
        for a in revoked_match:
            try:
                msg = ' with reason: ' + a['revocationReason']
            except (KeyError, TypeError,):
                continue

        return task_result(False, "Assertion {} has been revoked in RevocationList {}{}".format(
            assertion_id, issuer['revocationList'], msg
        ), actions)

    return task_result(True, "Assertion {} is not marked as revoked in RevocationList {}".format(
        assertion_id, issuer['revocationList']
    ), actions)
