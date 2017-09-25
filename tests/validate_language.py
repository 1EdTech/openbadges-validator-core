import unittest

from openbadges.verifier.actions.tasks import add_task
from openbadges.verifier.tasks import run_task
from openbadges.verifier.tasks.task_types import VALIDATE_EXPECTED_NODE_CLASS
from openbadges.verifier.tasks.validation import OBClasses


class ValidateLanguagePropertyTests(unittest.TestCase):
    def validate_language_prop_basic(self):
        badgeclass = {
            'id': 'http://example.org/badgeclass',
            '@language': 'en-US'
        }
        state = {'graph': [badgeclass]}
        task = add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=badgeclass['id'],
                        expected_class=OBClasses.BadgeClass)
        result, message, actions = run_task(state, task)
        self.assertTrue(result)

        l_actions = [a for a in actions if a.get('prop_name') == '@language']
        self.assertEqual(len(l_actions), 1)

        result, message, actions = run_task(state, l_actions[0])
        self.assertTrue(result)
