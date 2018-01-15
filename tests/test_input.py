from base64 import b64encode
from Crypto.PublicKey import RSA
import json
import jws
import os
from pydux import create_store
import responses
import unittest
import sys

from openbadges.verifier.actions.input import set_input_type, store_input
from openbadges.verifier.actions.action_types import SET_VALIDATION_SUBJECT, STORE_INPUT, STORE_ORIGINAL_RESOURCE
from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.tasks.task_types import DETECT_INPUT_TYPE
from openbadges.verifier.reducers import main_reducer
from openbadges.verifier.state import INITIAL_STATE
from openbadges.verifier.tasks import run_task
from openbadges.verifier.tasks.input import detect_input_type, process_baked_resource
from openbadges.verifier.tasks.task_types import FETCH_HTTP_NODE, PROCESS_BAKED_RESOURCE
from openbadges.verifier.utils import MESSAGE_LEVEL_ERROR
from openbadges_bakery import bake

try:
    from tests.testfiles.test_components import test_components
    from tests.utils import set_up_context_mock
except (ImportError, SystemError):
    from .testfiles.test_components import test_components
    from .utils import set_up_context_mock


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

        success, message, actions = detect_input_type(state, {})

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

        success, message, actions = detect_input_type(state, {})

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
        assertion_dict['id'] = assertion_dict['badge'] = 'urn:org:example:badges:robotics:beth'
        json_input = json.dumps(assertion_dict)
        state = INITIAL_STATE.copy()
        state['input']['value'] = json_input

        success, message, actions = detect_input_type(state, {})

        self.assertTrue(success)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['type'], 'SET_INPUT_TYPE')
        self.assertEqual(actions[0]['input_type'], 'json')

    def test_input_json_bad_0_5(self):
        input_data = {
            "recipient": "sha256$ef1253755797c2a3dfd3ab455a7a2080cb9160f2f1fbbf99c475347af1ecc598",
            "issued_on": "2012-12-28",
            "badge": {
                "name": "Completed Rails for Zombies Redux",
                "image": "https://d1ffx7ull4987f.cloudfront.net/images/achievements/large_badge/133/completed-rails-for-zombies-redux-0f73c361c3d5070ca2fa7951e65cbf39.png",
                "description": "Awarded for the completion of Rails for Zombies Redux",
                "version": "0.5.0",
                "criteria": "https://www.codeschool.com/users/mrmickca/badges/133",
                "issuer": {
                    "origin": "http://www.codeschool.com",
                    "org": None,
                    "contact": None,
                    "name": "Code School"
                }
            },
            "salt": "6abf7e9504d73363bdcf9336056f5235",
        }
        input_string = json.dumps(input_data)
        state = INITIAL_STATE
        state['input']['value'] = input_string
        task_meta = add_task(DETECT_INPUT_TYPE)
        result, message, actions = detect_input_type(state, task_meta)
        self.assertTrue(result)
        self.assertEqual(actions[0]['input_type'], 'json')
        self.assertEqual(actions[1]['messageLevel'], MESSAGE_LEVEL_ERROR)

        # 1.0 style hosted JSON input
        input_data['verify'] = {"url": "http://example.org/assertion/1", "type": "hosted"}
        input_data['badge'] = 'http://example.org/badge/1'
        input_string = json.dumps(input_data)
        state['input']['value'] = input_string

        result, message, actions = detect_input_type(state, task_meta)
        self.assertTrue(result)
        self.assertEqual(actions[0]['type'], STORE_INPUT)
        self.assertEqual(actions[0]['input'], input_data['verify']['url'])
        self.assertEqual(actions[1]['input_type'], 'url')
        self.assertEqual(actions[2]['url'], input_data['verify']['url'])  # FETCH_HTTP_NODE
        self.assertEqual(actions[3]['node_id'], input_data['verify']['url'])  # SET_VALIDATION_SUBJECT


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

        encoded_separator = '.'
        if sys.version[:3] < '3':
            encoded_header = b64encode(json.dumps(header))
            encoded_payload = b64encode(json.dumps(payload))
        else:
            encoded_separator = '.'.encode()
            encoded_header = b64encode(json.dumps(header).encode())
            encoded_payload = b64encode(json.dumps(payload).encode())

        self.signed_assertion = encoded_separator.join((encoded_header, encoded_payload, signature))

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

        success, message, actions = detect_input_type(state, {})

        self.assertTrue(success)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['input_type'], 'jws')


