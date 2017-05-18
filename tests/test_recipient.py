import hashlib
import json
import responses
import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_DICT
from badgecheck.tasks.graph import jsonld_compact_data
from badgecheck.tasks.task_types import JSONLD_COMPACT_DATA, VERIFY_RECIPIENT_IDENTIFIER
from badgecheck.tasks.utils import filter_tasks
from badgecheck.tasks.validation import OBClasses, validate_expected_node_class
from badgecheck.verifier import verification_store

from testfiles.test_components import test_components

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
        recipient_profile = {'@context': OPENBADGES_CONTEXT_V2_DICT, 'email': 'nobody@example.com'}
        url = 'https://example.org/beths-robotics-badge.json'
        assertion = json.loads(test_components['2_0_basic_assertion'])
        assertion['recipient']['identity'] = 'sha256$' + hashlib.sha256(recipient_profile['email']).hexdigest()

        responses.add(
            responses.GET, url, body=json.dumps(assertion), status=200,
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

        result = verification_store(url, recipient_profile)
        profile_verification_tasks = filter_tasks(result.get_state(),
            name=VERIFY_RECIPIENT_IDENTIFIER)
        self.assertEqual(len(profile_verification_tasks), 1)
        self.assertTrue(profile_verification_tasks[0]['success'])

