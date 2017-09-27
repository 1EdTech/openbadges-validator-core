import unittest

from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.tasks import run_task
from openbadges.verifier.tasks.task_types import DETECT_AND_VALIDATE_NODE_CLASS


class RelatedObjectTests(unittest.TestCase):
    def test_validate_related_language(self):
        assertion = {
            'type': 'Assertion',
            'id': 'http://example.com/assertion',
            'verification': {
                'type': 'HostedBadge'
            },
            'badge': 'http://example.com/badgeclass'
        }
        badgeclass = {
            'id': 'http://example.com/badgeclass',
            'type': 'BadgeClass',
            '@language': 'es',
            'issuer': 'http://example.com/issuer',
            'related': {
                'id': 'http://example.com/other_badgeclass',
                '@language': 'en-US'
            },
            'name': 'Insignia Pronto'
        }
        state = {'graph': [assertion, badgeclass]}
        task_meta = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=badgeclass['id'])
        result, message, actions = run_task(state, task_meta)
        self.assertTrue(result)

        language_task = [t for t in actions if t.get('prop_name') == '@language'][0]
        r, _, __ = run_task(state, language_task)
        self.assertTrue(r, "The BadgeClass's language property is valid.")

        related_task = [t for t in actions if t.get('prop_name') == 'related'][0]
        result, message, actions = run_task(state, related_task)
        self.assertTrue(result, "The related property is valid and queues up task discovery for embedded node")
        result, message, actions = run_task(state, actions[0])
        self.assertTrue(result, "Some tasks are discovered to validate the related node.")
        self.assertEqual(len(actions), 2, "There are only tasks for 'id' and '@language'.")

        for a in actions:
            r, _, __ = run_task(state, a)
            self.assertTrue(r, "Related node property validation is successful.")


