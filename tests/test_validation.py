# coding=utf-8
from datetime import datetime, timedelta
import json
from pyld import jsonld
from pytz import utc
from pydux import create_store
import responses
import unittest

from badgecheck.actions.action_types import ADD_TASK, PATCH_NODE
from badgecheck.actions.graph import add_node, patch_node
from badgecheck.actions.tasks import add_task
from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_DICT
from badgecheck.reducers import main_reducer
from badgecheck.state import filter_active_tasks, INITIAL_STATE
from badgecheck.tasks import task_named
from badgecheck.tasks.validation import (_get_validation_actions, assertion_timestamp_checks,
                                         criteria_property_dependencies, detect_and_validate_node_class,
                                         OBClasses, PrimitiveValueValidator, validate_property, ValueTypes,)
from badgecheck.tasks.verification import (_default_verification_policy, hosted_id_in_verification_scope,)
from badgecheck.tasks.task_types import (ASSERTION_TIMESTAMP_CHECKS, CRITERIA_PROPERTY_DEPENDENCIES,
                                         DETECT_AND_VALIDATE_NODE_CLASS, HOSTED_ID_IN_VERIFICATION_SCOPE,
                                         IDENTITY_OBJECT_PROPERTY_DEPENDENCIES, ISSUER_PROPERTY_DEPENDENCIES,
                                         VALIDATE_RDF_TYPE_PROPERTY, VALIDATE_PROPERTY, VALIDATE_EXPECTED_NODE_CLASS)
from badgecheck.utils import MESSAGE_LEVEL_WARNING
from badgecheck.verifier import call_task, verify

from testfiles.test_components import test_components
from tests.utils import set_up_context_mock, set_up_image_mock


class PropertyValidationTests(unittest.TestCase):

    def test_data_uri_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.DATA_URI)
        good_uris = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=',
                     'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==',
                     'data:text/plain;charset=UTF-8;page=21,the%20data:1234,5678',
                     'data:text/vnd-example+xyz;foo=bar;base64,R0lGODdh',
                     'data:,actually%20a%20valid%20data%20URI',
                     'data:,')
        bad_uris = ('data:image/gif',
                    'http://someexample.org',
                    'data:bad:path')
        for uri in good_uris:
            self.assertTrue(validator(uri), u"`{}` should pass data URI validation but failed.".format(uri))
        for uri in bad_uris:
            self.assertFalse(validator(uri), u"`{}` should fail data URI/URL validation but passed.".format(uri))

    def test_data_uri_or_url_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.DATA_URI_OR_URL)
        good_uris = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=',
                     'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==',
                     'data:text/plain;charset=UTF-8;page=21,the%20data:1234,5678',
                     'data:text/vnd-example+xyz;foo=bar;base64,R0lGODdh',
                     'http://www.example.com:8080/', 'http://www.example.com:8080/foo/bar',
                     'http://www.example.com/foo%20bar', 'http://www.example.com/foo/bar?a=b&c=d',
                     'http://www.example.com/foO/BaR', 'HTTPS://www.EXAMPLE.cOm/',
                     'http://142.42.1.1:8080/', 'http://142.42.1.1/',
                     'http://foo.com/blah_(wikipedia)#cite-1', 'http://a.b-c.de',
                     'http://userid:password@example.com/', "http://-.~:%40:80%2f:password@example.com",
                     'http://code.google.com/events/#&product=browser')
        bad_uris = ('///', '///f', '//',
                    'rdar://12345', 'h://test', 'http:// shouldfail.com', ':// should fail', '', 'a',
                    'urn:uuid:129487129874982374', 'urn:uuid:9d278beb-36cf-4bc8-888d-674ff9843d72')
        for uri in good_uris:
            self.assertTrue(validator(uri), u"`{}` should pass data URI/URL validation but failed.".format(uri))
        for uri in bad_uris:
            self.assertFalse(validator(uri), u"`{}` should fail data URI/URL validation but passed.".format(uri))

    def test_url_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.URL)
        # Thanks to Mathias Bynens for fun URL examples: http://mathiasbynens.be/demo/url-regex
        good_urls = ('http://www.example.com:8080/', 'http://www.example.com:8080/foo/bar',
                     'http://www.example.com/foo%20bar', 'http://www.example.com/foo/bar?a=b&c=d',
                     'http://www.example.com/foO/BaR', 'HTTPS://www.EXAMPLE.cOm/',
                     'http://142.42.1.1:8080/', 'http://142.42.1.1/',
                     'http://foo.com/blah_(wikipedia)#cite-1', 'http://a.b-c.de',
                     'http://userid:password@example.com/', "http://-.~:%40:80%2f:password@example.com",
                     'http://code.google.com/events/#&product=browser')
        good_urls_that_fail = (u'http://✪df.ws/123', u'http://عمان.icom.museum/',)  # TODO: Discuss support for these
        bad_urls = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=', '///', '///f', '//',
                    'rdar://12345', 'h://test', 'http:// shouldfail.com', ':// should fail', '', 'a',
                    'urn:uuid:129487129874982374', 'urn:uuid:9d278beb-36cf-4bc8-888d-674ff9843d72')
        bad_urls_that_pass = ('http://', 'http://../', 'http://foo.bar?q=Spaces should be encoded',
                                          'http://f', 'http://-error-.invalid/', 'http://.www.foo.bar./',)

        for url in good_urls:
            self.assertTrue(validator(url), u"`{}` should pass URL validation but failed.".format(url))
        for url in bad_urls:
            self.assertFalse(validator(url), u"`{}` should fail URL validation but passed.".format(url))

    def test_iri_validation(self):
        validator = PrimitiveValueValidator(ValueTypes.IRI)
        # Thanks to Mathias Bynens for fun URL examples: http://mathiasbynens.be/demo/url-regex
        good_iris = ('http://www.example.com:8080/', '_:b0', '_:b12', '_:b107', '_:b100000001232',
                     'urn:uuid:9d278beb-36cf-4bc8-888d-674ff9843d72',
                     'urn:uuid:9D278beb-36cf-4bc8-888d-674ff9843d72'
                     )
        good_iris_that_fail = ()  # TODO: Discuss support for these
        bad_iris = ('data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=', 'urn:uuid', 'urn:uuid:123',
                    '', 'urn:uuid:', 'urn:uuid:zz278beb-36cf-4bc8-888d-674ff9843d72',)
        bad_iris_that_pass = ()

        for url in good_iris:
            self.assertTrue(validator(url), u"`{}` should pass IRI validation but failed.".format(url))
        for url in bad_iris:
            self.assertFalse(validator(url), u"`{}` should fail IRI validation but passed.".format(url))


