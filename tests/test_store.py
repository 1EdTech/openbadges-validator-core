import responses
import unittest

from pydux import create_store

from badgecheck import verify
from badgecheck.reducers import main_reducer
from badgecheck.state import filter_active_tasks, INITIAL_STATE

from testfiles.test_components import test_components


class InitializationTests(unittest.TestCase):
    def test_store_initialization(self):
        def no_op(state, action):
            return state
        store = create_store(no_op, INITIAL_STATE)
        self.assertEqual(store.get_state(), INITIAL_STATE)


class TaskFilterTests(unittest.TestCase):
    def test_active_filter(self):
        tasks = [
            {'name': 'Carl', 'complete': True},
            {'name': 'Tim', 'complete': True},
            {'name': 'Linda', 'complete': False},
        ]
        state = {'tasks': tasks}

        active_tasks = filter_active_tasks(state)
        self.assertEqual(len(active_tasks), 1, "There should only be one active (incomplete) task")
        self.assertEqual(active_tasks[0]['name'], 'Linda')

        mary = {'name': 'Mary', 'complete': False, 'prerequisites': 'Tim'}
        tasks.append(mary)
        active_tasks = filter_active_tasks(state)
        self.assertEqual(len(active_tasks), 2, "Task whose prereq has been met should be active")

        mary['prerequisites'] = ['Tim', 'Carl']
        active_tasks = filter_active_tasks(state)
        self.assertEqual(len(active_tasks), 2, "Task whose prereqs has been met should be active")

        mary['prerequisites'] = ['Tim', 'Linda']
        active_tasks = filter_active_tasks(state)
        self.assertEqual(len(active_tasks), 1, "Task with an incomplete prereq should not be active")
