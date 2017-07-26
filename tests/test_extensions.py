import json
import responses
import unittest

from badgecheck.actions.graph import add_node
from badgecheck.actions.tasks import add_task
from badgecheck.extensions import GeoLocation
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_URI
from badgecheck.reducers.graph import graph_reducer
from badgecheck.tasks.extensions import validate_extension_node
from badgecheck.tasks.graph import _get_extension_actions
from badgecheck.tasks import task_named
from badgecheck.tasks.task_types import JSONLD_COMPACT_DATA, VALIDATE_EXTENSION_NODE
from badgecheck.utils import jsonld_no_cache

from tests.utils import set_up_context_mock


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
            'http://schema.org/text': 'I\'m a property, short and sweet'
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

    def test_validate_extension_node_path_based(self):
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_path=[self.extension['id']])

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
        self.extension['http://schema.org/text'] = 1337  # String value required

        result, message, actions = validate_extension_node(self.state, task_meta)
        self.assertFalse(result, "An invalid expression of a rule in schema should fail")
        self.assertIn('did not validate', message)
        self.assertEqual(len(actions), 0)

    def test_validation_breaks_down_multiple_extensions(self):
        self.extension['type'].append('extensions:ApplyLink')
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_id=self.extension['id'])

        result, message, actions = validate_extension_node(self.state, task_meta)
        self.assertTrue(result, "Task breakdown should succeed.")
        self.assertIn('Multiple extension types', message)
        self.assertEqual(len(actions), 2)
        self.assertTrue(all(a['name'] == VALIDATE_EXTENSION_NODE for a in actions),
                        'All tasks created should be of correct type')


class ComplexExtensionNodeValdiationTests(unittest.TestCase):
    """
    Tests for extensions that use nested properties.
    """
    def test_node_json_validation(self):
        node = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.com/1',
            'type': 'Assertion',
            'schema:location': {
                '@context': 'https://w3id.org/openbadges/extensions/geoCoordinatesExtension/context.json',
                'type': ['Extension', 'extensions:GeoCoordinates'],
                'description': 'That place in the woods where we built the fort',
                'schema:geo': {
                    'schema:latitude': 44.580900,
                    'schema:longitude': -123.301815
                }
            }
        }
        state = {'graph': graph_reducer([], add_node(node['id'], node))}

        task_meta = add_task(
            VALIDATE_EXTENSION_NODE,
            node_path=['http://example.com/1', 'schema:location'],
            node_json=json.dumps(node['schema:location']))

        result, message, actions = validate_extension_node(state, task_meta)
        self.assertTrue(result, "A valid expression of the extension should pass")
        self.assertIn('validated on node', message)
        self.assertEqual(len(actions), 0)

        del node['schema:location']['schema:geo']['schema:latitude']
        task_meta['node_json'] = json.dumps(node['schema:location'])
        result, message, actions = validate_extension_node(state, task_meta)
        self.assertFalse(result, "A required property not present should be detected by JSON-schema.")

    @responses.activate
    def test_extension_discovered_jsonld_compact(self):
        """
        Ensure an extension node is properly discovered and that the task runs without error.
        """
        node = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.com/1',
            'type': 'Assertion',
            'schema:location': {
                '@context': 'https://w3id.org/openbadges/extensions/geoCoordinatesExtension/context.json',
                'type': ['Extension', 'extensions:GeoCoordinates'],
                'description': 'That place in the woods where we built the fort',
                'geo': {
                    'latitude': 44.580900,
                    'longitude': -123.301815
                }
            }
        }
        state = {'graph': graph_reducer([], add_node(node['id'], node))}

        set_up_context_mock()

        responses.add(
            responses.GET,
            "https://w3id.org/openbadges/extensions/geoCoordinatesExtension/context.json",
            body=json.dumps(GeoLocation.context_json),
            status=200,
            content_type='application/ld+json')

        compact_task = add_task(JSONLD_COMPACT_DATA, data=json.dumps(node), jsonld_options=jsonld_no_cache)

        result, message, actions = task_named(JSONLD_COMPACT_DATA)(state, compact_task)
        self.assertTrue(result, "JSON-LD Compact is successful.")
        self.assertIn(VALIDATE_EXTENSION_NODE, [i.get('name') for i in actions], "Validation task queued.")

        validate_task = [i for i in actions if i.get('name') == VALIDATE_EXTENSION_NODE][0]
        self.assertIsNotNone(validate_task['node_json'])

        result, message, actions = task_named(VALIDATE_EXTENSION_NODE)(state, validate_task)
        self.assertTrue(result, "Validation task is successful.")


class UnknownExtensionsTests(unittest.TestCase):
    """
    TODO: In the future, dynamic discovery of extensions will be possible.
    Until then, make sure we are reporting on unverified extensions.
    """
    def test_report_message_on_unknown_extension(self):
        first_node = {
            'id': 'http://example.org/assertion',
            'extensions:exampleExtension': '_:b0',
            'evidence': '_:b1'
        }
        extension = {
            'id': '_:b0',
            'type': ['Extension', 'extensions:UnknownExtension'],
            'schema:unknownProperty': 'I\'m a property, short and sweet'
        }
        state = {'graph': [first_node, extension]}
        task_meta = add_task(
            VALIDATE_EXTENSION_NODE, node_id=extension['id'])

        result, message, actions = validate_extension_node(state, task_meta)
        self.assertFalse(result, "An unknown extension will fail for now.")