class PropertyValidationTaskTests(unittest.TestCase):

    def test_basic_text_property_validation(self):
        first_node = {'id': 'http://example.com/1', 'string_prop': 'string value'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='string_prop',
            prop_type=ValueTypes.TEXT,
            required=False
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Optional property is present and correct; validation should pass.")

        task['required'] = True
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Required property is present and correct; validation should pass.")

        first_node['string_prop'] = 1
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Required string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop value 1 not valid in unknown type node {}".format(first_node['id'])
        )

        task['required'] = False
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Optional string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop value 1 not valid in unknown type node {}".format(first_node['id'])
        )

        # When property isn't present
        second_node = {'id': 'http://example.com/1'}
        state = {'graph': [second_node]}
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")

        task['required'] = True
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")

    def test_basic_telephone_property_validation(self):
        first_node = {
            'id': 'http://example.com'
        }
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='tel',
            required=True,
            prop_type=ValueTypes.TELEPHONE
        )

        good_values = ["+64010", "+15417522845", "+18006664358", "+18006662344;ext=666"]
        bad_values = ["1-800-666-DEVIL", "1 (555) 555-5555", "+99 55 22 1234", "+18006664343 x666"]

        for tel_value in good_values:
            first_node['tel'] = tel_value
            result, message, actions = validate_property(state, task)
            self.assertTrue(result)

        for tel_value in bad_values:
            first_node['tel'] = tel_value
            result, message, actions = validate_property(state, task)
            self.assertFalse(result)

    def test_basic_email_property_validation(self):
        first_node = {
            'id': 'http://example.com'
        }
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='email',
            required=True,
            prop_type=ValueTypes.EMAIL
        )

        good_values = ["abc@localhost", "cool+uncool@example.org"]
        bad_values = [" spacey@gmail.com", "steveman [at] gee mail dot com"]

        for val in good_values:
            first_node['email'] = val
            result, message, actions = validate_property(state, task)
            self.assertTrue(result, "{} should be marked a valid email".format(val))

        for val in bad_values:
            first_node['email'] = val
            result, message, actions = validate_property(state, task)
            self.assertFalse(result, "{} should be marked an invalid email".format(val))

    def test_basic_boolean_property_validation(self):
        first_node = {'id': 'http://example.com/1'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='bool_prop',
            required=False,
            prop_type=ValueTypes.BOOLEAN
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")
        self.assertEqual(
            message, "Optional property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        task['required'] = True
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")
        self.assertEqual(
            message, "Required property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        first_node['bool_prop'] = True
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Required boolean property matches expectation")
        self.assertEqual(
            message, "BOOLEAN property bool_prop is valid in unknown type node {}".format(first_node['id'])
        )

    def test_basic_id_validation(self):
        ## test assumes that a node's ID must be an IRI
        first_node = {'id': 'http://example.com/1'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='id',
            required=True,
            prop_type=ValueTypes.IRI
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result)
        self.assertEqual(len(actions), 0)

    def test_basic_image_prop_validation(self):
        _VALID_DATA_URI = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=='
        _VALID_IMAGE_URL = 'http://example.com/images/foo.png'
        _INVALID_URI = 'notanurl'
        first_node = {'id': 'http://example.com/1',
                      'image_prop': _VALID_DATA_URI}

        state = {
            'graph': [first_node]
        }

        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='image_prop',
            required=False,
            prop_type=ValueTypes.DATA_URI_OR_URL
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Optional image_prop URI is present and well-formed; validation should pass.")
        self.assertTrue(
            "DATA_URI_OR_URL" in message and "valid" in message
        )

        first_node['image_prop'] = _INVALID_URI
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Optional image prop is present and mal-formed; validation should fail.")
        self.assertEqual(
            message, "DATA_URI_OR_URL property image_prop value {} not valid in unknown type node {}".format(
                _INVALID_URI,
                first_node['id'])
        )

    def test_basic_url_prop_validation(self):
        _VALID_URL = 'http://example.com/2'
        _INVALID_URL = 'notanurl'
        first_node = {'id': 'http://example.com/1',
                      'url_prop': _VALID_URL}
        state = {
            'graph': [first_node]
        }

        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='url_prop',
            required=False,
            prop_type=ValueTypes.URL
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Optional URL prop is present and well-formed; validation should pass.")

        first_node['url_prop'] = _INVALID_URL
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Optional URL prop is present and mal-formed; validation should fail.")
        self.assertEqual(
            message, "URL property url_prop value {} not valid in unknown type node {}".format(
                _INVALID_URL,
                first_node['id'])
        )

    def test_basic_datetime_property_validation(self):
        _VALID_DATETIMES = ['1977-06-10T12:00:00+0800',
                            '1977-06-10T12:00:00-0800',
                            '1977-06-10T12:00:00+08',
                            '1977-06-10T12:00:00+08:00']
        _INVALID_NOTZ_DATETIMES = ['1977-06-10T12:00:00']
        _INVALID_DATETIMES = ['notadatetime']

        first_node = {'id': 'http://example.com/1', 'date_prop': '1977-06-10T12:00:00Z'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PROPERTY,
            node_id=first_node['id'],
            prop_name='date_prop',
            required=False,
            prop_type=ValueTypes.DATETIME
        )
        task['id'] = 1

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Optional date prop is present and well-formed; validation should pass.")
        self.assertEqual(
            message, "DATETIME property date_prop is valid in unknown type node {}".format(first_node['id'])
        )

        for date in _VALID_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_property(state, task)
            self.assertTrue(result,
                            "Optional date prop {} is well-formed; validation should pass.".format(date))

        for date in _INVALID_NOTZ_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_property(state, task)
            self.assertFalse(result, "Optional date prop has no tzinfo particle; validation should fail.")
            self.assertEqual(
                message,
                "DATETIME property date_prop value {} not valid in unknown type node {}".format(
                    str(date), first_node['id'])
            )

        for date in _INVALID_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_property(state, task)
            self.assertFalse(result, "Optional date prop has malformed datetime; validation should fail.")
            self.assertEqual(
                message,
                "DATETIME property date_prop value {} not valid in unknown type node {}".format(
                    str(date), first_node['id'])
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
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="text_prop",
            required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 1. Test of an missing optional text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_text_prop",
            required=False,
            prop_type=ValueTypes.TEXT
        ))

        # 2. Test of an present optional valid boolean prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            required=False,
            prop_type=ValueTypes.BOOLEAN
        ))

        num_actions = len(store.get_state()['tasks'])
        # 2b. Retesting the same property won't add any actions to state
        store.dispatch(add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            required=True,
            prop_type=ValueTypes.TEXT
        ))
        self.assertEqual(num_actions, len(store.get_state()['tasks']),
                         "Duplicate check shouldn't add another action")

        store.dispatch(patch_node(node_id="http://example.com/1", data={'bool_prop2': True}))
        # 3 Invalid text value for required bool prop should fail.
        store.dispatch(add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop2",
            required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 4. Test of a required missing boolean prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_bool_prop",
            required=True,
            prop_type=ValueTypes.BOOLEAN
        ))

        last_task_id = 0
        while len(filter_active_tasks(store.get_state())):
            active_tasks = filter_active_tasks(store.get_state())
            task_meta = active_tasks[0]
            task_func = task_named(task_meta['name'])

            if task_meta['task_id'] == last_task_id:
                break

            last_task_id = task_meta['task_id']
            call_task(task_func, task_meta, store)

        state = store.get_state()
        self.assertEqual(len(state['tasks']), 5)
        self.assertTrue(state['tasks'][0]['success'], "Valid required text property is present.")
        self.assertTrue(state['tasks'][1]['success'], "Missing optional text property is OK.")
        self.assertTrue(state['tasks'][2]['success'], "Valid optional boolean property is present.")
        self.assertFalse(state['tasks'][3]['success'], "Invalid required text property is present.")
        self.assertFalse(state['tasks'][4]['success'], "Required boolean property is missing.")

    def optional_accepts_null_values(self):
        """
        If a simple or id-type property is optional, null values should not be rejected.
        """
        pass
        # TODO: they should be filtered from the node reported at output.

    def test_many_validation(self):
        """
        When detect_and_validate_node_class (through _get_validation_actions)
        queue up actions, some configs may have many=True. This means single or multiple
        values should be accepted. If optional, empty lists should also be accepted.
        """
        first_node = {
            'id': '_:b0',
            'type': 'BadgeClass'
        }
        state = {'graph': [first_node]}

        values = (
            ['one', 'two', 'three'],  # values[0]
            'one',                    # values[1]
            1,                        # values[2]
            ['one', 2, 'three'],      # values[3]
            [],                       # values[4]
            None,                     # values[5]
            [None],                   # values[6]
            [None, None],             # values[7] Always fail
            [None, 'one', None]       # values[8] Always fail
        )

        task_config = {
            'node_id': first_node['id'], 'node_class': OBClasses.BadgeClass,
            'prop_name': 'tags', 'prop_type': ValueTypes.TEXT
        }

        t_result = t_message = t_actions = None
        def run(i, expect_success, message):
            first_node['tags'] = values[i]
            task = add_task(VALIDATE_PROPERTY, **task_config)
            t_result, t_message, t_actions = validate_property(state, task)
            msg = message + ' when required is {} and many is {}'
            self.assertEqual(t_result, expect_success, msg.format(
                task_config['required'], task_config['many']))

        task_config['required'] = True
        task_config['many'] = True
        run(0, True, "Many acceptable values pass"),
        run(1, True, "One acceptable value passes"),
        run(2, False, "One unacceptable value fails"),
        run(3, False, "List containing an unacceptable non-null value fails"),
        run(4, False, "Empty list fails"),
        run(5, False, "One null value fails"),
        run(6, False, "One null value in a list fails"),
        run(7, False, "A list with all null values fails"),
        run(8, False, "One acceptable value in a list with other null values fails"),
        del first_node['tags']
        task = add_task(VALIDATE_PROPERTY, **task_config)
        t_result, t_message, t_actions = validate_property(state, task)
        self.assertFalse(t_result, "No value present fails when required is True.")

        task_config['required'] = True
        task_config['many'] = False
        run(0, False, "Many acceptable values fail"),
        run(1, True, "One acceptable value passes"),
        run(2, False, "One unacceptable value fails"),
        run(3, False, "List containing an unacceptable non-null value fails"),
        run(4, False, "Empty list fails"),
        run(5, False, "One null value fails"),
        run(6, False, "One null value in a list fails"),
        run(7, False, "Multiple null values fail"),
        run(8, False, "One acceptable value in a list with other null values fails"),
        del first_node['tags']
        task = add_task(VALIDATE_PROPERTY, **task_config)
        t_result, t_message, t_actions = validate_property(state, task)
        self.assertFalse(t_result, "No value present fails when required is True.")

        task_config['required'] = False
        task_config['many'] = True
        run(0, True, "Many acceptable values pass"),
        run(1, True, "One acceptable value passes"),
        run(2, False, "One unacceptable value fails"),
        run(3, False, "List containing an unacceptable non-null value fails"),
        run(4, True, "Empty list passes"),
        run(5, True, "One null value passes"),
        run(6, True, "One null value in a list passes"),
        run(7, True, "Multiple null values pass"),
        run(8, False, "One acceptable value in a list with other null values fails"),
        del first_node['tags']
        task = add_task(VALIDATE_PROPERTY, **task_config)
        t_result, t_message, t_actions = validate_property(state, task)
        self.assertTrue(t_result, "No value present fails when required is False.")

        task_config['required'] = False
        task_config['many'] = False
        run(0, False, "Many acceptable values fail"),
        run(1, True, "One acceptable value passes"),
        run(2, False, "One unacceptable value fails"),
        run(3, False, "List containing an unacceptable non-null value fails"),
        run(4, True, "Empty list passes"),
        run(5, True, "One null value passes"),
        run(6, True, "One null value in a list passes"),
        run(7, True, "Multiple null values pass"),
        run(8, False, "One acceptable value in a list with other null values fails"),
        del first_node['tags']
        task = add_task(VALIDATE_PROPERTY, **task_config)
        t_result, t_message, t_actions = validate_property(state, task)
        self.assertTrue(t_result, "No value present fails when required is False.")


