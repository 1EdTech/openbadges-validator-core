import hashlib
import json
import responses
import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_DICT
from badgecheck.state import filter_failed_tasks
from badgecheck.tasks.graph import jsonld_compact_data
from badgecheck.tasks.task_types import JSONLD_COMPACT_DATA, VERIFY_RECIPIENT_IDENTIFIER
from badgecheck.tasks.utils import filter_tasks
from badgecheck.tasks.validation import OBClasses
from badgecheck.tasks.verification import verify_recipient_against_trusted_profile
from badgecheck.verifier import verification_store

from testfiles.test_components import test_components
from tests.utils import set_up_image_mock


class RecipientProfileVerificationTests(unittest.TestCase):
    def test_jsonld_compact_recipient_profile(self):
        recipient_profile = {'@context': OPENBADGES_CONTEXT_V2_DICT, 'email': 'nobody@example.com'}
        task_meta = add_task(
            JSONLD_COMPACT_DATA,
            data=json.dumps(recipient_profile),
            expected_class=OBClasses.ExpectedRecipientProfile)
        state = {}

        result, message, actions = jsonld_compact_data(state, task_meta)
        self.assertTrue(result)
        self.assertEqual(len(actions), 2)

    @responses.activate
    def test_verify_badge_against_expected_profile(self):
        recipient_profile = {'email': 'nobody@example.org'}
        url = 'https://example.org/beths-robotics-badge.json'
        assertion = json.loads(test_components['2_0_basic_assertion'])
        assertion['recipient']['identity'] = 'sha256$' + hashlib.sha256(
            recipient_profile['email'] + assertion['recipient']['salt']).hexdigest()

        responses.add(
            responses.GET, url, body=json.dumps(assertion), status=200,
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
        set_up_image_mock('https://example.org/robotics-badge.png')
        responses.add(
            responses.GET, 'https://example.org/organization.json',
            body=test_components['2_0_basic_issuer'], status=200,
            content_type='application/ld+json'
        )

        result = verification_store(url, recipient_profile)
        state = result.get_state()
        profile_verification_tasks = filter_tasks(state, name=VERIFY_RECIPIENT_IDENTIFIER)

        self.assertEqual(len(filter_failed_tasks(state)), 0)
        self.assertEqual(len(profile_verification_tasks), 1)
        self.assertTrue(profile_verification_tasks[0]['success'])

        recipient_profile = {'email': ['otheremail@example.org', 'nobody@example.org']}
        result = verification_store(url, recipient_profile)
        state = result.get_state()
        profile_verification_tasks = filter_tasks(state, name=VERIFY_RECIPIENT_IDENTIFIER)
        self.assertEqual(len(filter_failed_tasks(state)), 0)
        self.assertEqual(len(profile_verification_tasks), 1)
        self.assertTrue(profile_verification_tasks[0]['success'])

    def test_profile_with_salted_hashed_email(self):
        recipient_profile = {'id': '_:b0', 'email': 'nobody@example.org'}
        assertion = {
            'id': 'http://example.org',
            'type': 'Assertion',
            'recipient': '_:b1'
        }
        identity_object = {
            'id': '_:b1',
            'type': 'email',
            'hashed': True,
            'salt': 'Maldon',
            'identity': 'sha256$' + hashlib.sha256(recipient_profile['email'] + 'Maldon').hexdigest()
        }

        state = {'graph': [recipient_profile, assertion, identity_object]}
        task_meta = add_task(VERIFY_RECIPIENT_IDENTIFIER, node_id='_:b0')

        result, message, actions = verify_recipient_against_trusted_profile(state, task_meta)
        self.assertTrue(result)
        self.assertIn('nobody@example.org', message)

    def test_unknown_identity_type(self):
        recipient_profile = {'id': '_:b0', 'schema:duns': '999999999'}
        assertion = {
            'id': 'http://example.org',
            'type': 'Assertion',
            'recipient': '_:b1'
        }
        identity_object = {
            'id': '_:b1',
            'type': 'schema:duns',
            'hashed': True,
            'salt': 'HimalayanPink',
            'identity': 'sha256$' + hashlib.sha256(
                recipient_profile['schema:duns'] + 'HimalayanPink').hexdigest()
        }

        state = {'graph': [recipient_profile, assertion, identity_object]}
        task_meta = add_task(VERIFY_RECIPIENT_IDENTIFIER, node_id='_:b0')

        result, message, actions = verify_recipient_against_trusted_profile(state, task_meta)
        self.assertTrue(result)
        self.assertIn(recipient_profile['schema:duns'], message)
        self.assertEqual(len(actions), 2)
        self.assertIn('schema:duns', actions[0]['message'], "Non-standard identifier reported")

    def test_profile_with_multiple_emails(self):
        recipient_profile = {'id': '_:b0', 'email': ['nobody@example.org', 'myaltemail@example.org']}
        assertion = {
            'id': 'http://example.org',
            'type': 'Assertion',
            'recipient': '_:b1'
        }
        identity_object = {
            'id': '_:b1',
            'type': 'email',
            'hashed': False,
            'identity': 'nobody@example.org'
        }

        state = {'graph': [recipient_profile, assertion, identity_object]}
        task_meta = add_task(VERIFY_RECIPIENT_IDENTIFIER, node_id='_:b0')

        result, message, actions = verify_recipient_against_trusted_profile(state, task_meta)
        self.assertTrue(result)
        self.assertIn('nobody@example.org', message)
