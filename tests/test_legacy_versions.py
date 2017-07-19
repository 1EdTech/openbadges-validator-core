import json
import responses
import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V1_URI, OPENBADGES_CONTEXT_V2_URI
from badgecheck.reducers import main_reducer
from badgecheck.tasks.task_types import INTAKE_JSON, JSONLD_COMPACT_DATA, UPGRADE_1_0_NODE, UPGRADE_1_1_NODE
from badgecheck.tasks import task_named
from badgecheck.state import INITIAL_STATE

from testfiles.test_components import test_components


class TestV1_1Detection(unittest.TestCase):
    def setUpContextCache(self):
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
        self.setUpContextCache()
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


    def test_upgrade_1_1_badgeclass(self):
        self.setUpContextCache()
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

