import responses
import unittest

from badgecheck.actions.graph import add_node
from badgecheck.actions.tasks import add_task
from badgecheck.reducers.graph import graph_reducer
from badgecheck.tasks.graph import fetch_http_node
from badgecheck.tasks.task_types import FETCH_HTTP_NODE, JSONLD_COMPACT_DATA

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
