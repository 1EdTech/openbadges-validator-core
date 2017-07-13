import responses
import unittest
from pydux import create_store

from badgecheck.actions.validation_report import set_validation_subject
from badgecheck.reducers import main_reducer
from badgecheck.state import INITIAL_STATE
from badgecheck.verifier import generate_report, verification_store

from testfiles.test_components import test_components
from tests.utils import set_up_context_mock


class VerificationReportTests(unittest.TestCase):
    @staticmethod
    def set_response_mocks():
        # Make sure to add @responses.activate decorator in calling method
        set_up_context_mock()
        responses.add(
            responses.GET, 'https://example.org/beths-robotics-badge.json',
            body=test_components['2_0_basic_assertion'], status=200,
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

    def test_validation_subject_reducer(self):
        """
        The validationReport should contain an ID of the root node that was validated in the graph.
        For example, if the input was the URL of an Assertion, that URL (the assertion['id'] would appear.
        """
        node_id = 'http://example.com/assertion'
        store = create_store(main_reducer, INITIAL_STATE)
        store.dispatch(set_validation_subject(node_id))
        state = store.get_state()
        self.assertEqual(state['report']['validationSubject'], node_id)

    @responses.activate
    def test_subject_set_from_badge_input(self):
        url = 'https://example.org/beths-robotics-badge.json'
        self.set_response_mocks()
        store = verification_store(url)
        report = generate_report(store)
        self.assertEqual(report['report']['validationSubject'], url)

    @responses.activate
    def test_confirmed_recipient_profile_reported(self):
        url = 'https://example.org/beths-robotics-badge.json'
        email = 'nobody@example.org'
        self.set_response_mocks()
        store = verification_store(url, recipient_profile={'email': email})
        report = generate_report(store)
        self.assertEqual(report['report']['recipientProfile']['email'], email)

    def test_validation_version(self):
        """
        The validationReport reports which version of the Open Badges spec the validationSubject was found to be in.
        prop: "openBadgesversion"
        """
        pass


    def test_messages_warnings_counts(self):
        """
        The validationReport contains the properties of messages, warningCount, errorCount, valid
        :return: 
        """
        pass
