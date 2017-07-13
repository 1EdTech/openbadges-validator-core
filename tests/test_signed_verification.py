from base64 import b64encode
from Crypto.PublicKey import RSA
import json
import jws
import responses
import unittest

from badgecheck.actions.graph import patch_node
from badgecheck.actions.tasks import add_task
from badgecheck.exceptions import TaskPrerequisitesError
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_URI
from badgecheck.reducers.graph import graph_reducer
from badgecheck.tasks.crypto import (process_jws_input, verify_key_ownership, verify_jws_signature,
                                     verify_signed_assertion_not_revoked,)
from badgecheck.tasks.task_types import (PROCESS_JWS_INPUT, VERIFY_JWS, VERIFY_KEY_OWNERSHIP,
                                         VERIFY_SIGNED_ASSERTION_NOT_REVOKED,)
from badgecheck.verifier import verify

from testfiles.test_components import test_components
from tests.utils import set_up_context_mock, set_up_image_mock


class JwsVerificationTests(unittest.TestCase):
    def setUp(self):
        self.private_key = RSA.generate(2048)
        self.signing_key_doc = {
            'id': 'http://example.org/key1',
            'type': 'CryptographicKey',
            'owner': 'http://example.org/issuer',
            'publicKeyPem': self.private_key.publickey().exportKey('PEM')
        }
        self.issuer_data = {
            'id': 'http://example.org/issuer',
            'publicKey': 'http://example.org/key1'
        }
        self.badgeclass = {
            'id': '_:b1',
            'issuer': 'http://example.org/issuer'
        }
        self.verification_object = {
            'id': '_:b0',
            'type': 'SignedBadge',
            'creator': 'http://example.org/key1'
        }
        self.assertion_data = {
            'id': 'urn:uuid:bf8d3c3d-fe60-487c-87a3-06440d0d0163',
            'verification': '_:b0',
            'badge': '_:b1'
        }

        header = {'alg': 'RS256'}
        payload = self.assertion_data
        signature = jws.sign(header, payload, self.private_key)
        self.signed_assertion = '.'.join((b64encode(json.dumps(header)), b64encode(json.dumps(payload)), signature))

        self.state = {
            'graph': [self.signing_key_doc, self.issuer_data, self.badgeclass,
                      self.verification_object, self.assertion_data]
        }

    def test_can_process_jws_input(self):
        task_meta = add_task(PROCESS_JWS_INPUT, data=self.signed_assertion)
        state = {}

        success, message, actions = process_jws_input(state, task_meta)
        self.assertTrue(success)
        self.assertEqual(len(actions), 3)

    def test_can_verify_jws(self):
        task_meta = add_task(VERIFY_JWS, data=self.signed_assertion,
                             node_id=self.assertion_data['id'])

        success, message, actions = verify_jws_signature(self.state, task_meta)
        self.assertTrue(success)
        self.assertEqual(len(actions), 2)

        # Construct an invalid signature by adding to payload after signing, one theoretical attack.
        header = {'alg': 'RS256'}
        signature = jws.sign(header, self.assertion_data, self.private_key)
        self.assertion_data['evidence'] = 'http://hahafakeinserteddata.com'
        self.signed_assertion = '.'.join(
            (b64encode(json.dumps(header)), b64encode(json.dumps(self.assertion_data)), signature)
        )
        task_meta = add_task(VERIFY_JWS, data=self.signed_assertion,
                             node_id=self.assertion_data['id'])

        success, message, actions = verify_jws_signature(self.state, task_meta)
        self.assertFalse(success)
        self.assertEqual(len(actions), 2)

    def test_can_verify_key_ownership(self):
        state = self.state
        task_meta = add_task(VERIFY_KEY_OWNERSHIP, node_id=self.assertion_data['id'])

        result, message, actions = verify_key_ownership(state, task_meta)
        self.assertTrue(result)

        del self.verification_object['creator']
        with self.assertRaises(TaskPrerequisitesError):
            verify_key_ownership(state, task_meta)

        self.verification_object['creator'] = 'http://nowhere.man'
        with self.assertRaises(TaskPrerequisitesError):
            verify_key_ownership(state, task_meta)

        self.verification_object['creator'] = self.signing_key_doc['id']
        self.issuer_data['publicKey'] = ['http://example.org/key2']
        result, message, actions = verify_key_ownership(state, task_meta)
        self.assertFalse(result)
        self.issuer_data['publicKey'] = [self.signing_key_doc['id'], 'http://example.org/key2']
        result, message, actions = verify_key_ownership(state, task_meta)
        self.assertTrue(result)
        self.assertEqual(len(actions), 0)

        self.issuer_data['revocationList'] = 'http://example.org/revocationList'
        result, message, actions = verify_key_ownership(state, task_meta)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1, "Revocation check task should be queued.")
        self.assertTrue(actions[0]['name'], VERIFY_SIGNED_ASSERTION_NOT_REVOKED)

    def test_can_verify_revoked(self):
        state = self.state
        revocation_list = {
            'id': 'http://example.org/revocationList',
            'type': 'RevocationList',
            'revokedAssertions': []
        }
        state['graph'] += [revocation_list]
        self.issuer_data['revocationList'] = revocation_list['id']

        task_meta = add_task(VERIFY_SIGNED_ASSERTION_NOT_REVOKED, node_id=self.assertion_data['id'])

        result, message, actions = verify_signed_assertion_not_revoked(state, task_meta)
        self.assertTrue(result)

        b123 = {'id': 'http://example.org/another', 'revocationReason': 'was imaginary'}
        revocation_list['revokedAssertions'] = [
            self.assertion_data['id'], 'http://example.org/else',
            'http://example.org/another'
        ]
        state['graph'].append(b123)
        result, message, actions = verify_signed_assertion_not_revoked(state, task_meta)
        self.assertFalse(result)

        revocation_entry = {
            'id': self.assertion_data['id'],
            'revocationReason': 'Tom got to pressing the award button again. Oh, Tom.'}
        revocation_list['revokedAssertions'].append(revocation_entry)
        result, message, actions = verify_signed_assertion_not_revoked(state, task_meta)
        self.assertFalse(result)
        self.assertIn(revocation_entry['revocationReason'], message)


