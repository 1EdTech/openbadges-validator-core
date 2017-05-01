from ..actions.action_types import ADD_TASK, RESOLVE_TASK, UPDATE_TASK


def task_reducer(state=None, action=None):
    if state is None or len(state) == 0:
        state = []
        task_counter = 1
    else:
        task_counter = state[-1]['task_id'] + 1

    if action.get('type') == ADD_TASK:
        new_task = {'task_id': task_counter, 'complete': False}
        for key in [k for k in action.keys() if k != 'type']:
            new_task[key] = action[key]
        return list(state) + [new_task]

    elif action.get('type') == RESOLVE_TASK:
        try:
            task = [t for t in state if t['task_id'] == action['task_id']][0]
        except KeyError:
            return state
        else:
            update = task.copy()
            update.update({
                'complete': True,
                'success': action.get('success'),
                'result': action.get('result')
            })
            return _new_state_with_updated_item(state, action['task_id'], update)

    elif action.get('type') == UPDATE_TASK:
        try:
            task = [t for t in state if t['task_id'] == action['task_id']][0]
        except KeyError:
            return state
        else:
            update = task.copy()
            for key in [k for k in action.keys() if k not in ('type', 'task_id',)]:
                update[key] = action[key]
            return _new_state_with_updated_item(state, action['task_id'], update)


    return state


def _new_state_with_updated_item(state, item_id, update):
    new_state = []
    for i in range(0, len(state)):
        if item_id != state[i].get('task_id'):
            new_state.append(state[i])
        else:
            new_state.append(update)
    return new_state