class InputImageUrlTests(unittest.TestCase):
    def test_input_type_detection(self):
        state = INITIAL_STATE.copy()
        url = 'http://example.org/assertion/1'
        state['input'] = {'value': url}
        task_meta = add_task(DETECT_INPUT_TYPE)
        result, message, actions = detect_input_type(state, task_meta)

        fetch_action = [a for a in actions if a.get('name') == FETCH_HTTP_NODE][0]
        set_action = [a for a in actions if a.get('type') == SET_VALIDATION_SUBJECT][0]

        self.assertTrue(fetch_action.get('is_potential_baked_input'))
        self.assertEqual(set_action.get('node_id'), url)

        task_meta = add_task(DETECT_INPUT_TYPE, is_potential_baked_input=False)
        result, message, actions = detect_input_type(state, task_meta)
        self.assertTrue(result)
        fetch_action = [a for a in actions if a.get('name') == FETCH_HTTP_NODE][0]
        self.assertFalse(fetch_action.get('is_potential_baked_input'))

    @responses.activate
    def test_fetch_task_handles_potential_baked_input(self):
        set_up_context_mock()
        assertion_url = 'http://example.org/assertion/1'
        image_url = 'http://example.org/image'

        with open(os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png'), 'rb') as f:
            baked_file = bake(f, assertion_url)

        responses.add(responses.GET, image_url, body=baked_file.read(), status=200, content_type='image/png')

        task = add_task(FETCH_HTTP_NODE, url=image_url, is_potential_baked_input=True)
        result, message, actions = run_task({}, task)

        self.assertTrue(result)
        store_resource_action = [a for a in actions if a.get('type') == STORE_ORIGINAL_RESOURCE][0]
        process_baked_input_action = [a for a in actions if a.get('name') == PROCESS_BAKED_RESOURCE][0]

        self.assertEqual(store_resource_action.get('node_id'), image_url)
        self.assertEqual(process_baked_input_action.get('node_id'), image_url)

        task = add_task(FETCH_HTTP_NODE, url=image_url, is_potential_baked_input=False)
        result, message, actions = run_task({}, task)
        self.assertTrue(result)

    def test_process_baked_resource(self):
        image_url = 'http://example.org/image'

        # Store baked Base64 data generated in test_fetch_task_handles_potential_baked_input as a original_resource
        state = {
            'input': {
                'original_json': {
                    image_url: b'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAATCAYAAAB/TkaLAAAALWlUWHRvcGVuYmFkZ2VzAAAAAABodHRwOi8vZXhhbXBsZS5vcmcvYXNzZXJ0aW9uLzFq+wCZAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAACtUlEQVQ4y6XRS08TURjG8eec6UxbekmvtFAU0pIajFANxhKNQV2gRF24dOFnUFE3BiMuJUSXLvwCxhhjNCExCiaQECJSqIgXlBgNhd6k9D5tZ+a4kBrAVpH+V5M5b37vyQzBhlivv+mtKCzyILxQpyO6FgdLx9ZWvQ+f2Mozn3qOfSWK1Ojq7sp+mwiYjG3NSVc64if3hxfKM6T8EOw9+SW3HPF4PE5IggBZUcBrBQhWE0rUmDY+frov6m4KClqNCXo1ZL0hSwtFndpsRI4CKl79oGHw3vnf6Mdzp0ZCn5dOeJ1WJNYyMbkk2cvLOIEPKyXJXG/XXxeLzJ9K5/xMVprL55Tjfljb3VbFbITLZrrG9d8ZIgAw2rlf8TY6WOx7WAIgoHLLABqrnMnOIz4qO6xounmXktc+3zMB5AzAZhhwADtMpdWEXN0drkKBzdGcLPVoCGG1gAAg5UVXaTUJScXtpSXGVLVgG1MkBcVYnFKZSCVRlggApVaTEgrIDLQBmhtxKOAICdYiauvNOU4uQVcnLBIAeNTmVTy8hoCQEADXDswVZ4uzIbQUx8HpaUIBoOvDwm7GMKal9DmAlf/RCBC2W4xj1OWY7zx+6ML6u18xgEy3tw/oeX6XKMu9DHBuw4zYLIbRYjK36g4E+ghQBAC6YSPrnJsbCBfFFYHjhgFE/gFGrWbjKzGRSbgDgStlcBNahrvfve+PFsWIhuOHAUSrgDGbxTgiJjOJ1tnZPgIUtjh/xgAy3tFx20GpPcfYaQD2zaDhZXYtm9ozM3NxK1gVXYfphM83aCXEkmfsLAAbgLjVYnhRTIlJz/SbywQQq/y86jFAPe7zDdUTosszdthsMQRKGSnROjXZV+mGFb9phY2Fo8Hg1SVFypv0Wian8snWqclLfwO3HQPU837/LQbw25n/Cf7NEg3as9WWAAAAAElFTkSuQmCC'
                }
            }
        }
        task_meta = add_task(PROCESS_BAKED_RESOURCE, node_id=image_url)
        result, message, actions = process_baked_resource(state, task_meta)
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['type'], STORE_INPUT, "The baked URL is saved")
        self.assertEqual(actions[0]['input'], 'http://example.org/assertion/1', "The baked URL is saved in store_input")
        self.assertEqual(actions[1]['name'], DETECT_INPUT_TYPE)
        self.assertFalse(actions[1]['is_potential_baked_input'])

        state['input']['original_json'][image_url] = 'data:image/jpeg;base64,/9j/4AA'
        result, message, actions = process_baked_resource(state, task_meta)
        self.assertFalse(result, "Task fails when image is not of known type.")

        state['input']['original_json'][image_url] = 'data:image/jpeg;base64,'
        result, message, actions = process_baked_resource(state, task_meta)
        self.assertFalse(result, "Task fails when there is no content.")
        self.assertIn('Cannot determine image type or content', message)
