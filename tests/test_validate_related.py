import unittest

from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.tasks import run_task, task_named
from openbadges.verifier.tasks.task_types import DETECT_AND_VALIDATE_NODE_CLASS


class RelatedObjectTests(unittest.TestCase):
    def test_validate_related_language(self):
        options = {'max_validation_depth': 3}

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
        task_meta = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=badgeclass['id'], depth=0)
        result, message, actions = task_named(DETECT_AND_VALIDATE_NODE_CLASS)(state, task_meta, **options)
        self.assertTrue(result)

        language_task = [t for t in actions if t.get('prop_name') == '@language'][0]
        r, _, __ = run_task(state, language_task)
        self.assertTrue(r, "The BadgeClass's language property is valid.")

        related_task = [t for t in actions if t.get('prop_name') == 'related'][0]
        result, message, actions = task_named(related_task['name'])(state, related_task, **options)
        self.assertTrue(result, "The related property is valid and queues up task discovery for embedded node")
        result, message, actions = task_named(actions[0]['name'])(state, actions[0], **options)
        self.assertTrue(result, "Some tasks are discovered to validate the related node.")
        self.assertEqual(len(actions), 2, "There are only tasks for 'id' and '@language'.")

        for a in actions:
            r, _, __ = run_task(state, a)
            self.assertTrue(r, "Related node property validation is successful.")

    def test_validate_multiple_related_languages(self):
        options = {'max_validation_depth': 3}

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
            'related': [{
                'id': 'http://example.com/other_badgeclass',
                '@language': 'en-US'
            },
            {
                'id': 'http://example.com/another_badgeclass',
                '@language': 'fi'
            }],
            'name': 'Insignia Pronto'
        }
        state = {'graph': [assertion, badgeclass]}
        task_meta = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=badgeclass['id'], depth=0)
        result, message, actions = task_named(DETECT_AND_VALIDATE_NODE_CLASS)(state, task_meta, **options)
        self.assertTrue(result)

        language_task = [t for t in actions if t.get('prop_name') == '@language'][0]
        r, _, __ = task_named(language_task['name'])(state, language_task, **options)
        self.assertTrue(r, "The BadgeClass's language property is valid.")

        related_task = [t for t in actions if t.get('prop_name') == 'related'][0]
        result, message, actions = task_named(related_task['name'])(state, related_task, **options)
        self.assertTrue(result, "The related property is valid and queues up task discovery for embedded node")
        self.assertEqual(len(actions), 2, "It has now discovered two nodes to test.")
