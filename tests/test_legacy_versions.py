import json
import os
import responses
import unittest

from openbadges.verifier.actions.action_types import SET_OPENBADGES_VERSION, SET_VALIDATION_SUBJECT, REPORT_MESSAGE
from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.actions.input import store_input
from openbadges.verifier.openbadges_context import OPENBADGES_CONTEXT_V1_URI, OPENBADGES_CONTEXT_V2_URI
from openbadges.verifier.reducers import main_reducer
from openbadges.verifier.tasks.task_types import (DETECT_INPUT_TYPE, FETCH_HTTP_NODE, INTAKE_JSON, JSONLD_COMPACT_DATA,
                                                  UPGRADE_0_5_NODE, UPGRADE_1_0_NODE, UPGRADE_1_1_NODE)
from openbadges.verifier.tasks import run_task, task_named
from openbadges.verifier.state import INITIAL_STATE
from openbadges.verifier.tasks.validation import OBClasses
from openbadges.verifier.verifier import generate_report, verification_store, verify

from .testfiles.test_components import test_components


def setUpContextCache():
    v2_data = test_components['openbadges_context']
    responses.add(
        responses.GET, OPENBADGES_CONTEXT_V2_URI,
        body=v2_data, status=200, content_type='application/ld+json'
    )
    v1_data = test_components['openbadges_context_v1']
    responses.add(
        responses.GET, OPENBADGES_CONTEXT_V1_URI,
        body=v1_data, status=200, content_type='application/ld+json'
    )


class V1_1DetectionAndUpgradesTests(unittest.TestCase):
    def test_can_detect_v1_based_on_context(self):
        json_data = test_components['1_1_basic_assertion']
        state = INITIAL_STATE

        task = add_task(INTAKE_JSON, data=json_data)
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(actions[2]['name'], UPGRADE_1_1_NODE)

        json_data = test_components['1_1_basic_badgeclass']
        task['data'] = json_data
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(actions[2]['name'], UPGRADE_1_1_NODE)

        json_data = test_components['1_1_basic_issuer']
        task['data'] = json_data
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(actions[2]['name'], UPGRADE_1_1_NODE)

        json_data = test_components['1_0_basic_issuer']
        task['data'] = json_data
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(actions[1]['name'], UPGRADE_1_0_NODE)

    @responses.activate
    def test_upgrade_1_1_assertion(self):
        setUpContextCache()
        json_data = test_components['1_1_basic_assertion']
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, node_id='https://example.org/beths-robotics-badge.json', data=json_data)

        result, message, actions = task_named(INTAKE_JSON)(state, task)
        for action in actions:
            state = main_reducer(state, action)
        for task in state.get('tasks'):
            result, message, actions = task_named(task['name'])(state, task)
            for action in actions:
                state = main_reducer(state, action)

        result, message, actions = task_named(UPGRADE_1_1_NODE)(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 0)

        # Test timestamp upgrading
        state['graph'][0]['issuedOn'] = 1500423730
        result, message, actions = task_named(UPGRADE_1_1_NODE)(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['data']['issuedOn'], '2017-07-19T00:22:10+00:00')
        self.assertEqual(len(actions[0]['data'].keys()), 1, "There is a patch made of one prop")

        state['graph'][0]['issuedOn'] = '1500423730.5'
        result, message, actions = task_named(UPGRADE_1_1_NODE)(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1)
        state = main_reducer(state, actions[0])

        state['graph'][0]['issuedOn'] = '2016-05-15'
        result, message, actions = task_named(UPGRADE_1_1_NODE)(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1)
        state = main_reducer(state, actions[0])

    @responses.activate
    def test_upgrade_1_1_badgeclass(self):
        setUpContextCache()
        json_data = test_components['1_1_basic_badgeclass']
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, node_id='https://example.org/robotics-badge.json', data=json_data)

        result, message, actions = task_named(INTAKE_JSON)(state, task)
        for action in actions:
            state = main_reducer(state, action)
        for task in state.get('tasks'):
            result, message, actions = task_named(task['name'])(state, task)
            for action in actions:
                state = main_reducer(state, action)

        # Test criteria class upgrade
        state['graph'][0]['alignment'] = {
            'url': 'http://somewhere.overtherainbow.net/wayuphigh',
            'name': "Knowledge of children's songs"
        }
        result, message, actions = task_named(UPGRADE_1_1_NODE)(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1)

    def test_upgrade_1_1_issuer(self):
        setUpContextCache()
        data = json.loads(test_components['1_1_basic_issuer'])
        data['type'] = 'IssuerOrg'  # Test alias that was accepted in v1.1 context
        json_data = json.dumps(data)
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, node_id='https://example.org/organization.json', data=json_data)

        result, message, actions = task_named(INTAKE_JSON)(state, task)
        for action in actions:
            state = main_reducer(state, action)
        for task in state.get('tasks'):
            result, message, actions = task_named(task['name'])(state, task)
            for action in actions:
                state = main_reducer(state, action)

        self.assertTrue(result)
        self.assertEqual(state['graph'][0]['type'], OBClasses.Issuer)

    @responses.activate
    def test_upgrade_1_1_issuer_in_full_verify_with_redirect(self):
        setUpContextCache()
        old_url = "http://example.org/oldissuerurl"
        data = {
            "@context": "https://w3id.org/openbadges/v1",
            "type": "Issuer",
            "id": "http://example.org/realissuerurl",
            "description": "Example Badge Issuer",
            "url": "http://example.org",
            "email": "noreply@example.org",
            "name": "Test Issuer",
            "image": "http://example.org/image"
        }

        responses.add(responses.GET, old_url, json=data)
        responses.add(responses.GET, data['id'], json=data)

        result = verify(old_url)
        self.assertTrue(result['report']['valid'])


