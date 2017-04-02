import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.tasks.validation import validate_primitive_property, ValueTypes
from badgecheck.tasks.task_types import VALIDATE_PRIMITIVE_PROPERTY


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
