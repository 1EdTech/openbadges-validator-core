import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.tasks.extensions import extension_analysis, validate_extension_node
from badgecheck.tasks.graph import _get_extension_actions
from badgecheck.tasks.task_types import EXTENSION_ANALYSIS, VALIDATE_EXTENSION_NODE


class CompactJsonExtensionDiscoveryTests(unittest.TestCase):
    def test_can_discover_actions_right(self):
        node = {
            'string_prop': 'string_val'
        }
        self.assertEqual(_get_extension_actions(node, ['_:b0']), [])

        node['dict_prop_1'] = {'type': 'Extension'}
        actions = _get_extension_actions(node, ['_:b0'])
        self.assertEqual(len(actions), 1,
                         "When one Extension-type node is present, file one action")
        self.assertEqual(actions[0]['node_path'], ['_:b0', 'dict_prop_1'])

        node['dict_prop_1'] = {'type': ['Extension', 'extensions:ApplyLink']}
        actions = _get_extension_actions(node, ['_:b0'])
        self.assertEqual(len(actions), 1,
                         "It can handle an Extension-type node declared in list")
        self.assertEqual(actions[0]['node_path'], ['_:b0', 'dict_prop_1'])

        node['dict_prop_2'] = {'type': 'NotAnExtension'}
        self.assertEqual(len(_get_extension_actions(node, ['_:b0'])), 1,
                         "Another non-Extension node doesn't add another action.")

        node['dict_prop_2'] = {'type': 'Extension'}
        self.assertEqual(len(_get_extension_actions(node, ['_:b0'])), 2,
                         "A second Extension node yields another action.")

        node = {
            'dict_prop_3': {
                'string_prop_2': 'string_val',
                'dict_prop_4': {'type': 'Extension'}
            }
        }
        actions = _get_extension_actions(node, ['_:b0'])
        self.assertEqual(len(actions), 1, "One Extension is found.")
        self.assertEqual(actions[0]['node_path'], ['_:b0', 'dict_prop_3', 'dict_prop_4'],
                         "A deeply nested extension is properly identified.")

        node = {
            'list_prop_1': [
                {
                    'prop': 'not an extension'
                },
                {
                    'id': '_:b0',
                    'string_prop_1': 'string_val',
                    'dict_prop_1': {'id': '_:b1'}
                },
                'string_val'
            ]
        }

        actions = _get_extension_actions(node, ['_:b0'])
        self.assertEqual(len(actions), 0, "No extensions exist in node yet")
        node['list_prop_1'][1]['type'] = 'Extension'
        actions = _get_extension_actions(node, ['_:b0'])
        self.assertEqual(len(actions), 1, "An Extension is found inside a many=True value.")
        self.assertEqual(
            actions[0]['node_path'], ['_:b0', 'list_prop_1', 1],
            "The action's node_path correctly identifies the list index of the Extension")


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

    def test_does_not_discover_unknown_type_to_test(self):
        # Define a node with an unknown extension type
        pass


class ExtensionNodeValidationTests(unittest.TestCase):
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

    def test_validate_extension_node_basic(self):
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_id=self.extension['id'])

        result, message, actions = validate_extension_node(self.state, task_meta)
        self.assertTrue(result, "A valid expression of the extension should pass")
        self.assertIn('validated on node', message)
        self.assertEqual(len(actions), 0)

    def test_validate_extension_node_declared_type(self):
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_id=self.extension['id'],
            type_to_test='extensions:ExampleExtension')

        result, message, actions = validate_extension_node(self.state, task_meta)
        self.assertTrue(result, "A valid expression of the extension should pass")
        self.assertIn('validated on node', message)
        self.assertEqual(len(actions), 0)

    def test_validate_extension_node_invalid(self):
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_id=self.extension['id'])
        self.extension['exampleProperty'] = 1337  # String value required

        result, message, actions = validate_extension_node(self.state, task_meta)
        self.assertFalse(result, "An invalid expression of a rule in schema should fail")
        self.assertIn('did not validate', message)
        self.assertEqual(len(actions), 0)

    def test_validation_breaks_down_multiple_extensions(self):
        self.extension['type'].append('extensions:ApplyLink')  # TODO: switch to a different extension after installing another
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_id=self.extension['id'])

        result, message, actions = validate_extension_node(self.state, task_meta)
        self.assertTrue(result, "Task breakdown should succeed.")
        self.assertIn('Multiple extension types', message)
        self.assertEqual(len(actions), 2)
        self.assertTrue(all(a['name'] == VALIDATE_EXTENSION_NODE for a in actions),
                        'All tasks created should be of correct type')

