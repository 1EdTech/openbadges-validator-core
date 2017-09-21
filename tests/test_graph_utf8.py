# -*- coding: utf-8 -*-

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
from openbadges.verifier.utils import MESSAGE_LEVEL_WARNING,make_utf8
from openbadges.verifier.verifier import verify

from .utils import set_up_context_mock, set_up_image_mock




try:
    from .testfiles.test_utf8_components import test_utf8_components
except (ImportError, SystemError):
    from .testfiles.test_utf8_components import test_utf8_components



class HttpFetchingUTF8Tests(unittest.TestCase):

    @responses.activate
    def test_basic_http_fetch_task(self):
        url = 'http://example.org/Краљ_Петар'
        responses.add(
            responses.GET, url,
            body=test_utf8_components['2_0_basic_utf8_assertion'],
            status=200, content_type='application/ld+json'
        )
        task = add_task(FETCH_HTTP_NODE, url=url)

        import requests
        resp = requests.get(url)
        self.assertEqual(resp.status_code,200)


        success, message, actions = fetch_http_node({}, task)

        self.assertTrue(success)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['type'], STORE_ORIGINAL_RESOURCE)
        self.assertEqual(actions[1]['name'], INTAKE_JSON)


