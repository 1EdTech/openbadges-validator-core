from pydux import combine_reducers

from .input import store_input


main_reducer = combine_reducers({
    'input': store_input
})
