import unittest

from pydux import create_store

from badgecheck.actions.input import set_input_type, store_input
from badgecheck.reducers import main_reducer
from badgecheck.state import INITIAL_STATE



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
