from base64 import b64encode
from Crypto.PublicKey import RSA
import json
import jws
from pydux import create_store
import responses
import unittest

from badgecheck.actions.input import set_input_type, store_input
from badgecheck.reducers import main_reducer
from badgecheck.state import INITIAL_STATE
from badgecheck.tasks.input import detect_input_type

from testfiles.test_components import test_components

from tests.utils import set_up_context_mock


class InputReducerTests(unittest.TestCase):
    def setUp(self):
        self.store = create_store(main_reducer, INITIAL_STATE)

    def test_store_input(self):
        self.store.dispatch(store_input("http://example.com/url1"))
        self.assertEqual(self.store.get_state().get('input').get('value'), 'http://example.com/url1')

    def test_set_input_type(self):
        self.store.dispatch(store_input("http://example.com/url1"))
        self.store.dispatch(set_input_type('url'))
        self.assertEqual(self.store.get_state().get('input').get('input_type'), 'url')


class InputTaskTests(unittest.TestCase):
    def test_input_url_type_detection(self):
        """
        The detect_input_type task should successfully detect
        """
        url = 'http://example.com/assertionmaybe'
        state = INITIAL_STATE.copy()
        state['input']['value'] = url

        success, message, actions = detect_input_type(state)

        self.assertTrue(success)
        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0]['type'], 'SET_INPUT_TYPE')
        self.assertEqual(actions[1]['url'], url)

    def test_input_jsonld_type_detection_replaces_with_url(self):
        """
        The detect_input_type task should successfully detect JSONLD with an id URL
        as input and switch to using an 'id' as URL value if possible
        """
        json_input = test_components['2_0_basic_assertion']
        state = INITIAL_STATE.copy()
        state['input']['value'] = json_input

        success, message, actions = detect_input_type(state)

        self.assertTrue(success)
        self.assertEqual(len(actions), 4)
        self.assertEqual(actions[0]['type'], 'STORE_INPUT')
        self.assertEqual(actions[1]['type'], 'SET_INPUT_TYPE')
        self.assertEqual(actions[2]['type'], 'ADD_TASK')
        self.assertEqual(actions[2]['name'], 'FETCH_HTTP_NODE')

        self.assertEqual(actions[0]['input'], actions[2]['url'])
        self.assertEqual(json.loads(json_input)['id'], actions[2]['url'])

    def test_input_jsonld_type_detection_preserves_json(self):
        """
        If the detect_input_type_task can't find an id field as a URL, it preserves
        the input as json
        """
        assertion_dict = json.loads(test_components['2_0_basic_assertion'])
        assertion_dict['id'] = assertion_dict['badge'] = u'urn:org:example:badges:robotics:beth'
        json_input = json.dumps(assertion_dict)
        state = INITIAL_STATE.copy()
        state['input']['value'] = json_input

        success, message, actions = detect_input_type(state)

        self.assertTrue(success)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'SET_INPUT_TYPE')
        self.assertEqual(actions[0]['input_type'], 'json')


class InputJwsTests(unittest.TestCase):
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

    @responses.activate
    def test_detect_jws_signed_input_type(self):
        set_up_context_mock()
        # responses.add(responses.GET, badgeclass_data['id'], json=badgeclass_data, status=200)
        # responses.add(responses.GET, issuer_data['id'], json=issuer_data, status=200)
        # responses.add(responses.GET, signing_key['id'], json=signing_key, status=200)

        state = INITIAL_STATE.copy()
        state['input']['value'] = self.signed_assertion

        success, message, actions = detect_input_type(state)

        self.assertTrue(success)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['input_type'], 'jws')
