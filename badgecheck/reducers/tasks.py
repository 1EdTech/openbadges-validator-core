from ..actions.action_types import ADD_TASK, RESOLVE_TASK, UPDATE_TASK


def task_reducer(state=None, action=None):
    if state is None or len(state) == 0:
        state = []
        task_counter = 1
    else:
        task_counter = state[-1]['id'] + 1

    if action.get('type') == ADD_TASK:
        new_task = {'id': task_counter, 'complete': False}
        for key in [k for k in action.keys() if k != 'type']:
            new_task[key] = action[key]
        return list(state) + [new_task]

    elif action.get('type') == RESOLVE_TASK:
        try:
            task = [t for t in state if t['id'] == action['id']][0]
        except KeyError:
            return state
        else:
            update = task.copy()
            update.update({
                'complete': True,
                'success': action.get('success'),
                'result': action.get('result')
            })
            return _new_state_with_updated_item(state, action['id'], update)

    elif action.get('type') == UPDATE_TASK:
        try:
            task = [t for t in state if t['id'] == action['id']][0]
        except KeyError:
            return state
        else:
            update = task.copy()
            for key in [k for k in action.keys() if k not in ('type', 'id',)]:
                update[key] = action[key]
            return _new_state_with_updated_item(state, action['id'], update)


    return state


def _new_state_with_updated_item(state, item_id, update):
    new_state = []
    for i in range(0, len(state)):
        if item_id != state[i].get('id'):
            new_state.append(state[i])
        else:
            new_state.append(update)
    return new_state