class JwsFullVerifyTests(unittest.TestCase):
    @responses.activate
    def test_can_full_verify_jws_signed_assertion(self):
        """
        I can input a JWS string
        I can extract the Assertion from the input signature string and store it as the canonical version of the Assertion.
        I can discover and retrieve key information from the Assertion.
        I can Access the signing key
        I can verify the key is associated with the listed issuer Profile
        I can verify the JWS signature has been created by a key trusted to correspond to the issuer Profile
        Next: I can verify an assertion with an ephemeral embedded badgeclass as well
        """
        input_assertion = json.loads(test_components['2_0_basic_assertion'])
        input_assertion['verification'] = {'type': 'signed', 'creator': 'http://example.org/key1'}
        set_up_image_mock(u'https://example.org/beths-robot-badge.png')

        input_badgeclass = json.loads(test_components['2_0_basic_badgeclass'])
        set_up_image_mock(input_badgeclass['image'])

        input_issuer = json.loads(test_components['2_0_basic_issuer'])
        input_issuer['publicKey'] = input_assertion['verification']['creator']

        private_key = RSA.generate(2048)
        cryptographic_key_doc = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': input_assertion['verification']['creator'],
            'type': 'CryptographicKey',
            'owner': input_issuer['id'],
            'publicKeyPem': private_key.publickey().exportKey('PEM')
        }

        set_up_context_mock()
        for doc in [input_assertion, input_badgeclass, input_issuer, cryptographic_key_doc]:
            responses.add(responses.GET, doc['id'], json=doc, status=200)

        header = json.dumps({'alg': 'RS256'})
        payload = json.dumps(input_assertion)
        signature = '.'.join([
            b64encode(header),
            b64encode(payload),
            jws.sign(header, payload, private_key, is_json=True)
        ])

        response = verify(signature, use_cache=False)
        self.assertTrue(response['report']['valid'])

    @responses.activate
    def test_can_full_verify_with_revocation_check(self):
        input_assertion = json.loads(test_components['2_0_basic_assertion'])
        input_assertion['verification'] = {'type': 'signed', 'creator': 'http://example.org/key1'}
        set_up_image_mock(u'https://example.org/beths-robot-badge.png')

        input_badgeclass = json.loads(test_components['2_0_basic_badgeclass'])
        set_up_image_mock(input_badgeclass['image'])

        revocation_list = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.org/revocationList',
            'type': 'RevocationList',
            'revokedAssertions': []}
        input_issuer = json.loads(test_components['2_0_basic_issuer'])
        input_issuer['revocationList'] = revocation_list['id']
        input_issuer['publicKey'] = input_assertion['verification']['creator']

        private_key = RSA.generate(2048)
        cryptographic_key_doc = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': input_assertion['verification']['creator'],
            'type': 'CryptographicKey',
            'owner': input_issuer['id'],
            'publicKeyPem': private_key.publickey().exportKey('PEM')
        }

        set_up_context_mock()
        for doc in [input_assertion, input_badgeclass, input_issuer, cryptographic_key_doc, revocation_list]:
            responses.add(responses.GET, doc['id'], json=doc, status=200)

        header = json.dumps({'alg': 'RS256'})
        payload = json.dumps(input_assertion)
        signature = '.'.join([
            b64encode(header),
            b64encode(payload),
            jws.sign(header, payload, private_key, is_json=True)
        ])

        response = verify(signature, use_cache=False)
        self.assertTrue(response['report']['valid'])

    @responses.activate
    def test_revoked_badge_marked_invalid(self):
        input_assertion = json.loads(test_components['2_0_basic_assertion'])
        input_assertion['verification'] = {'type': 'signed', 'creator': 'http://example.org/key1'}

        input_badgeclass = json.loads(test_components['2_0_basic_badgeclass'])

        revocation_list = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.org/revocationList',
            'type': 'RevocationList',
            'revokedAssertions': [
                {'id': input_assertion['id'], 'revocationReason': 'A good reason, for sure'},
                {'id': 'urn:uuid:52e4c6b3-8c13-4fa8-8482-a5cf34ef37a9'},
                'urn:uuid:6deb4a00-ebce-4b28-8cc2-afa705ef7be4'
            ]
        }
        input_issuer = json.loads(test_components['2_0_basic_issuer'])
        input_issuer['revocationList'] = revocation_list['id']
        input_issuer['publicKey'] = input_assertion['verification']['creator']

        private_key = RSA.generate(2048)
        cryptographic_key_doc = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': input_assertion['verification']['creator'],
            'type': 'CryptographicKey',
            'owner': input_issuer['id'],
            'publicKeyPem': private_key.publickey().exportKey('PEM')
        }

        set_up_context_mock()
        for doc in [input_assertion, input_badgeclass, input_issuer, cryptographic_key_doc, revocation_list]:
            responses.add(responses.GET, doc['id'], json=doc, status=200)

        header = json.dumps({'alg': 'RS256'})
        payload = json.dumps(input_assertion)
        signature = '.'.join([
            b64encode(header),
            b64encode(payload),
            jws.sign(header, payload, private_key, is_json=True)
        ])

        response = verify(signature, use_cache=False)
        self.assertFalse(response['report']['valid'])
        msg = [a for a in response['report']['messages'] if a.get('name') == VERIFY_SIGNED_ASSERTION_NOT_REVOKED][0]
        self.assertIn('A good reason', msg['result'])

        # Assert pruning went well to eliminate revocationlist revokedAssertions except for the revoked one
        rev_list = [n for n in response['graph'] if n.get('id') == revocation_list['id']][0]
        self.assertEqual(len(rev_list['revokedAssertions']), 1)
        self.assertEqual(rev_list['revokedAssertions'], [revocation_list['revokedAssertions'][0]])


