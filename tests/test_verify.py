import os
import responses
import unittest

from pydux import create_store

from badgecheck import verify
from badgecheck.state import INITIAL_STATE

from openbadges_bakery import bake

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

    @responses.activate
    def test_verify_of_baked_image(self):
        url = 'https://example.org/beths-robotics-badge.json'
        png_badge = os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png')
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

        with open(png_badge, 'rb') as image:
            baked_image = bake(image, test_components['2_0_basic_assertion'])
            results = verify(baked_image)

        # verify gets the JSON out of the baked image, and then detect_input_type
        # will reach out to the assertion URL to fetch the canonical assertion (thus,
        # we expect this to become an URL input type for the verifier).
        self.assertNotEqual(results, None)
        self.assertEqual(results.get('input').get('value'), url)
        self.assertEqual(results.get('input').get('input_type'), 'url')
        self.assertEqual(len(results.get('messages')), 0,
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