class IDPropertyValidationTests(unittest.TestCase):
    def test_validate_nested_identity_object(self):
        first_node = {
            'id': 'http://example.com/1',
            'recipient': {
                'id': '_:b0',
                'identity': 'two@example.com',
                'type': 'email',
                'hashed': False
            }
        }
        state = {'graph': [first_node]}

        task = add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="recipient",
            required=True,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.IdentityObject
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['expected_class'], OBClasses.IdentityObject)
        self.assertEqual(actions[0]['node_path'], [first_node['id'], 'recipient'])

    def test_validate_linked_related_resource(self):
        first_node = {
            'id': 'http://example.com/1',
            'badge': 'http://example.com/2'
        }
        state = {'graph': [first_node]}

        task = add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="badge",
            required=True,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.BadgeClass,
            fetch=True
        )

        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['expected_class'], OBClasses.BadgeClass)

    def test_many_validation_for_id_property(self):
        """
        When detect_and_validate_node_class (through _get_validation_actions)
        queue up actions, some configs may have many=True. This means single or multiple
        values should be accepted. If optional, empty lists should also be accepted.
        """
        first_node = {
            'id': '_:b0',
            'type': 'Assertion'
        }
        second_node = {
            'id': '_:b1',
            'narrative': 'Did cool stuff'
        }
        third_node = {
            'id': '_:b2',
            'narrative': 'Did more cool stuff'
        }
        state = {'graph': [first_node, second_node, third_node]}
        required = True

        task = add_task(
            VALIDATE_PROPERTY, node_id=first_node['id'], node_class=OBClasses.Assertion,
            prop_name='evidence', prop_type=ValueTypes.ID, required=required, many=True, fetch=False,
            expected_class=OBClasses.Evidence, allow_remote_url=True
        )
        result, message, actions = validate_property(state, task)
        self.assertFalse(result)
        self.assertTrue('Required property evidence not present' in message)

        first_node['evidence'] = 'http://youtube.com/avideoofmedoingthething'
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "A single string URL value should be acceptable for evidence")

        first_node['evidence'] = 'notanurl'
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "A single string value that doesn't look like a URL is not acceptable as evidence")

        first_node['evidence'] = ['http://example.com/1', 'http://example.com/2']
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Multiple string URLs should be acceptable for evidence")

        first_node['evidence'] = ['_:b1', 'http://example.com/2']
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "An embedded node and a URL should be acceptable evidence references")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['node_id'], '_:b1')

        # Test when many values are disallowed
        task = add_task(
            VALIDATE_PROPERTY, node_id=first_node['id'], node_class=OBClasses.Assertion,
            prop_name='evidence', prop_type=ValueTypes.ID, required=required, many=False, fetch=False,
            expected_class=OBClasses.Evidence, allow_remote_url=True
        )
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Many values should be rejected when many=False")
        self.assertTrue('has more than the single allowed value' in message, "Error should mention many violation")

        task = add_task(
            VALIDATE_PROPERTY, node_id=first_node['id'], node_class=OBClasses.Assertion,
            prop_name='evidence', prop_type=ValueTypes.ID, required=required, fetch=False,
            expected_class=OBClasses.Evidence, allow_remote_url=True
        )
        result, message, actions = validate_property(state, task)
        self.assertFalse(result, "Many values should be rejected when many is not present")
        self.assertTrue('has more than the single allowed value' in message, "Error should mention many violation")

    def test_many_nested_validation_for_id_property(self):
        """
        When detect_and_validate_node_class (through _get_validation_actions)
        queue up actions, some configs may have many=True. This means single or multiple
        values should be accepted. If optional, empty lists should also be accepted.
        """
        first_node = {
            'id': '_:b0',
            'type': 'BadgeClass',
            'alignment': [
                {
                    'targetName': 'Alignment One',
                    'targetUrl': 'http://example.org/alignment1'
                }
            ]
        }
        state = {'graph': [first_node]}
        required = True

        task = add_task(
            VALIDATE_PROPERTY, node_id=first_node['id'], node_class=OBClasses.BadgeClass,
            prop_name='alignment', prop_type=ValueTypes.ID, required=required, many=True, fetch=False,
            expected_class=OBClasses.AlignmentObject, allow_remote_url=False
        )
        result, message, actions = validate_property(state, task)
        self.assertTrue(result, "Task the queues up individual class validators is successful")
        self.assertEqual(len(actions), 1)

        result, message, actions = task_named(actions[0]['name'])(state, actions[0])
        self.assertTrue(result)
        for a in actions:
            self.assertEqual(a['node_path'], [first_node['id'], 'alignment', 0])
            next_result, next_message, next_actions = task_named(a['name'])(state, a)
            self.assertTrue(next_result)



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