class GraphScrubbingTests(unittest.TestCase):
    def test_can_scrub_revocationlist_from_graph(self):
        assertion_data = {
            'id': 'urn:uuid:339e3b02-8b45-4948-b8d9-3589ec0f75d4',
            'type': 'Assertion',
            'badge': 'urn:uuid:6cd431ae-3155-4a81-b404-3bdc4d64b10d'
        }
        badgeclass_data = {
            'id': assertion_data['badge'],
            'type': 'BadgeClass',
            'issuer': 'http://example.org/issuer'
        }
        issuer_data = {
            'id': 'http://example.org/issuer',
            'type': 'Issuer',
            'revocationList': 'http://example.org/revocations'
        }
        revocation_list = {
            'id': 'http://example.org/revocations',
            'revokedAssertions': [
                'urn:uuid:1fac23b6-f1f7-46bd-9247-b1a94c3f8aaa',
                'urn:uuid:486590d2-89ec-4f71-9c1e-63d1be796a95',
                {'uid': 'abc123'}
            ]
        }
        graph = [assertion_data, badgeclass_data, issuer_data, revocation_list]

        action = patch_node(revocation_list['id'], {'revokedAssertions': []})
        new_graph = graph_reducer(graph, action)

        self.assertEqual(len(new_graph), 4)
        rev_list = [n for n in new_graph if n['id'] == revocation_list['id']][0]
        self.assertEqual(rev_list['revokedAssertions'], [])
