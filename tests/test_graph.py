import json
import responses
import unittest

from openbadges.verifier.actions.action_types import ADD_NODE, STORE_ORIGINAL_RESOURCE
from openbadges.verifier.actions.graph import add_node, patch_node, patch_node_reference
from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.reducers.graph import graph_reducer
from openbadges.verifier.state import get_node_by_id
from openbadges.verifier.tasks.graph import fetch_http_node, jsonld_compact_data
from openbadges.verifier.tasks import run_task
from openbadges.verifier.tasks.task_types import (DETECT_AND_VALIDATE_NODE_CLASS, FETCH_HTTP_NODE, INTAKE_JSON,
                                         JSONLD_COMPACT_DATA)
from openbadges.verifier.openbadges_context import OPENBADGES_CONTEXT_V2_URI
from openbadges.verifier.utils import MESSAGE_LEVEL_WARNING
from openbadges.verifier.verifier import verify

from .utils import set_up_context_mock, set_up_image_mock


try:
    from .testfiles.test_components import test_components
except (ImportError, SystemError):
    from .testfiles.test_components import test_components


class HttpFetchingTests(unittest.TestCase):

    @responses.activate
    def test_basic_http_fetch_task(self):
        url = 'http://example.com/assertionmaybe'
        responses.add(
            responses.GET, url,
            body=test_components['2_0_basic_assertion'],
            status=200, content_type='application/ld+json'
        )
        task = add_task(FETCH_HTTP_NODE, url=url)

        success, message, actions = fetch_http_node({}, task)

        self.assertTrue(success)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['type'], STORE_ORIGINAL_RESOURCE)
        self.assertEqual(actions[1]['name'], INTAKE_JSON)


class NodeStorageTests(unittest.TestCase):
    def test_single_node_store(self):
        new_node = {
            "key1": 1
        }
        state = graph_reducer([], add_node('http://example.com/node1', new_node))
        self.assertEqual(len(state), 1)
        self.assertEqual(state[0]['id'], 'http://example.com/node1')
        self.assertEqual(state[0]['key1'], 1)

    def new_node_successfully_appends_to_state(self):
        new_node = {
            "key1": 1
        }
        state = graph_reducer([{"id": "_:b9000"}], add_node('http://example.com/node1', new_node))
        self.assertEqual(len(state), 2)

    def test_store_nested(self):
        new_node = {
            "key1": 1,
            "nested1": {"key2": 2}
        }
        state = graph_reducer([], add_node('http://example.com/node1', new_node))
        self.assertEqual(len(state), 1)
        first_node = [node for node in state if node['id'] == 'http://example.com/node1'][0]
        self.assertEqual(first_node['key1'], 1)
        nested_node = first_node['nested1']
        self.assertEqual(nested_node['key2'], 2)
        self.assertIsNone(nested_node.get('id'))

    def test_store_node_inaccurate_id_value(self):
        """
        Due to redirects, we may not have the canonical id for a node.
        If there's a conflict due to the id and the node[id] in add_node(id, node), 
        what should we do?
        """
        pass

    def test_store_with_included_blank_node_ids_in_input(self):
        """
        Make sure the graph reducer can handle assigning node ids when we include
        some collisions in the input that use the blank node identifier scheme _:
        """
        pass

    def test_store_lists(self):
        new_node = {
            "key1": 1,
            "b_list": [
                "b",
                {"c": 3}
            ]
        }

        state = graph_reducer([], add_node('http://example.com/node1', new_node))
        self.assertEqual(len(state), 1)
        root_node = get_node_by_id({'graph': state}, 'http://example.com/node1')
        self.assertEqual(root_node['id'], 'http://example.com/node1')
        self.assertEqual(root_node['key1'], 1)

        nested_node = root_node['b_list'][1]
        self.assertEqual(nested_node['c'], 3)


class NodeUpdateTests(unittest.TestCase):
    def test_patch_node(self):
        first_node = {'id': '_:b0', 'name': 'One'}
        second_node = {'id': '_:b1', 'name': 'Two'}

        action = patch_node(first_node['id'], {'name': 'New One'})
        state = graph_reducer([first_node, second_node], action)

        self.assertEqual(len(state), 2)
        updated_node = get_node_by_id({'graph': state}, first_node['id'])
        self.assertEqual(updated_node['name'], 'New One')

    def test_update_node_id(self):
        """
        TODO: allow ability to update a node id, replacing all references to that
        id in other nodes with the new id
        """
        pass

    def test_update_node_reference(self):
        first_node = {'id': '_:b0', 'badge': 'http://example.org/old'}
        graph_state = [first_node]
        new_id = 'http://example.org/new'
        action = patch_node_reference([first_node['id'], 'badge'], new_id)

        graph_state = graph_reducer(graph_state, action)
        self.assertEqual(graph_state[0]['badge'], new_id)



