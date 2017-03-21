import unittest

from pydux import create_store

from badgecheck.actions.input import set_input_type, store_input
from badgecheck.reducers import main_reducer
from badgecheck.state import INITIAL_STATE
from badgecheck.tasks.input import detect_input_type


class InputReducerTests(unittest.TestCase):
    def setUp(self):
        self.store = create_store(main_reducer, INITIAL_STATE)

    def test_store_input(self):
        self.store.dispatch(store_input("http://example.com/url1"))
        self.assertEqual(self.store.get_state().get('input').get('value'), 'http://example.com/url1')

    def test_set_input_type(self):
        self.store.dispatch(store_input("http://example.com/url1"))
        self.store.dispatch(set_input_type('url'))
        self.assertEqual(self.store.get_state().get('input').get('input_type'), 'url')


class InputTaskTests(unittest.TestCase):
    def test_input_url_type_detection(self):
        """
        The detect_input_type task should successfully detect
        """
        url = 'http://example.com/assertionmaybe'
        state = INITIAL_STATE.copy()
        state['input']['value'] = url

        success, message, actions = detect_input_type(state)

        self.assertTrue(success)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['type'], 'SET_INPUT_TYPE')
        self.assertEqual(actions[1]['url'], url)

