import datetime
import json
import responses
import unittest
import sys

from openbadges.verifier.actions.graph import add_node
from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.extensions import GeoLocation, ExampleExtension, ApplyLink
from openbadges.verifier.openbadges_context import OPENBADGES_CONTEXT_V2_URI
from openbadges.verifier.reducers import main_reducer
from openbadges.verifier.reducers.graph import graph_reducer
from openbadges.verifier.state import INITIAL_STATE
from openbadges.verifier.tasks.extensions import validate_extension_node
from openbadges.verifier.tasks.graph import _get_extension_actions
from openbadges.verifier.tasks import task_named
from openbadges.verifier.tasks.task_types import (INTAKE_JSON, JSONLD_COMPACT_DATA, VALIDATE_EXTENSION_NODE,
                                         VALIDATE_EXTENSION_SINGLE)
from openbadges.verifier.utils import jsonld_no_cache, CachableDocumentLoader

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
        self.extension = {
            'id': '_:b0',
            'type': ['Extension', 'extensions:ExampleExtension'],
            'http://schema.org/text': 'I\'m a property, short and sweet'
        }
        self.evidence = {
            'id': '_:b1',
            'narrative': 'Rocked the free world'
        }
        self.first_node = {
            '@context': [OPENBADGES_CONTEXT_V2_URI, ExampleExtension.context_url],
            'id': 'http://example.org/assertion',
            'extensions:exampleExtension': self.extension,
            'evidence': self.evidence
        }

    def load_mocks(self):
        loader = CachableDocumentLoader(use_cache=True)
        loader.session.cache.remove_old_entries(datetime.datetime.utcnow())
        loader.contexts = set()
        self.options = {'jsonld_options': {'documentLoader': loader}}

        set_up_context_mock()
        loader(OPENBADGES_CONTEXT_V2_URI)
        schema_url = list(ExampleExtension.validation_schema)[0]
        responses.add(responses.GET, ExampleExtension.context_url, status=200, json=ExampleExtension.context_json)
        loader(ExampleExtension.context_url)
        responses.add(responses.GET, schema_url, status=200, json=ExampleExtension.validation_schema[schema_url])
        loader.session.get(schema_url)

        self.state = INITIAL_STATE
        task = add_task(
            INTAKE_JSON, data=json.dumps(self.first_node), node_id=self.first_node['id'])
        result, message, actions = task_named(INTAKE_JSON)(self.state, task,  **self.options)
        self.state = main_reducer(self.state, actions[0])
        result, message, actions = task_named(actions[1]['name'])(
            self.state, actions[1],  **self.options)  # JSONLD_COMPACT_DATE
        self.state = main_reducer(self.state, actions[0])  # ADD_NODE
        self.validation_task = actions[1]  # VALIDATE_EXTENSION_NODE


    @responses.activate
    def test_validate_extension_node_basic(self):
        self.load_mocks()
        task_meta = self.validation_task

        result, message, actions = validate_extension_node(self.state, task_meta, **self.options)
        self.assertTrue(result, "A valid expression of the extension should pass")
        self.assertIn('validated on node', message)
        self.assertEqual(len(actions), 0)

    @responses.activate
    def test_validate_extension_node_invalid(self):
        self.load_mocks()
        task_meta = self.validation_task

        # String value is required, we'll try a number
        self.state['graph'][0]['extensions:exampleExtension']['schema:text'] = 1337

        result, message, actions = validate_extension_node(self.state, task_meta, **self.options)
        self.assertFalse(result, "An invalid expression of a rule in schema should fail")
        self.assertIn('did not validate', message)
        self.assertEqual(len(actions), 0)

    @responses.activate
    def test_validation_breaks_down_multiple_extensions(self):
        self.load_mocks()
        # Load up ApplyLink schema and context
        responses.add(responses.GET, ApplyLink.context_url, status=200, json=ApplyLink.context_json)
        self.options['jsonld_options']['documentLoader'](ApplyLink.context_url)
        schema_url = list(ApplyLink.validation_schema)[0]
        responses.add(responses.GET, schema_url, status=200, json=ApplyLink.validation_schema[schema_url])
        self.options['jsonld_options']['documentLoader'].session.get(schema_url)

        self.state['graph'][0]['extensions:exampleExtension']['type'].append('extensions:ApplyLink')
        task_meta = self.validation_task.copy()
        task_meta['context_urls'].append(ApplyLink.context_url)
        task_meta['types_to_test'].append('extensions:ApplyLink')

        result, message, actions = validate_extension_node(self.state, task_meta, **self.options)
        self.assertTrue(result, "Task breakdown should succeed.")
        self.assertIn('Multiple extension types', message)
        self.assertEqual(len(actions), 2)
        self.assertTrue(all(a['name'] == VALIDATE_EXTENSION_SINGLE for a in actions),
                        'All tasks created should be of correct type')

        for action in actions:
            aresult, amessage, aactions = validate_extension_node(self.state, task_meta, **self.options)
            self.assertTrue(aresult)


