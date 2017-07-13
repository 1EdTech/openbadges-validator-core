import os.path
from requests_cache import CachedSession
import responses
import unittest

from badgecheck.actions.tasks import add_task
from badgecheck.actions.action_types import STORE_ORIGINAL_RESOURCE
from badgecheck.reducers.input import input_reducer
from badgecheck.tasks import task_named
from badgecheck.tasks.validation import OBClasses
from badgecheck.tasks.task_types import (IMAGE_VALIDATION, VALIDATE_EXPECTED_NODE_CLASS)
from badgecheck.utils import CachableDocumentLoader


class ImageValidationTests(unittest.TestCase):
    @responses.activate
    def test_validate_badgeclass_image_formats(self):
        session = CachedSession(backend='memory', expire_after=100000)
        loader = CachableDocumentLoader(use_cache=True, session=session)
        options = {
            'jsonld_options': {'documentLoader': loader}
        }
        image_url = 'http://example.org/awesomebadge.png'
        badgeclass = {
            'id': 'http://example.org/badgeclass',
            'name': 'Awesome badge',
            'image': image_url
        }
        state = {'graph': [badgeclass]}

        with open(os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png'), 'r') as f:
            responses.add(responses.GET, badgeclass['image'], body=f.read(), content_type='image/png')
        response = session.get(badgeclass['image'])
        self.assertEqual(response.status_code, 200)

        task_meta = add_task(
            VALIDATE_EXPECTED_NODE_CLASS, node_id=badgeclass['id'], expected_class=OBClasses.BadgeClass)

        result, message, actions = task_named(VALIDATE_EXPECTED_NODE_CLASS)(state, task_meta, **options)
        self.assertTrue(result)

        image_task = [a for a in actions if a.get('prop_name') == 'image'][0]
        class_image_validation_task = [a for a in actions if a.get('name') == IMAGE_VALIDATION][0]
        result, message, actions = task_named(image_task['name'])(state, image_task, **options)
        self.assertTrue(result)
        self.assertEqual(len(actions), 0)

        result, message, actions = task_named(class_image_validation_task['name'])(
            state, class_image_validation_task, **options)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1)
        # self.assertEqual(actions[0]['name'], STORE_ORIGINAL_RESOURCE)

        # Case 2: Embedded image document
        badgeclass['image'] = {
            'id': 'http://example.org/awesomebadge.png',
            'author': 'http://someoneelse.org/1',
            'caption': 'A hexagon with attitude'
        }

        # Validate BadgeClass, queuing the image node validation task
        result, message, actions = task_named(image_task['name'])(state, image_task, **options)
        self.assertTrue(result)
        self.assertEqual(len(actions), 1, "Image node validation task queued")

        # Run image node task discovery
        next_task = actions[0]
        result, message, actions = task_named(next_task['name'])(state, next_task, **options)
        self.assertTrue(result)

        # Run validation task for the Image node
        next_task = [a for a in actions if a.get('name') == IMAGE_VALIDATION][0]
        result, message, actions = task_named(next_task['name'])(state, next_task, **options)
        self.assertTrue(result)

        # Store image data
        next_task = actions[0]
        self.assertEqual(next_task['type'], STORE_ORIGINAL_RESOURCE)
        new_state = input_reducer({}, next_task)
        self.assertTrue(new_state['original_json'][image_url].startswith('data:'), "Data is stored in the expected spot.")
