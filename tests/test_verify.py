import os
import responses
import unittest

from pydux import create_store

from openbadges.verifier.actions.input import store_original_resource
from openbadges.verifier.actions.tasks import add_task, report_message
from openbadges.verifier.reducers import main_reducer
from openbadges.verifier.state import INITIAL_STATE
from openbadges.verifier.tasks import task_named
from openbadges.verifier.tasks.task_types import VALIDATE_PROPERTY
from openbadges.verifier.tasks.validation import ValueTypes
from openbadges.verifier.verifier import call_task, generate_report, verify

from openbadges_bakery import bake

try:
    from tests.testfiles.test_components import test_components
except (ImportError, SystemError):
    from .testfiles.test_components import test_components

from tests.utils import set_up_image_mock


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
            len(results['report']['messages']), 0, "There should be no failing tasks.")

    @responses.activate
    def test_verify_of_baked_image(self):
        url = 'https://example.org/beths-robotics-badge.json'
        png_badge = os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png')
        responses.add(
            responses.GET, url, body=test_components['2_0_basic_assertion'], status=200,
            content_type='application/ld+json'
        )
        set_up_image_mock(u'https://example.org/beths-robot-badge.png')
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

        with open(png_badge, 'rb') as image:
            baked_image = bake(image, test_components['2_0_basic_assertion'])
            responses.add(responses.GET, 'https://example.org/baked', body=baked_image.read(), content_type='image/png')
            results = verify(baked_image)

        # verify gets the JSON out of the baked image, and then detect_input_type
        # will reach out to the assertion URL to fetch the canonical assertion (thus,
        # we expect this to become an URL input type for the verifier).
        self.assertNotEqual(results, None)
        self.assertEqual(results.get('input').get('value'), url)
        self.assertEqual(results.get('input').get('input_type'), 'url')
        self.assertEqual(len(results['report']['messages']), 0, "There should be no failing tasks.")

        # Verify that the same result occurs when passing in the baked image url.
        another_result = verify('https://example.org/baked')
        self.assertTrue(another_result['report']['valid'])
        self.assertEqual(another_result['report']['validationSubject'], results['report']['validationSubject'])

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


class MessagesTests(unittest.TestCase):
    def test_message_reporting(self):
        store = create_store(main_reducer, INITIAL_STATE)
        store.dispatch(report_message('TEST MESSAGE'))

        state = store.get_state()
        self.assertEqual(len(state['tasks']), 1)

        result = generate_report(store)
        self.assertEqual(len(result['report']['messages']), 1)
        self.assertEqual(result['report']['messages'][0]['result'], 'TEST MESSAGE')

    def test_valid_when_no_graph(self):
        state = INITIAL_STATE.copy()
        store = create_store(main_reducer, state)
        result = generate_report(store)
        self.assertFalse(result['report']['valid'])


class ResultReportTests(unittest.TestCase):
    def test_original_json_option(self):
        store = create_store(main_reducer, INITIAL_STATE)
        store.dispatch(store_original_resource('http://example.org/1', '{"data": "test data"}'))

        report = generate_report(store)
        self.assertNotIn('original_json', list(report['input'].keys()))

        report = generate_report(store, {'include_original_json': True})
        self.assertIn('original_json', list(report['input'].keys()))

    @responses.activate
    def test_verify_with_original_json(self):
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

        result = verify(url, include_original_json=True)
        self.assertIn('original_json', list(result['input'].keys()))
        self.assertEqual(len(result['input']['original_json']), 3)
        self.assertIn(url, list(result['input']['original_json'].keys()))


class ExceptionHandlingTests(unittest.TestCase):
    def test_can_print_exception(self):
        state = INITIAL_STATE.copy()
        # Create a state that will trigger an exception
        state['graph'] = [AttributeError("Haha this isn't a dict!")]
        task = add_task(
            VALIDATE_PROPERTY, node_id='http://example.org/1', prop_name='turnips',
            prop_type=ValueTypes.TEXT)
        store = create_store(main_reducer, state)
        store.dispatch(task)

        call_task(task_named(VALIDATE_PROPERTY), store.get_state()['tasks'][0], store)

        state = store.get_state()
        self.assertEqual(len(state['tasks']), 1, 'There is one task in state.')
        task = state['tasks'][0]
        self.assertFalse(task['success'])
        self.assertIn('AttributeError:', task['result'], "assert an AttributeError is formatted as the message.")
