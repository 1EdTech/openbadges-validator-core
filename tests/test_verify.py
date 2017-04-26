import responses
import unittest

from pydux import create_store

from badgecheck import verify
from badgecheck.reducers import main_reducer
from badgecheck.state import INITIAL_STATE

from testfiles.test_components import test_components


class InitializationTests(unittest.TestCase):
    def test_store_initialization(self):
        def no_op(state, action):
            return state
        store = create_store(no_op, INITIAL_STATE)
        self.assertEqual(store.get_state(), INITIAL_STATE)

    @responses.activate
    def test_verify_function(self):
        url = 'https://example.org/beths-robotics-badge.json'
        responses.add(
            responses.GET, url, body=test_components['2_0_basic_assertion'], status=200,
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
        responses.add(
            responses.GET, 'https://example.org/organization.json',
            body=test_components['2_0_basic_issuer'], status=200,
            content_type='application/ld+json'
        )

        results = verify(url)
        self.assertEqual(results.get('input').get('value'), url)
        self.assertEqual(results.get('input').get('input_type'), 'url')

        self.assertEqual(
            len(results.get('messages')), 0,
            "There should be no failing tasks.")

    # def debug_live_badge_verification(self):
    #     """
    #     Developers: Uncomment this test to run a quick verification check in your debugger.
    #     Because this test method name doesn't start with 'test', it will not be automatically run
    #     even when uncommented.
    #     """
    #     results = verify(
    #         'http://NOTAVALIDURL.COM')
    #
    #     self.assertTrue(results['valid'])
