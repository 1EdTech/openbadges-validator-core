from ..action_types import ADD_TASK, DELETE_TASK, RESOLVE_TASK, UPDATE_TASK


def task_reducer(state=None, action=None):
    if state is None or len(state) == 0:
        state = []
        task_counter = 1
    else:
        task_counter = state[-1]['id'] + 1

    if action.get('type') == ADD_TASK:
        new_task = {'id': task_counter}
        for key in action.keys():
            if key != 'type':
                new_task[key] = action[key]
        return list(state) + [new_task]

    return state
