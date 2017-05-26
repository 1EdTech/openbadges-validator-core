from base64 import b64decode
import json
import jws

from ..actions.tasks import add_task
from ..exceptions import TaskPrerequisitesError
from ..state import get_node_by_id, get_node_by_path
from ..utils import list_of

from .utils import task_result
from .task_types import ISSUER_PROPERTY_DEPENDENCIES, JSONLD_COMPACT_DATA, VERIFY_JWS, VERIFY_KEY_OWNERSHIP


def process_jws_input(state, task_meta):
    try:
        data = task_meta['data']
    except KeyError:
        raise TaskPrerequisitesError()

    header, payload, signature = data.split('.')

    node_json = b64decode(payload)
    node_data = json.loads(node_json)
    node_id = task_meta.get('node_id', node_data.get('id'))

    actions = [
        add_task(JSONLD_COMPACT_DATA, data=node_json, node_id=node_id),
        add_task(VERIFY_JWS, node_id=node_id, data=data, prerequisites=ISSUER_PROPERTY_DEPENDENCIES)
    ]
    return task_result(True, "Processed JWS-signed data and queued signature verification task", actions)


def verify_jws_signature(state, task_meta):
    try:
        data = task_meta['data']
        node_id = task_meta['node_id']
        key_node = get_node_by_path(state, [node_id, 'verification', 'creator'])
        public_pem = key_node['publicKeyPem']
    except (KeyError, IndexError,):
        raise TaskPrerequisitesError()

    actions = [add_task(VERIFY_KEY_OWNERSHIP, node_id=node_id)]
    header, payload, signature = data.split('.')

    try:
        header_data = b64decode(header)
        payload_data = b64decode(payload)
    except TypeError:
        return task_result(
            False, "Signature for node {} failed to unpack into a predictable format".format(node_id))

    try:
        jws.verify(header_data, payload_data, signature, public_pem, is_json=True)
    except (jws.exceptions.SignatureError, TypeError):
        return task_result(
            False, "Signature for node {} failed verification".format(node_id), actions)

    return task_result(
        True, "Signature for node {} passed verification".format(node_id), actions)


def verify_key_ownership(state, task_meta):
    try:
        node_id = task_meta['node_id']
        issuer_node = get_node_by_path(state, [node_id, 'badge', 'issuer'])
        key_node = get_node_by_path(state, [node_id, 'verification', 'creator'])
        key_id = key_node['id']
    except (KeyError, IndexError,):
        raise TaskPrerequisitesError()

    issuer_keys = list_of(issuer_node.get('publicKey'))
    if key_id not in issuer_keys:
        return task_result(
            False,
            "Assertion signed by a key {} other than those authorized by issuer profile".format(key_id))

    return task_result(
        True, "Assertion signing key {} is properly declared in issuer profile".format(key_id))
