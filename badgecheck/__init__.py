from pydux import create_store

from actions.input import store_input
from reducers import main_reducer
from store import INITIAL_STATE


def verify(badge_input):
    store = create_store(main_reducer, INITIAL_STATE)
    store.dispatch(store_input(badge_input))

    return store.get_state()