class ClassValidationTaskTests(unittest.TestCase):
    def test_validate_identity_object_property_dependencies(self):
        first_node = {
            'id': 'http://example.com/1',
            'recipient': {
                'identity': 'sha256$c7ef86405ba71b85acd8e2e95166c4b111448089f2e1599f42fe1bba46e865c5',
                'type': 'email',
                'hashed': True,
                'salt': 'deadsea'
            }
        }
        state = {'graph': [first_node]}

        task = add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="recipient",
            required=True,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.IdentityObject
        )

        def run(cur_state, cur_task, expected_result, msg=''):
            result, message, actions = validate_property(cur_state, cur_task)
            self.assertTrue(result, "Property validation task should succeed.")
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]['expected_class'], OBClasses.IdentityObject)

            cur_task = actions[0]
            result, message, actions = task_named(cur_task['name'])(cur_state, cur_task)
            self.assertTrue(result, "IdentityObject validation task discovery should succeed.")

            for cur_task in [a for a in actions if a.get('type') == ADD_TASK]:
                val_result, val_message, val_actions = task_named(cur_task['name'])(cur_state, cur_task)
                if not cur_task['name'] == IDENTITY_OBJECT_PROPERTY_DEPENDENCIES:
                    self.assertTrue(val_result, "Test {} should pass".format(cur_task['name']))
                else:
                    self.assertEqual(val_result, expected_result,
                                     "{} should be {}: {}".format(cur_task['name'], expected_result, msg))

        # Hashed and salted
        run(state, task, True, "Good working hashed identity")

        # Identity shouldn't look hashed if it says it isn't!
        first_node['recipient']['hashed'] = False
        run(state, task, False, "Identity looks hashed and smells fishy")

        # Hash doesn't match known types.
        first_node['recipient']['hashed'] = True
        first_node['recipient']['identity'] = "sha1billiion$abc123"
        run(state, task, False, "Hash doesn't match known types")
        first_node['recipient']['identity'] = "plaintextjane@example.com"
        run(state, task, False, "Identity shouldn't look like email if hashed is true")

    def test_criteria_property_dependency_validation(self):
        state = {
            'graph': [
                {'id': '_:b0'},
                {'id': '_:b1', 'narrative': 'Do cool stuff'},
                {'id': 'http://example.com/a', 'narrative': 'Do cool stuff'},
                {'id': 'http://example.com/b', 'name': 'Another property outside of Criteria class scope'},
            ]
        }
        task = add_task(CRITERIA_PROPERTY_DEPENDENCIES, node_id="_:b1")
        result, message, actions = criteria_property_dependencies(state, task)
        self.assertTrue(result)

        task = add_task(CRITERIA_PROPERTY_DEPENDENCIES, node_id="_:b1")
        result, message, actions = criteria_property_dependencies(state, task)
        self.assertTrue(result, "Evidence with blank node ID and narrative passes.")

        task = add_task(CRITERIA_PROPERTY_DEPENDENCIES, node_id="_:b0")
        result, message, actions = criteria_property_dependencies(state, task)
        self.assertFalse(result, "Evidence with just a blank node id fails.")

        task = add_task(CRITERIA_PROPERTY_DEPENDENCIES, node_id="_:b1")
        result, message, actions = criteria_property_dependencies(state, task)
        self.assertTrue(result, "Evidence with blank node ID and narrative passes.")

        task = add_task(CRITERIA_PROPERTY_DEPENDENCIES, node_id="http://example.com/b")
        result, message, actions = criteria_property_dependencies(state, task)
        self.assertTrue(result, "External URL with unknown properties passes.")

        task = add_task(CRITERIA_PROPERTY_DEPENDENCIES, node_id="http://example.com/a")
        result, message, actions = criteria_property_dependencies(state, task)
        self.assertTrue(result, "External URL and narrative passes")

    def test_run_criteria_task_discovery_and_validation(self):
        badgeclass_node = {'id': 'http://example.com/badgeclass', 'type': 'BadgeClass'}
        state = {
            'graph': [
                badgeclass_node,
                {'id': '_:b0'},
                {'id': '_:b1', 'narrative': 'Do cool stuff'},
                {'id': 'http://example.com/a', 'narrative': 'Do cool stuff'},
                {'id': 'http://example.com/b', 'name': 'Another property outside of Criteria class scope'},
            ]
        }
        actions = [add_task(
            VALIDATE_PROPERTY,
            node_id=badgeclass_node['id'],
            prop_name="criteria",
            required=False,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.Criteria
        )]
        badgeclass_node['criteria'] = 'http://example.com/a'

        for task in actions:
            if not task.get('type') == 'ADD_TASK':
                continue
            result, message, new_actions = task_named(task['name'])(state, task)
            if new_actions:
                actions.extend(new_actions)
            self.assertTrue(result)

        self.assertEqual(len(actions), 5)
        self.assertTrue(CRITERIA_PROPERTY_DEPENDENCIES in [a.get('name') for a in actions])

    def test_run_criteria_task_discovery_and_validation_embedded(self):
        badgeclass_node = {'id': 'http://example.com/badgeclass', 'type': 'BadgeClass'}
        state = {
            'graph': [badgeclass_node]
        }
        actions = [add_task(
            VALIDATE_PROPERTY,
            node_id=badgeclass_node['id'],
            prop_name="criteria",
            required=False,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.Criteria
        )]
        badgeclass_node['criteria'] = {
            'narrative': 'Do the important things.'
        }

        for task in actions:
            if not task.get('type') == 'ADD_TASK':
                continue
            result, message, new_actions = task_named(task['name'])(state, task)
            if new_actions:
                actions.extend(new_actions)
            self.assertTrue(result)

        self.assertEqual(len(actions), 5)
        self.assertTrue(CRITERIA_PROPERTY_DEPENDENCIES in [a.get('name') for a in actions])

    def test_many_criteria_disallowed(self):
        badgeclass_node = {'id': 'http://example.com/badgeclass', 'type': 'BadgeClass'}
        state = {'graph': [badgeclass_node]}
        actions = [add_task(
            VALIDATE_PROPERTY,
            node_id=badgeclass_node['id'],
            prop_name="criteria",
            required=False,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.Criteria
        )]
        badgeclass_node['criteria'] = ['http://example.com/a', 'http://example.com/b']

        task = actions[0]
        result, message, new_actions = task_named(task['name'])(state, task)
        self.assertFalse(result, "Validation should reject multiple criteria entries")
        self.assertTrue('has more than the single allowed value' in message)

    def _setUpEvidenceState(self):
        self.first_node = {
            'id': '_:b0',
            'type': 'Assertion'
        }
        self.second_node = {
            'id': '_:b1',
            'narrative': 'Did cool stuff'
        }
        self.third_node = {
            'id': '_:b2',
            'narrative': 'Earner did more cool stuff, like photography',
            'name': 'My porfolio item',
            'descrpition': 'A photo of earner\'s cat',
            'audience': 'Ages 0-99',
            'genre': 'Photography'
        }
        self.fourth_node = {
            'id': 'http://example.com/myblog/1',
            'narrative': 'Did more cool stuff'
        }
        self.empty_narrative = {
            'id': '_:b3'
        }
        self.state = {'graph': [
            self.first_node, self.second_node,
            self.third_node, self.empty_narrative,
            self.fourth_node
        ]}

    def _run(self, task_meta, expected_result, msg='', test_task='UNKNOWN'):
        result, message, actions = validate_property(self.state, task_meta)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)

        task_meta = actions[0]
        result, message, actions = task_named(task_meta['name'])(self.state, task_meta)
        self.assertTrue(result, "Class validation task discovery should succeed.")

        for task_meta in [a for a in actions if a.get('type') == ADD_TASK]:
            val_result, val_message, val_actions = task_named(task_meta['name'])(self.state, task_meta)
            if not task_meta['name'] == test_task:
                self.assertTrue(val_result, "Test {} should pass".format(task_meta['name']))
            elif task_meta['name'] == test_task:
                self.assertEqual(
                    val_result, expected_result,
                    "{} should be {}: {}".format(task_meta['name'], expected_result, msg)
                )

    def test_evidence_class_validation(self):
        self._setUpEvidenceState()
        self.first_node['evidence'] = '_:b1'

        task = add_task(
            VALIDATE_PROPERTY,
            node_id="_:b0",
            prop_name="evidence",
            required=False,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.Evidence
        )

        self._run(task, True, 'Single embedded complete evidence node passes')
        self.first_node['evidence'] = ['_:b3']
        self._run(task, True, 'Even an evidence list containing just a blank node should not fail.')
        self.first_node['evidence'] = 'http://example.com/myblog/1'
        self._run(task, True, 'Checks run even when the Evidence node ID is an external URL')

    def test_image_object_validation(self):
        image_data_node = {'id': 'data:image/gif;base64,R0lGODlhyAAiALM...DfD0QAADs=',
                           'type': 'schema:ImageObject'}
        image_uri_node = {'id': 'http://example.com/images/Badge',
                          'type': 'schema:ImageObject',
                          'caption': 'This is an image',
                          'author': 'http://example.com/users/ProfessorDale'}

        badgeclass_node = {'id': 'http://example.com/badgeclass',
                           'type': 'BadgeClass',
                           'image': image_data_node['id']}
        assertion_node = {'id': '_:b0',
                          'type': 'Assertion',
                          'image': image_uri_node['id']}

        badgeclass_state = {'graph': [badgeclass_node, image_data_node]}
        assertion_state = {'graph': [assertion_node, image_uri_node]}

        task = add_task(
            VALIDATE_PROPERTY,
            node_id=badgeclass_node['id'],
            prop_name='image',
            prop_required=False,
            prop_type=ValueTypes.DATA_URI_OR_URL,
            expected_class=OBClasses.Image
        )

        result, message, actions = validate_property(badgeclass_state, task)
        self.assertTrue(result, "Class validation of image property as data node in BadgeClass should succeed.")

        task['node_id']=assertion_node['id']
        result, message, actions = validate_property(assertion_state, task)
        self.assertTrue(result, "Class validation of image property as uri node in Assertion should succeed.")

    def test_alignment_object_validation(self):
        self.first_node = {'id': 'http://example.com/badge1'}
        self.state = {
            'graph': [
                self.first_node,
                {'id': '_:b0'},
                {'id': '_:b1', 'targetUrl': 'http://example.com/skill1', 'targetName': 'Cool Skill'},
            ]
        }
        self.first_node['alignment'] = '_:b1'

        task = add_task(
            VALIDATE_PROPERTY,
            node_id="http://example.com/badge1",
            prop_name="alignment",
            required=False,
            prop_type=ValueTypes.ID,
            expected_class=OBClasses.AlignmentObject
        )

        self._run(task, True, 'Single embedded complete alignment node passes', test_task=None)

    def test_basic_badgeclass_validation(self):
        first_node = {
            '@context': OPENBADGES_CONTEXT_V2_DICT,
            'id': 'http://example.com/badgeclass',
            'type': 'BadgeClass',
            'name': 'Test Badge',
            'description': 'A badge of learning',
            'image': 'http://example.com/badgeimage',
            'criteria': '_:b0',
            'issuer': 'http://example.com/issuer',
            'tags': ['important', 'learning']
        }
        second_node = {'id': '_:b0', 'narrative': 'Do the important learning.'}
        state = {'graph': [first_node, second_node]}

        actions = _get_validation_actions(OBClasses.BadgeClass, first_node['id'])
        results = []
        for action in actions:
            if action['type'] == 'ADD_TASK':
                results.append(
                    task_named(action['name'])(state, action)
                )
        self.assertTrue(all(i[0] for i in results))