class ComplexExtensionNodeValdiationTests(unittest.TestCase):
    """
    Tests for extensions that use nested properties.
    """
    @responses.activate
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

        loader = CachableDocumentLoader(use_cache=True)
        loader.session.cache.remove_old_entries(datetime.datetime.utcnow())
        loader.contexts = set()
        options = {'jsonld_options': {'documentLoader': loader}}

        set_up_context_mock()
        loader(OPENBADGES_CONTEXT_V2_URI)
        schema_url = list(GeoLocation.validation_schema)[0]
        responses.add(responses.GET, GeoLocation.context_url, status=200, json=GeoLocation.context_json)
        loader(GeoLocation.context_url)
        responses.add(responses.GET, schema_url, status=200, json=GeoLocation.validation_schema[schema_url])
        loader.session.get(schema_url)

        state = INITIAL_STATE
        task = add_task(
            INTAKE_JSON, data=json.dumps(node), node_id=node['id'])
        result, message, actions = task_named(INTAKE_JSON)(state, task, **options)
        state = main_reducer(state, actions[0])
        result, message, actions = task_named(actions[1]['name'])(
            state, actions[1], **options)  # JSONLD_COMPACT_DATE
        state = main_reducer(state, actions[0])  # ADD_NODE
        task_meta = actions[1]  # VALIDATE_EXTENSION_NODE

        result, message, actions = validate_extension_node(state, task_meta)
        self.assertTrue(result, "A valid expression of the extension should pass")
        self.assertIn('validated on node', message)
        self.assertEqual(len(actions), 0)

        del state['graph'][0]['schema:location']['schema:geo']['schema:latitude']
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
                '@context': GeoLocation.context_url,
                'type': ['Extension', 'extensions:GeoCoordinates'],
                'description': 'That place in the woods where we built the fort',
                'schema:geo': {
                    'schema:latitude': 44.580900,
                    'schema:longitude': -123.301815
                }
            }
        }
        state = INITIAL_STATE

        set_up_context_mock()

        responses.add(
            responses.GET,
            GeoLocation.context_url,
            body=json.dumps(GeoLocation.context_json),
            status=200,
            content_type='application/ld+json')

        schema_url = 'https://w3id.org/openbadges/extensions/geoCoordinatesExtension/schema.json'
        responses.add(
            responses.GET, schema_url,
            body=json.dumps(GeoLocation.validation_schema[schema_url]),
            status=200,
            content_type='application/ld+json')

        compact_task = add_task(
            JSONLD_COMPACT_DATA, data=json.dumps(node), jsonld_options=jsonld_no_cache,
            context_urls=[GeoLocation.context_url]
        )
        result, message, actions = task_named(JSONLD_COMPACT_DATA)(state, compact_task)
        self.assertTrue(result, "JSON-LD Compact is successful.")
        self.assertIn(VALIDATE_EXTENSION_NODE, [i.get('name') for i in actions], "Validation task queued.")
        state = main_reducer(state, actions[0])  # ADD_NODE

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


class DynamicExtensionValidationTests(unittest.TestCase):
    """
    Extension validation involves establishin
    """
    @responses.activate
    def test_queue_validation_on_unknown_extension(self):
        set_up_context_mock()

        extension_schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "title": "1.1 Open Badge Example Extension for testing: Unknown Extension",
            "description": "An extension that allows you to add a single string unknownProperty to an extension object for unknown reasons.",
            "type": "object",
            "properties": {
                "unknownProperty": {
                    "type": "string"
                }
            },
            "required": ["unknownProperty"]
        }
        extension_schema_url = 'http://example.org/unkownSchema'
        extension_context = {
            '@context': {
                "obi": "https://w3id.org/openbadges#",
                "extensions": "https://w3id.org/openbadges/extensions#",
                'unknownProperty': 'http://schema.org/unknownProperty'
            },
            "obi:validation": [
                {
                    "obi:validatesType": "extensions:UnknownExtension",
                    "obi:validationSchema": extension_schema_url
                }
            ]
        }
        extension_context_url = 'http://example.org/unknownExtensionContext'

        first_node_json = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.org/assertion',
            'extensions:exampleExtension': {
                '@context': extension_context_url,
                'type': ['Extension', 'extensions:UnknownExtension'],
                'unknownProperty': 'I\'m a property, short and sweet'
            },
            'evidence': 'http://example.org/evidence'
        }

        responses.add(
            responses.GET, extension_context_url,
            json=extension_context
        )
        responses.add(
            responses.GET, extension_schema_url,
            json=extension_schema
        )
        state = INITIAL_STATE

        task_meta = add_task(
            INTAKE_JSON, data=json.dumps(first_node_json), node_id=first_node_json['id'])

        result, message, actions = task_named(INTAKE_JSON)(state, task_meta)
        for action in actions:
            state = main_reducer(state, action)

        # Compact JSON
        result, message, actions = task_named(state['tasks'][0]['name'])(state, state['tasks'][0])

        self.assertEqual(len(actions), 3)

        state = main_reducer(state, actions[0])

        validation_action = actions[1]
        result, message, actions = validate_extension_node(state, validation_action)

        self.assertTrue(result)
