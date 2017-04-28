import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.tasks.extensions import extension_analysis
from badgecheck.tasks.task_types import EXTENSION_ANALYSIS, VALIDATE_EXTENSION_NODE


class ExtensionTaskDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.first_node = {
            'id': 'http://example.org/assertion',
            'extensions:exampleExtension': '_:b0',
            'evidence': '_:b1'
        }
        self.extension = {
            'id': '_:b0',
            'type': ['Extension', 'extensions:ExampleExtension'],
            'exampleProperty': 'I\'m a property, short and sweet'
        }
        self.evidence = {
            'id': '_:b1',
            'narrative': 'Rocked the free world'
        }
        self.state = {'graph': [self.first_node, self.extension, self.evidence]}

    def test_queue_extension_validation_check(self):
        task_meta = add_task(EXTENSION_ANALYSIS, node_id=self.first_node['id'])

        result, message, actions = extension_analysis(self.state, task_meta)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['node_id'], self.extension['id'])
        self.assertEqual(actions[0]['name'], VALIDATE_EXTENSION_NODE)

    def test_does_not_queue_duplicate_tasks(self):
        # Queue up existing task that should not be duplicated
        self.state['tasks'] = [add_task(VALIDATE_EXTENSION_NODE, node_id='_:b0')]

        task_meta = add_task(EXTENSION_ANALYSIS, node_id=self.first_node['id'])
        result, message, actions = extension_analysis(self.state, task_meta)
        self.assertTrue(result)
        self.assertEqual(
            len(actions), 0,
            "There should not be any actions returned that would duplicate existing tasks.")

    def test_does_not_get_stuck_in_circular_loop(self):
        # Ensure that if Node A references Node B and vice versa, that we do not get stuck.
        self.extension['obi:myAssertion'] = 'http://example.org/assertion'

        self.test_queue_extension_validation_check()

    def test_validate_extension_node_basic(self):
        # task_meta = add_task(VALIDATE_EXTENSION_NODE, node_id=first_node['id'])
        pass