class RdfTypeValidationTests(unittest.TestCase):
    @responses.activate
    def test_validate_in_context_string_type(self):
        set_up_context_mock()
        input_value = {
            '@context': OPENBADGES_CONTEXT_V2_DICT,
            'id': 'http://example.com/badge1',
            'type': 'BadgeClass',
            'name': 'Chumley'
        }

        test_types = (
            ('BadgeClass',                   True),
            (['Issuer', 'Extension'],        True),
            ('AlignmentObject',              True),
            ('http://example.com/CoolClass', True),
            ('NotAKnownClass',               False),
            ([],                             False),
            (['Issuer', 'UNKNOWN'],          False),
        )

        for type_value, expected_result in test_types:
            input_value['type'] = type_value
            compact_value = jsonld.compact(input_value, OPENBADGES_CONTEXT_V2_DICT)
            state = {'graph': [compact_value]}

            task_meta = add_task(
                VALIDATE_PROPERTY,
                node_id="http://example.com/badge1",
                prop_name="type",
                required=True,
                prop_type=ValueTypes.RDF_TYPE,
                many=True
            )
            result, message, actions = task_named(task_meta['name'])(state, task_meta)
            self.assertEqual(
                result, expected_result,
                "{} didn't meet expectation of result {}".format(type_value, expected_result))

    def test_rdf_property_default_applied(self):
        """
        Ensure that when a default is provided it is added to the class if there is no type declared.
        This occurs by a UPDATE_NODE task.
        """
        first_node = {
            "@context": OPENBADGES_CONTEXT_V2_DICT,
            'id': '_:b0',
            'narrative': 'Some criteria'
        }
        task_meta = add_task(
            VALIDATE_RDF_TYPE_PROPERTY,
            node_id='_:b0',
            prop_name='type',
            required=False,
            default='Criteria',
            prop_type=ValueTypes.RDF_TYPE,
            many=True
        )
        state = {'graph': [first_node]}
        result, message, actions = task_named(task_meta['name'])(state, task_meta)

        self.assertTrue(result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['node_id'], '_:b0')
        self.assertEqual(actions[0]['type'], PATCH_NODE)

    def test_type_must_contain_one(self):
        """
        Ensure that a type property doesn't validate if it is required to contain at least one of
        one or more class options provided in task_meta['must_contain_one']
        """
        first_node = {
            "@context": OPENBADGES_CONTEXT_V2_DICT,
            'id': '_:b0',
            'name': 'Some Issuer'
        }
        task_meta = add_task(
            VALIDATE_RDF_TYPE_PROPERTY,
            node_id='_:b0',
            prop_name='type',
            required=True,
            prop_type=ValueTypes.RDF_TYPE,
            must_contain_one=['Issuer', 'Profile'],
            many=True
        )
        state = {'graph': [first_node]}
        result, message, actions = task_named(task_meta['name'])(state, task_meta)

        self.assertFalse(result)
        self.assertEqual(len(actions), 0)

        first_node['type'] = 'schema:Buffalo'
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertFalse(result, "Buffalo is not among allowable type values for this task.")
        self.assertTrue('does not have type among allowed values' in message)

        first_node['type'] = 'Issuer'
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertTrue(result, 'Issuer is one of the acceptable values for this task.')

        first_node['type'] = ['Issuer', 'schema:Buffalo']
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertTrue(result, 'Issuer as one of several values should be acceptable.')

        task_meta['must_contain_one'] = 'Assertion'
        first_node['type'] = 'A'
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertFalse(result, 'A portion of the acceptable value is not acceptable.')
        first_node['type'] = 'Assertion'
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertTrue(result, 'The exact string match between must_contain_one and type passes.')


