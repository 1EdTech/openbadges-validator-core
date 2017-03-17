from pydux import combine_reducers

from .input import input_reducer
from .tasks import task_reducer


main_reducer = combine_reducers({
    'input': input_reducer,
    'tasks': task_reducer
})
