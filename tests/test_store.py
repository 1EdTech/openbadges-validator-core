import responses
import unittest

from pydux import create_store

from badgecheck import verify
from badgecheck.reducers import main_reducer
from badgecheck.state import (filter_active_tasks, INITIAL_STATE, get_node_by_id,
                              get_node_by_path,)

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


class FindNodeByPathTests(unittest.TestCase):
    def test_find_node_with_single_length_path(self):
        state = {
            'graph': [{'id': '_:b0'}]
        }
        with self.assertRaises(IndexError):
            get_node_by_path(state, ['_:b100'])

        self.assertEqual(get_node_by_path(state, ['_:b0']), state['graph'][0])

        state['graph'].append({'id': '_:b1', 'prop': '_:b0'})
        self.assertEqual(get_node_by_path(state, ['_:b1', 'prop']), state['graph'][0])

        state['graph'].append({'id': '_:b2', 'prop': ['http://unknown.external', '_:b1']})
        self.assertEqual(get_node_by_path(state, ['_:b2', 'prop', 1]), state['graph'][1])
        self.assertEqual(get_node_by_path(state, ['_:b2', 'prop', 1, 'prop']), state['graph'][0])