class V1_0DetectionAndUpgradesTests(unittest.TestCase):
    def test_json_1_0_assertion_input(self):
        assertion_data = test_components['1_0_basic_assertion']
        state = INITIAL_STATE
        action = store_input(assertion_data)
        state = main_reducer(state, action)
        self.assertEqual(state['input']['value'], assertion_data)

        task_meta = add_task(DETECT_INPUT_TYPE)
        result, message, actions = run_task(state, task_meta)
        self.assertTrue(result)
        self.assertIn(SET_VALIDATION_SUBJECT, [a.get('type') for a in actions])
        self.assertIn(FETCH_HTTP_NODE, [a.get('name') for a in actions])

    def test_upgrade_1_0_assertion(self):
        json_data = test_components['1_0_basic_assertion']
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, node_id='http://a.com/instance', data=json_data)

        result, message, actions = task_named(INTAKE_JSON)(state, task)
        for action in actions:
            state = main_reducer(state, action)

        task = state.get('tasks')[0]
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        for action in actions:
            state = main_reducer(state, action)

        self.assertEqual(len(state.get('tasks')), 3)
        modified_data = json.loads(state.get('tasks')[1]['data'])
        self.assertEqual(modified_data['@context'], OPENBADGES_CONTEXT_V1_URI)
        self.assertEqual(modified_data['id'], modified_data['verify']['url'])
        self.assertEqual(modified_data['type'], OBClasses.Assertion)

    def test_upgrade_1_0_badgeclass(self):
        json_data = test_components['1_0_basic_badgeclass']
        node_id = 'http://a.com/badgeclass'
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, node_id=node_id, data=json_data)

        result, message, actions = task_named(INTAKE_JSON)(state, task)
        for action in actions:
            state = main_reducer(state, action)

        task = state.get('tasks')[0]
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        for action in actions:
            state = main_reducer(state, action)

        self.assertEqual(len(state.get('tasks')), 3)
        modified_data = json.loads(state.get('tasks')[1]['data'])
        self.assertEqual(modified_data['@context'], OPENBADGES_CONTEXT_V1_URI)
        self.assertEqual(modified_data['id'], node_id)
        self.assertEqual(modified_data['type'], OBClasses.BadgeClass)

    def test_upgrade_1_0_issuer(self):
        json_data = test_components['1_0_basic_issuer']
        node_id = 'http://a.com/issuer'
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, node_id=node_id, data=json_data)

        result, message, actions = task_named(INTAKE_JSON)(state, task)
        for action in actions:
            state = main_reducer(state, action)

        task = state.get('tasks')[0]
        result, message, actions = task_named(task['name'])(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        for action in actions:
            state = main_reducer(state, action)

        self.assertEqual(len(state.get('tasks')), 3)
        modified_data = json.loads(state.get('tasks')[1]['data'])
        self.assertEqual(modified_data['@context'], OPENBADGES_CONTEXT_V1_URI)
        self.assertEqual(modified_data['id'], node_id)
        self.assertEqual(modified_data['type'], OBClasses.Issuer)

    @responses.activate
    def full_validate_1_0_to_2_0_conversion(self):
        setUpContextCache()
        assertion_data = json.loads(test_components['1_0_basic_assertion_with_extra_properties'])
        badgeclass_data = json.loads(test_components['1_0_basic_badgeclass'])
        issuer_data = json.loads(test_components['1_0_basic_issuer'])

        responses.add(
            responses.GET, assertion_data['verify']['url'],
            json=assertion_data
        )
        responses.add(
            responses.GET, assertion_data['badge'],
            json=badgeclass_data
        )
        responses.add(
            responses.GET, badgeclass_data['issuer'],
            json=issuer_data
        )
        png_badge = os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png')
        with open(png_badge, 'rb') as image:
            responses.add(
                responses.GET, badgeclass_data['image'], body=image.read(), status=200, content_type='image/png'
            )

        store = verification_store(assertion_data['verify']['url'])
        state = store.get_state()
        report = generate_report(store)

        self.assertTrue(report['report']['valid'])
        assertion_node = state['graph'][0]
        badgeclass_node = state['graph'][1]
        issuer_node = state['graph'][2]

        self.assertEqual(assertion_node['id'], assertion_data['verify']['url'])
        self.assertEqual(badgeclass_node['@context'], OPENBADGES_CONTEXT_V2_URI)
        self.assertEqual(issuer_node['type'], OBClasses.Issuer)

        self.assertEqual(report['report']['openBadgesVersion'], '1.0')


class V1_0DetectionAndUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.assertion_data = {
            "recipient": "sha256$a4a934a0bfc882a34a3e71650e40789453b2db9799a51a2d084a64caadd72397",
            "salt": "2e2bad0df9e11272ffbcee86e4c7edd4",
            "issued_on": "2017-01-01",
            "badge": {
                "name": "Test Badge for admin@bluemantis.com",
                "image": "http://example.org/image",
                "description": "Awarded using the php example codebase",
                "criteria": "http://example.org/criteria",
                "issuer": {
                    "origin": "example.org",
                    "name": "Test Issuer",
                    "org": None,
                    "contact": None
                }
            }
        }

    def test_can_detect_and_upgrade_v_0_5(self):
        assertion_data = self.assertion_data
        state = INITIAL_STATE
        task = add_task(INTAKE_JSON, data=json.dumps(assertion_data), node_id='http://example.org/assertion')

        result, message, actions = run_task(state, task)
        self.assertTrue(result)
        version_action = [a for a in actions if a.get('type') == SET_OPENBADGES_VERSION][0]
        self.assertEqual(version_action['version'], '0.5')
        upgrade_action = [a for a in actions if a.get('name') == UPGRADE_0_5_NODE][0]

        result, message, actions = run_task(state, upgrade_action)
        self.assertTrue(result)

        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['name'], JSONLD_COMPACT_DATA)

    def test_json_0_5_assertion_input(self):
        assertion_data = json.dumps(self.assertion_data)
        state = INITIAL_STATE
        action = store_input(assertion_data)
        state = main_reducer(state, action)
        self.assertEqual(state['input']['value'], assertion_data)

        task_meta = add_task(DETECT_INPUT_TYPE)
        result, message, actions = run_task(state, task_meta)
        self.assertTrue(result, "Task completes successfully")
        self.assertIn(REPORT_MESSAGE, [a.get('type') for a in actions])

    @responses.activate
    def full_validate_0_5_to_2_0_conversion(self):
        setUpContextCache()
        assertion_url = 'http://example.org/assertion'
        assertion_data = {
            "recipient": "sha256$a4a934a0bfc882a34a3e71650e40789453b2db9799a51a2d084a64caadd72397",
            "salt": "2e2bad0df9e11272ffbcee86e4c7edd4",
            "issued_on": "2017-01-01",
            "badge": {
                "name": "Test Badge for admin@bluemantis.com",
                "image": "http://example.org/image",
                "description": "Awarded using the php example codebase",
                "criteria": "http://example.org/criteria",
                "issuer": {
                    "origin": "http://example.org",
                    "name": "Test Issuer",
                    "org": None,
                    "contact": 'test@example.com'
                }
            }
        }

        responses.add(
            responses.GET, assertion_url,
            json=assertion_data
        )
        png_badge = os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png')
        with open(png_badge, 'rb') as image:
            responses.add(
                responses.GET, assertion_data['badge']['image'],
                body=image.read(), status=200, content_type='image/png'
            )

        store = verification_store(assertion_url)
        state = store.get_state()
        report = generate_report(store)

        self.assertTrue(report['report']['valid'])
        assertion_node = state['graph'][0]
        badgeclass_node = state['graph'][2]
        issuer_node = state['graph'][1]

        self.assertEqual(assertion_node['id'], assertion_url)
        self.assertEqual(badgeclass_node['@context'], OPENBADGES_CONTEXT_V2_URI)
        self.assertEqual(issuer_node['type'], OBClasses.Profile)

        self.assertEqual(report['report']['openBadgesVersion'], '0.5')
