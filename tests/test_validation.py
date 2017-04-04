import json
from pydux import create_store
import unittest

from badgecheck.actions.graph import add_node
from badgecheck.actions.tasks import add_task
from badgecheck.reducers import main_reducer
from badgecheck.state import filter_active_tasks, INITIAL_STATE
from badgecheck.tasks import task_named
from badgecheck.tasks.validation import (detect_and_validate_node_class,
                                         validate_primitive_property, ValueTypes,)
from badgecheck.tasks.task_types import VALIDATE_PRIMITIVE_PROPERTY, DETECT_AND_VALIDATE_NODE_CLASS
from badgecheck.verifier import call_task

from testfiles.test_components import test_components


class PropertyValidationTaskTests(unittest.TestCase):

    def test_basic_text_property_validation(self):
        first_node = {'id': 'http://example.com/1', 'string_prop': 'string value'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='string_prop',
            prop_type=ValueTypes.TEXT,
            prop_required=False
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is present and correct; validation should pass.")
        self.assertEqual(
            message, "TEXT property string_prop valid in unknown type node {}".format(first_node['id'])
        )

        task['prop_required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Required property is present and correct; validation should pass.")
        self.assertEqual(
            message, "TEXT property string_prop valid in unknown type node {}".format(first_node['id'])
        )

        first_node['string_prop'] = 1
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop not valid in unknown type node {}".format(first_node['id'])
        )

        task['prop_required'] = False
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Optional string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop not valid in unknown type node {}".format(first_node['id'])
        )

        # When property isn't present
        second_node = {'id': 'http://example.com/1'}
        state = {'graph': [second_node]}
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")

        task['prop_required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")

    def test_basic_boolean_property_validation(self):
        first_node = {'id': 'http://example.com/1'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='bool_prop',
            prop_required=False,
            prop_type=ValueTypes.BOOLEAN
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")
        self.assertEqual(
            message, "Optional property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        task['prop_required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")
        self.assertEqual(
            message, "Required property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        first_node['bool_prop'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Required boolean property matches expectation")
        self.assertEqual(
            message, "BOOLEAN property bool_prop valid in unknown type node {}".format(first_node['id'])
        )

    def test_validation_action(self):
        store = create_store(main_reducer, INITIAL_STATE)
        first_node = {
            'text_prop': 'text_value',
            'bool_prop': True
        }
        store.dispatch(add_node(node_id="http://example.com/1", data=first_node))

        # 0. Test of an existing valid text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="text_prop",
            prop_required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 1. Test of an missing optional text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_text_prop",
            prop_required=False,
            prop_type=ValueTypes.TEXT
        ))

        # 2. Test of an present optional valid boolean prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            prop_required=False,
            prop_type=ValueTypes.BOOLEAN
        ))

        # 3. Test of a present invalid text prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            prop_required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 4. Test of a required missing boolean prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_ bool_prop",
            prop_required=True,
            prop_type=ValueTypes.BOOLEAN
        ))

        # TODO refactor while loop into callable here and in badgecheck.verifier.verify()
        last_task_id = 0
        while len(filter_active_tasks(store.get_state())):
            active_tasks = filter_active_tasks(store.get_state())
            task_meta = active_tasks[0]
            task_func = task_named(task_meta['name'])

            if task_meta['id'] == last_task_id:
                break

            last_task_id = task_meta['id']
            call_task(task_func, task_meta, store)

        state = store.get_state()
        self.assertEqual(len(state['tasks']), 5)
        self.assertTrue(state['tasks'][0]['success'], "Valid required text property is present.")
        self.assertTrue(state['tasks'][1]['success'], "Missing optional text property is OK.")
        self.assertTrue(state['tasks'][2]['success'], "Valid optional boolean property is present.")
        self.assertFalse(state['tasks'][3]['success'], "Invalid required text property is present.")
        self.assertFalse(state['tasks'][4]['success'], "Required boolean property is missing.")


class NodeTypeDetectionTasksTests(unittest.TestCase):
    def detect_assertion_type_from_node(self):
        node_data = json.loads(test_components['2_0_basic_assertion'])
        state = {'graph': [node_data]}
        task = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=node_data['id'])

        result, message, actions = detect_and_validate_node_class(state, task)
        self.assertTrue(result, "Type detection task should complete successfully.")
        self.assertEqual(len(actions), 5)

        issuedOn_task = [t for t in actions if t['prop_name'] == 'issuedOn'][0]
        self.assertEqual(issuedOn_task['prop_type'], ValueTypes.DATETIME)
