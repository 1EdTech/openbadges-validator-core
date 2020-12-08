import unittest

from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.tasks import task_named
from openbadges.verifier.tasks.task_types import VALIDATE_EXPECTED_NODE_CLASS
from openbadges.verifier.tasks.validation import OBClasses


class ValidateLanguagePropertyTests(unittest.TestCase):
    def test_validate_language_prop_basic(self):
        options = {'max_validation_depth': 3}

        badgeclass = {
            'id': 'http://example.org/badgeclass',
            '@language': 'en-US'
        }
        state = {'graph': [badgeclass]}
        task = add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=badgeclass['id'],
                        expected_class=OBClasses.BadgeClass, depth=0)
        result, message, actions = task_named(VALIDATE_EXPECTED_NODE_CLASS)(state, task, **options)
        self.assertTrue(result)

        l_actions = [a for a in actions if a.get('prop_name') == '@language']
        self.assertEqual(len(l_actions), 1)

        result, message, actions = task_named(l_actions[0]['name'])(state, l_actions[0], **options)
        self.assertTrue(result)
