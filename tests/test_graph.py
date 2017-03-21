import responses
import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.actions.action_types import ADD_TASK
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