class VerificationObjectValiationTests(unittest.TestCase):
    def test_hosted_verification_object_in_assertion(self):
        assertion = {
            'type': 'Assertion',
            'id': 'http://example.com/assertion',
            'verification': '_:b0',
            'badge': 'http://example.com/badgeclass'
        }
        verification = {
            'id': '_:b0',
            'type': 'HostedBadge'
        }
        badge = {
            'id': 'http://example.com/badgeclass',
            'issuer': 'http://example.com/issuer'
        }
        issuer = {
            'id': 'http://example.com/issuer',
            'verification': '_:b1'
        }
        issuer_verification = {
            'id': '_:b1',
            'allowedOrigins': 'example.com'
        }
        state = {'graph': [assertion, verification, badge, issuer, issuer_verification]}
        task_meta = add_task(HOSTED_ID_IN_VERIFICATION_SCOPE, node_id=assertion['id'])

        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertTrue(result)

        # Use default value for allowedOrigins:
        del issuer_verification['allowedOrigins']
        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertTrue(result)

        # Ensure startsWith is used if present
        issuer_verification['startsWith'] = 'http://example.com/'
        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertTrue(result)
        issuer_verification['startsWith'] = 'http://example.com/NOT'
        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertFalse(result)

        # Handle multiple declared values for allowedOrigins
        issuer_verification['startsWith'] = ['http://example.com/NOT', 'http://example.com/ALSONOT']
        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertFalse(result)
        issuer_verification['startsWith'] = ['http://example.com/NOT', 'http://example.com/assert']
        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertTrue(result)

        # Use default policy
        del issuer['verification']
        result, message, actions = hosted_id_in_verification_scope(state, task_meta)
        self.assertTrue(result)


