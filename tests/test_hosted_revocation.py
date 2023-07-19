import json
import responses
import unittest

from openbadges.verifier.actions.action_types import STORE_ORIGINAL_RESOURCE
from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.actions.utils import generate_task_signature
from openbadges.verifier.tasks.graph import fetch_http_node
from openbadges.verifier.tasks.task_types import FETCH_HTTP_NODE, INTAKE_JSON, JSONLD_COMPACT_DATA, PROCESS_410_GONE
from openbadges.verifier.verifier import verify

try:
    from .testfiles.test_components import test_components
except (ImportError, SystemError):
    from tests.testfiles.test_components import test_components

from tests.utils import set_up_image_mock


class HttpFetchingTests(unittest.TestCase):

    @responses.activate
    def test_revoked_410_assertion_invalid(self):
        """
        The specification states "If either the 410 Gone status or a response body declaring revoked true is returned,
        the Assertion should be treated as revoked and thus invalid." This test checks the 410 state
        """
        url = 'http://example.com/assertionmaybe'
        # The issuer has revoked via just the status code, not body. Ideally they do both 410 and "revoked": true
        responses.add(
            responses.GET, url,
            body=test_components['2_0_basic_assertion'],
            status=410, content_type='application/ld+json'
        )
        task = add_task(FETCH_HTTP_NODE, url=url, depth=0)

        success, message, actions = fetch_http_node({}, task)

        self.assertTrue(success)
        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0]['type'], STORE_ORIGINAL_RESOURCE)
        self.assertEqual(actions[1]['name'], INTAKE_JSON)
        self.assertEqual(actions[2]['name'], PROCESS_410_GONE)
        self.assertEqual(actions[2]['prerequisites'][0], generate_task_signature(JSONLD_COMPACT_DATA, url))

    @responses.activate
    def test_verify_of_410_assertion(self):
        url = 'https://example.org/beths-robotics-badge.json'
        responses.add(
            responses.GET, url, body=test_components['2_0_basic_assertion'], status=410,
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
        set_up_image_mock(u'https://example.org/robotics-badge.png')
        responses.add(
            responses.GET, 'https://example.org/organization.json',
            body=test_components['2_0_basic_issuer'], status=200,
            content_type='application/ld+json'
        )

        results = verify(url)
        self.assertEqual(results.get('input').get('value'), url)
        self.assertEqual(results.get('input').get('input_type'), 'url')

        self.assertEqual(
            len(results['report']['messages']), 1, "The 410 status results in an error.")

    @responses.activate
    def test_verify_of_410_endorsement_no_disruption(self):
        url = 'https://example.org/beths-robotics-badge.json'
        assertion_body = json.loads(test_components['2_0_basic_assertion'])
        assertion_body['endorsement'] = 'https://example.org/beths-robotics-endorsement.json'
        assertion_body['related'] = 'https://example.org/beths-robotics-badge2.json'
        assertion_body = json.dumps(assertion_body)
        responses.add(
            responses.GET, url, body=assertion_body, status=200,
            content_type='application/ld+json'
        )
        set_up_image_mock('https://example.org/beths-robot-badge.png')
        responses.add(
            responses.GET, 'https://example.org/beths-robotics-badge2.json', body=assertion_body, status=410,
            content_type='application/ld+json'
        )
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
        set_up_image_mock(u'https://example.org/robotics-badge.png')
        responses.add(
            responses.GET, 'https://example.org/organization.json',
            body=test_components['2_0_basic_issuer'], status=200,
            content_type='application/ld+json'
        )
        responses.add(
            responses.GET, 'https://example.org/beths-robotics-endorsement.json',
            body=test_components['2_0_basic_endorsement'], status=410,
            content_type='application/ld+json'
        )

        results = verify(url)
        self.assertEqual(results.get('input').get('value'), url)
        self.assertEqual(results.get('input').get('input_type'), 'url')

        self.assertEqual(
            len(results['report']['messages']), 0, "The 410 status of the endorsement doesn't affect validity.")
