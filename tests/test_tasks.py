import unittest

from pydux import create_store

from badgecheck.reducers import main_reducer
from badgecheck.actions.tasks import add_task, resolve_task
from badgecheck.reducers.tasks import _new_state_with_updated_item
from badgecheck.state import INITIAL_STATE, filter_active_tasks


class TaskActionTests(unittest.TestCase):
    def setUp(self):
        self.store = create_store(main_reducer, INITIAL_STATE)

    def test_add_task_basic(self):
        self.store.dispatch(add_task('DETECT_INPUT_TYPE', **{'other': 123}))
        tasks = self.store.get_state().get('tasks')
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], 1)
        self.assertEqual(tasks[0]['name'], 'DETECT_INPUT_TYPE')
        self.assertEqual(tasks[0]['other'], 123)

        self.store.dispatch(add_task('DETECT_INPUT_TYPE'))
        tasks = self.store.get_state().get('tasks')
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1]['id'], 2)

    def test_cannot_add_unknown_task(self):
        with self.assertRaises(AssertionError):
            self.store.dispatch(add_task('UNKNOWN_SOLDIER'))

    def test_resolve_task(self):
        self.store.dispatch(add_task('DETECT_INPUT_TYPE', **{'other': 123}))
        tasks = self.store.get_state().get('tasks')
        self.assertEqual(len(filter_active_tasks(self.store.get_state())), 1)

        self.store.dispatch(resolve_task(tasks[0]['id']))
        tasks = self.store.get_state().get('tasks')
        self.assertTrue(tasks[0]['complete'])
        self.assertEqual(len(filter_active_tasks(self.store.get_state())), 0)


    def test_task_updater_internals(self):
        initial = [{'id': 1}, {'id': 2}, {'id': 3}]
        updated = _new_state_with_updated_item(initial, 2, {'id': 2, 'foo': 'bar'})
        self.assertEqual(updated[1].get('foo'), 'bar')