class AssertionTimeStampValidationTests(unittest.TestCase):
    def test_assertion_not_expired(self):
        machine_time_now = datetime.now(utc)
        an_hour_ago = machine_time_now - timedelta(hours=1)
        two_hours_ago = an_hour_ago - timedelta(hours=1)

        assertion = {
            'id': 'http://example.com/assertion',
            'issuedOn': two_hours_ago.isoformat()
        }
        state = {'graph': [assertion]}
        task_meta = add_task(ASSERTION_TIMESTAMP_CHECKS, node_id=assertion['id'])

        result, message, actions = assertion_timestamp_checks(state, task_meta)
        self.assertTrue(result)

        assertion['expires'] = an_hour_ago.isoformat()

        result, message, actions = assertion_timestamp_checks(state, task_meta)
        self.assertFalse(result)


    def test_assertion_not_expires_before_issue(self):
        machine_time_now = datetime.now(utc)
        an_hour_ago = machine_time_now - timedelta(hours=1)
        two_hours_ago = an_hour_ago - timedelta(hours=1)

        assertion = {
            'id': 'http://example.com/assertion',
            'issuedOn': an_hour_ago.isoformat(),
            'expires': two_hours_ago.isoformat()
        }
        state = {'graph': [assertion]}
        task_meta = add_task(ASSERTION_TIMESTAMP_CHECKS, node_id=assertion['id'])

        result, message, actions = assertion_timestamp_checks(state, task_meta)
        self.assertFalse(result, "Assertion that expires before issue should not be accepted.")
        self.assertTrue('expiration is prior to issue date' in message)

    def test_assertion_not_issued_in_future(self):
        machine_time_now = datetime.now(utc)
        an_hour_future = machine_time_now + timedelta(hours=1)

        assertion = {
            'id': 'http://example.com/assertion',
            'issuedOn': an_hour_future.isoformat()
        }
        state = {'graph': [assertion]}
        task_meta = add_task(ASSERTION_TIMESTAMP_CHECKS, node_id=assertion['id'])

        result, message, actions = assertion_timestamp_checks(state, task_meta)
        self.assertFalse(result, "Assertion issued in the future should not be accepted.")
        self.assertTrue('future in ')