class JsonLdCompactTests(unittest.TestCase):
    def setUpContextCache(self):
        data = test_components['openbadges_context']
        responses.add(
            responses.GET, OPENBADGES_CONTEXT_V2_URI,
            body=data, status=200, content_type='application/ld+json'
        )

    @responses.activate
    def test_compact_node(self):
        self.setUpContextCache()

        data = """{
            "@context": {"thing_we_call_you_by": "http://schema.org/name"},
            "thing_we_call_you_by": "Test Data"
        }"""

        task = add_task(JSONLD_COMPACT_DATA, data=data, node_id='http://example.com/1')

        result, message, actions = jsonld_compact_data({}, task)
        self.assertTrue(result, "JSON-LD Compaction should be successful.")
        self.assertEqual(message, "Successfully compacted node http://example.com/1")
        self.assertEqual(
            len(actions), 2,
            "Should queue up add_node and add_task for type detection")
        self.assertEqual(
            actions[0]['data']['name'], "Test Data",
            "Node should be compacted into OB Context and use OB property names.")

    @responses.activate
    def test_no_task_data(self):
        task = add_task(JSONLD_COMPACT_DATA)

        result, message, actions = jsonld_compact_data({}, task)
        self.assertFalse(result)
        self.assertEqual(message, 'Could not load data')


    @responses.activate
    def test_reduce_compacted_output(self):
        self.setUpContextCache()

        data = {
            "@context": {"thing_we_call_you_by": "http://schema.org/name"},
            "thing_we_call_you_by": "Test Data"
        }

        task = add_task(JSONLD_COMPACT_DATA, data=json.dumps(data), node_id='_:b100')

        result, message, actions = jsonld_compact_data({}, task)

        state = graph_reducer([], actions[0])
        self.assertEqual(len(state), 1, "Node should be added to graph")
        self.assertEqual(state[0]['name'], data['thing_we_call_you_by'])
        self.assertEqual(state[0].get('id'), '_:b100', "Node should have a blank id assigned")


class ObjectRedirectionTests(unittest.TestCase):
    @responses.activate
    def test_node_has_id_different_from_fetch_url(self):
        set_up_context_mock()

        first_url = 'http://example.org/url1'
        second_url = 'http://example.org/url2'
        node_data = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': first_url,
            'name': 'Some Badge'
        }

        responses.add(responses.GET, first_url, json=node_data)
        responses.add(responses.GET, second_url, json=node_data)

        task = add_task(FETCH_HTTP_NODE, url=second_url)
        state = {'graph': []}

        result, message, actions = run_task(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[1]['name'], INTAKE_JSON)

        result, message, actions = run_task(state, actions[1])  # INTAKE_JSON
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[1]['name'], JSONLD_COMPACT_DATA)

        result, message, actions = run_task(state, actions[1])  # JSONLD_COMPACT_DATA
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[1]['name'], FETCH_HTTP_NODE)
        self.assertEqual(actions[1]['url'], first_url)
        self.assertEqual(actions[0]['messageLevel'], MESSAGE_LEVEL_WARNING)

        # Pass 2: re-run FETCH_HTTP_NODE
        result, message, actions = run_task(state, actions[1])
        self.assertTrue(result)

        result, message, actions = run_task(state, actions[1])  # INTAKE_JSON
        self.assertTrue(result)

        result, message, actions = run_task(state, actions[1])  # JSONLD_COMPACT_DATA
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['type'], ADD_NODE)
        self.assertEqual(actions[1]['name'], DETECT_AND_VALIDATE_NODE_CLASS)

    @responses.activate
    def test_verify_with_redirection(self):
        url = 'https://example.org/beths-robotics-badge.json'
        assertion_data = json.loads(test_components['2_0_basic_assertion'])
        alt_badge_url = 'http://example.org/altbadgeurl'
        assertion_data['badge'] = alt_badge_url
        responses.add(
            responses.GET, url, json=assertion_data, status=200,
            content_type='application/ld+json'
        )
        set_up_image_mock('https://example.org/beths-robot-badge.png')
        responses.add(
            responses.GET, 'https://w3id.org/openbadges/v2',
            body=test_components['openbadges_context'], status=200,
            content_type='application/ld+json'
        )
        responses.add(
            responses.GET, 'https://example.org/robotics-badge.json',
            body=test_components['2_0_basic_badgeclass'], status=200,
            content_type='application/ld+json'
        )
        responses.add(
            responses.GET, alt_badge_url,
            body=test_components['2_0_basic_badgeclass'], status=200,
            content_type='application/ld+json'
        )
        set_up_image_mock(u'https://example.org/robotics-badge.png')
        responses.add(
            responses.GET, 'https://example.org/organization.json',
            body=test_components['2_0_basic_issuer'], status=200,
            content_type='application/ld+json'
        )

        results = verify(url)

        self.assertEqual(len(results['report']['messages']), 1,
                         "There should be a warning about the redirection.")
        self.assertIn('Node fetched from source', results['report']['messages'][0]['result'],
                      "Message should be the one about the graph ID change.")
        self.assertEqual(len(results['graph']), 3)
        assertion_node = [n for n in results['graph'] if n['id'] == assertion_data['id']][0]
        self.assertEqual(assertion_node['badge'], 'https://example.org/robotics-badge.json')