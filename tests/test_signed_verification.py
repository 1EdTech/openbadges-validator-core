from base64 import b64encode
from Crypto.PublicKey import RSA
import json
import jws
import responses
import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.exceptions import TaskPrerequisitesError
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_URI
from badgecheck.tasks.crypto import (process_jws_input, verify_key_ownership, verify_jws_signature,
                                     verify_signed_assertion_not_revoked,)
from badgecheck.tasks.task_types import (PROCESS_JWS_INPUT, VERIFY_JWS, VERIFY_KEY_OWNERSHIP,
                                         VERIFY_SIGNED_ASSERTION_NOT_REVOKED,)
from badgecheck.verifier import verify

from testfiles.test_components import test_components
from tests.utils import setUpContextMock


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
        self.assertEqual(len(actions), 2)

    def test_can_verify_jws(self):
        task_meta = add_task(VERIFY_JWS, data=self.signed_assertion,
                             node_id=self.assertion_data['id'])

        success, message, actions = verify_jws_signature(self.state, task_meta)
        self.assertTrue(success)
        self.assertEqual(len(actions), 2)

        # Construct an invalid signature by adding to payload after signing, one theoretical attack.
        header = {'alg': 'RS256'}
        signature = jws.sign(header, self.assertion_data, self.private_key)
        self.assertion_data['evidence'] = 'http://hahafakeinserteddata'
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

        revocation_list['revokedAssertions'] = [
            self.assertion_data['id'], 'http://example.org/else',
            {'id': 'http://example.org/another', 'revocationReason': 'was imaginary'}
        ]
        result, message, actions = verify_signed_assertion_not_revoked(state, task_meta)
        self.assertFalse(result)

        revocation_list['revokedAssertions'][0] = {
            'id': self.assertion_data['id'],
            'revocationReason': 'Tom got to pressing the award button again. Oh, Tom.'}
        result, message, actions = verify_signed_assertion_not_revoked(state, task_meta)
        self.assertFalse(result)
        self.assertIn(revocation_list['revokedAssertions'][0]['revocationReason'], message)


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

        input_badgeclass = json.loads(test_components['2_0_basic_badgeclass'])

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

        setUpContextMock()
        for doc in [input_assertion, input_badgeclass, input_issuer, cryptographic_key_doc]:
            responses.add(responses.GET, doc['id'], json=doc, status=200)

        header = json.dumps({'alg': 'RS256'})
        payload = json.dumps(input_assertion)
        signature = '.'.join([
            b64encode(header),
            b64encode(payload),
            jws.sign(header, payload, private_key, is_json=True)
        ])

        response = verify(signature)
        self.assertTrue(response['valid'])

    @responses.activate
    def test_can_full_verify_with_revocation_check(self):
        input_assertion = json.loads(test_components['2_0_basic_assertion'])
        input_assertion['verification'] = {'type': 'signed', 'creator': 'http://example.org/key1'}

        input_badgeclass = json.loads(test_components['2_0_basic_badgeclass'])

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

        setUpContextMock()
        for doc in [input_assertion, input_badgeclass, input_issuer, cryptographic_key_doc, revocation_list]:
            responses.add(responses.GET, doc['id'], json=doc, status=200)

        header = json.dumps({'alg': 'RS256'})
        payload = json.dumps(input_assertion)
        signature = '.'.join([
            b64encode(header),
            b64encode(payload),
            jws.sign(header, payload, private_key, is_json=True)
        ])

        response = verify(signature)
        self.assertTrue(response['valid'])