class BadgeClassInputValidationTests(unittest.TestCase):
    @responses.activate
    def test_can_input_badgeclass(self):
        badgeclass = {
            '@context': OPENBADGES_CONTEXT_V2_DICT,
            'id': 'http://example.com/badgeclass1',
            'type': 'BadgeClass',
            'name': 'Example Badge',
            'description': 'An example',
            'criteria': 'http://example.com/criteria',
            'issuer': 'http://example.com/issuer1',
            'image': 'http://example.com/image1',
        }
        issuer = {
            '@context': OPENBADGES_CONTEXT_V2_DICT,
            'id': 'http://example.com/issuer1',
            'type': 'Issuer',
            'name': 'Example Issuer',
            'email': 'me@example.com',
            'url': 'http://example.com'
        }
        set_up_image_mock(badgeclass['image'])

        responses.add(responses.GET, badgeclass['id'], json=badgeclass)
        responses.add(responses.GET, issuer['id'], json=issuer)
        set_up_context_mock()

        results = verify('http://example.com/badgeclass1')
        self.assertTrue(results['report']['valid'])


class IssuerClassValidationTests(unittest.TestCase):
    def test_both_issuer_and_profile_queue_class_validation(self):
        issuer = {
            '@context': OPENBADGES_CONTEXT_V2_DICT,
            'id': 'http://example.com/issuer1',
            'type': 'Issuer',
            'url': 'http://example.com'
        }

        state = {'graph': [issuer]}

        task_meta = add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=issuer['id'],
                             expected_class=issuer['type'])

        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertTrue(result)

        task_meta = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=issuer['id'])
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertTrue(result)

    def test_issuer_warn_on_non_https_id(self):
        issuer = {
            '@context': OPENBADGES_CONTEXT_V2_DICT,
            'id': 'urn:uuid:2d391246-6e0d-4dab-906c-b29770bd7aa6',
            'type': 'Issuer',
            'url': 'http://example.com'
        }
        state = {'graph': [issuer]}
        task_meta = add_task(ISSUER_PROPERTY_DEPENDENCIES, node_id=issuer['id'],
                             messageLevel=MESSAGE_LEVEL_WARNING)

        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertFalse(result)
        self.assertIn('HTTP', message)

        issuer['id'] = 'http://example.org/issuer1'
        task_meta['node_id'] = issuer['id']
        result, message, actions = task_named(task_meta['name'])(state, task_meta)
        self.assertTrue(result)
