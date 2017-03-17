import unittest

from pydux import create_store

from badgecheck.reducers import main_reducer
from badgecheck.actions.tasks import add_task
from badgecheck.store import INITIAL_STATE


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.store = create_store(main_reducer, INITIAL_STATE)

    def test_add_task_basic(self):
        self.store.dispatch(add_task('Test task', **{'other': 123}))
        tasks = self.store.get_state().get('tasks')
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], 1)
        self.assertEqual(tasks[0]['name'], 'Test task')
        self.assertEqual(tasks[0]['other'], 123)

        self.store.dispatch(add_task('Second task'))
        self.assertEqual(len(self.store.get_state().get('tasks')), 2)
