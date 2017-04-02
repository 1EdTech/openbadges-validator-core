import json
import responses
import unittest

from badgecheck.actions.graph import add_node
from badgecheck.actions.tasks import add_task
from badgecheck.reducers.graph import graph_reducer
from badgecheck.state import get_node_by_id
from badgecheck.tasks.graph import fetch_http_node, jsonld_compact_data
from badgecheck.tasks.task_types import FETCH_HTTP_NODE, JSONLD_COMPACT_DATA
from badgecheck.util import OPENBADGES_CONTEXT_URI_V2

from testfiles.test_components import test_components


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
        self.assertEqual(actions[0]['name'], JSONLD_COMPACT_DATA)
        self.assertEqual(len(actions), 1)


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
        self.assertEqual(len(state), 2)
        first_node = [node for node in state if node['id'] == 'http://example.com/node1'][0]
        self.assertEqual(first_node['key1'], 1)
        nested_node_id = first_node['nested1']
        second_node = [node for node in state if node['id'] == nested_node_id][0]
        self.assertEqual(second_node['key2'], 2)
        self.assertEqual(first_node['nested1'], second_node['id'])

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

    def test_store_flattened_lists(self):
        new_node = {
            "key1": 1,
            "b_list": [
                "b",
                {"c": 3}
            ]
        }

        state = graph_reducer([], add_node('http://example.com/node1', new_node))
        self.assertEqual(len(state), 2)
        root_node = get_node_by_id({'graph': state}, 'http://example.com/node1')
        self.assertEqual(root_node['id'], 'http://example.com/node1')
        self.assertEqual(root_node['key1'], 1)

        # the new_node's b_list's second value will now be a blank node id
        nested_id = root_node['b_list'][1]
        second_node = get_node_by_id({'graph': state}, nested_id)
        self.assertEqual(second_node['c'], 3)


class JsonLdCompactTests(unittest.TestCase):
    def setUpContextCache(self):
        data = test_components['openbadges_context']
        responses.add(
            responses.GET, OPENBADGES_CONTEXT_URI_V2,
            body=data, status=200, content_type='application/ld+json'
        )

    @responses.activate
    def test_compact_node(self):
        self.setUpContextCache()

        data = """{
            "@context": {"thing_we_call_you_by": "http://schema.org/name"},
            "thing_we_call_you_by": "Test Data"
        }"""

        task = add_task(JSONLD_COMPACT_DATA, data=data)
        task['id'] = 1

        result, message, actions = jsonld_compact_data({}, task)
        self.assertTrue(result, "JSON-LD Compaction should be successful.")
        self.assertEqual(message, "Successfully compacted node with unknown id")
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0]['data']['name'], "Test Data",
            "Node should be compacted into OB Context and use OB property names.")

    @responses.activate
    def test_reduce_compacted_output(self):
        self.setUpContextCache()

        data = {
            "@context": {"thing_we_call_you_by": "http://schema.org/name"},
            "thing_we_call_you_by": "Test Data"
        }

        task = add_task(JSONLD_COMPACT_DATA, data=json.dumps(data))
        task['id'] = 1

        result, message, actions = jsonld_compact_data({}, task)

        state = graph_reducer([], actions[0])
        self.assertEqual(len(state), 1)
        self.assertEqual(state[0]['name'], data['thing_we_call_you_by'])
        self.assertIsNotNone(state[0].get('id'))
