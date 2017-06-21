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
from tests.utils import setUpContextMock


class ImageValidationTests(unittest.TestCase):
    def test_validate_badgeclass_image_formats(self):
        badgeclass = {
            'id': 'http://example.org/badgeclass',
            'name': 'Awesome badge',
            'image': 'http://example.org/awesomebadge.png'
        }
        state = {'graph': [badgeclass]}

        task_meta = add_task(
            VALIDATE_EXPECTED_NODE_CLASS, node_id=badgeclass['id'], expected_class=OBClasses.BadgeClass)

        result, message, actions = task_named(VALIDATE_EXPECTED_NODE_CLASS)(state, task_meta)

        self.assertTrue(result)
        image_task = [a for a in actions if a['prop_name'] == 'image'][0]
        result, message, actions = task_named(image_task['name'])(state, image_task)

        self.assertTrue(result)
