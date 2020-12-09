import responses
import unittest

from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.openbadges_context import OPENBADGES_CONTEXT_V2_URI
from openbadges.verifier.tasks.task_types import VALIDATE_EXPECTED_NODE_CLASS
from openbadges.verifier.tasks.validation import OBClasses
from openbadges import verify
from openbadges.verifier.tasks import task_named


from .utils import set_up_context_mock, set_up_image_mock


class EndorsementTests(unittest.TestCase):
    def set_up_resources(self):
        self.assertion = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'type': 'Assertion',
            'id': 'http://example.com/assertion',
            'badge': 'http://example.com/badgeclass',
            'issuedOn': '2017-09-30T00:00Z',
            'recipient': {'identity': 'recipient@example.com', 'type': 'email', 'hashed': False},
            'verification': {
                'type': 'HostedBadge'
            }
        }
        self.badgeclass = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.com/badgeclass',
            'type': 'BadgeClass',
            'issuer': 'http://example.com/issuer',
            'endorsement': {
                '@context': OPENBADGES_CONTEXT_V2_URI,
                'id': 'http://example.org/endorsement',
                'type': 'Endorsement',
                'claim': {
                    'id': 'http://example.com/badgeclass',
                    'endorsementComment': 'Pretty good'
                },
                'issuedOn': '2017-10-01T00:00Z',
                'issuer': 'http://example.org/issuer',
                'verification': {
                    'type': "HostedBadge"
                }
            },
            'name': 'Best Badge',
            'description': 'An achievement that is good.',
            'image': 'http://example.com/badgeimage',
            'criteria': 'http://example.com/badgecriteria'
        }
        self.badgeclass_with_endorsement_array = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.com/badgeclass',
            'type': 'BadgeClass',
            'issuer': 'http://example.com/issuer',
            'endorsement': ['http://example.org/endorsement', 'http://example.org/endorsement2'],
            'name': 'Best Badge',
            'description': 'An achievement that is good.',
            'image': 'http://example.com/badgeimage',
            'criteria': 'http://example.com/badgecriteria'
        }
        self.issuer = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.com/issuer',
            'type': 'Profile',
            'name': 'Test Issuer',
            'email': 'test@example.com',
            'url': 'http://example.com'
        }
        self.endorsement = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.org/endorsement',
            'type': 'Endorsement',
            'claim': {
                'id': self.badgeclass['id'],
                'endorsementComment': 'Pretty good'
            },
            'issuedOn': '2017-10-01T00:00Z',
            'issuer': 'http://example.org/issuer',
            'verification': {
                'type': "HostedBadge"
            }
        }
        self.endorsement2 = self.endorsement.copy()
        self.endorsement2['id'] = 'http://example.org/endorsement2'
        self.endorsement_issuer = {
            '@context': OPENBADGES_CONTEXT_V2_URI,
            'id': 'http://example.org/issuer',
            'type': 'Profile',
            'name': 'Test Endorser',
            'email': 'test@example.org',
            'url': 'http://example.org'
        }

    @responses.activate
    def test_validate_linked_endorsement(self):
        set_up_context_mock()
        self.set_up_resources()

        for resource in [self.assertion, self.badgeclass, self.issuer, self.endorsement, self.endorsement_issuer]:
            responses.add(responses.GET, resource['id'], json=resource)
        set_up_image_mock(self.badgeclass['image'])

        results = verify(self.assertion['id'])
        self.assertTrue(results['report']['valid'])
        self.assertEqual(5, len(results['graph']), "The graph now contains all five resources.")

    @responses.activate
    def test_validate_linked_endorsement_array(self):
        set_up_context_mock()
        self.set_up_resources()

        for resource in [self.assertion, self.badgeclass_with_endorsement_array, self.issuer, self.endorsement, self.endorsement2, self.endorsement_issuer]:
            responses.add(responses.GET, resource['id'], json=resource)
        set_up_image_mock(self.badgeclass['image'])

        results = verify(self.assertion['id'])
        self.assertTrue(results['report']['valid'])
        self.assertEqual(6, len(results['graph']), "The graph now contains all six resources including both endorsements.")

    @responses.activate
    def test_validate_endorsement_as_input(self):
        set_up_context_mock()
        self.set_up_resources()

        for resource in [self.assertion, self.badgeclass, self.issuer, self.endorsement, self.endorsement_issuer]:
            responses.add(responses.GET, resource['id'], json=resource)
        set_up_image_mock(self.badgeclass['image'])

        results = verify(self.endorsement['id'])
        self.assertTrue(results['report']['valid'])
        self.assertEqual(2, len(results['graph']))

    def test_claim_property_validation(self):
        self.set_up_resources()

        options = {'max_validation_depth': 3}

        state = {'graph': [self.endorsement]}
        task_meta = add_task(
            VALIDATE_EXPECTED_NODE_CLASS, node_id=self.endorsement['id'], prop_name='claim',
            expected_class=OBClasses.Endorsement,
            depth=0
        )

        result, message, actions = task_named(VALIDATE_EXPECTED_NODE_CLASS)(state, task_meta, **options)
        self.assertTrue(result)
        claim_action = [a for a in actions if a.get('prop_name') == 'claim'][0]

        result, message, actions = task_named(claim_action['name'])(state, claim_action, **options)
        self.assertTrue(result)
        self.assertEqual(1, len(actions))

        result, message, actions = task_named(actions[0]['name'])(state, actions[0], **options)
        self.assertTrue(result)
        self.assertEqual(3, len(actions))
