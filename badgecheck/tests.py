import json

# import responses

from django.test import TestCase

from rest_framework.test import APITestCase

from . import *
from .testfiles.test_components import test_components


# def setup_minimal():
#     responses.add(
#         responses.GET, 'http://a.com/instance',
#         body=test_components['1_0_basic_instance'],
#         status=200, content_type='application/json'
#     )
#     responses.add(
#         responses.GET, 'http://a.com/badgeclass',
#         body=test_components['1_0_basic_badgeclass'],
#         status=200, content_type='application/json'
#     )
#     responses.add(
#         responses.GET, 'http://a.com/issuer',
#         body=test_components['1_0_basic_issuer'],
#         status=200, content_type='application/json'
#     )


# def setup_1_0_extra_property():
#     setup_minimal()
#     responses.add(
#         responses.GET, 'http://a.com/instance3',
#         body=test_components['1_0_basic_instance_with_extra_properties'],
#         status=200, content_type='application/json'
#     )


# def setup_bad_version():
#     responses.add(
#         responses.GET, 'http://a.com/instance2',
#         body=test_components['1_0_instance_with_errors'],
#         status=200, content_type='application/json'
#     )
#     responses.add(
#         responses.GET, 'http://a.com/badgeclass',
#         body=test_components['1_0_basic_badgeclass'],
#         status=200, content_type='application/json'
#     )
#     responses.add(
#         responses.GET, 'http://a.com/issuer',
#         body=test_components['1_0_basic_issuer'],
#         status=200, content_type='application/json'
#     )


# def setup_0_5_0_ok():
#     responses.add(
#         responses.GET, 'http://oldstyle.com/instance3',
#         body=test_components['0_5_instance'],
#         status=200, content_type='application/json'
#     )


# def setup_0_5_1_ok():
#     responses.add(
#         responses.GET, 'http://oldstyle.com/instance4',
#         body=test_components['0_5_1_instance'],
#         status=200, content_type='application/json'
#     )


# class InstanceVerificationTests(TestCase):

#     @responses.activate
#     def test_1_0_minimal(self):
#         setup_minimal()

#         rbi = RemoteBadgeInstance('http://a.com/instance')
#         abi = AnalyzedBadgeInstance(rbi, recipient_id='test@example.com')

#         self.assertEqual(abi.version, 'v1.0')
#         self.assertEqual(len(abi.non_component_errors), 0)

#     @responses.activate
#     def test_bad_version(self):
#         setup_bad_version()

#         rbi = RemoteBadgeInstance('http://a.com/instance2')
#         abi = AnalyzedBadgeInstance(rbi, recipient_id='test@example.com')
#         self.assertIsNone(abi.version)
#         self.assertFalse(abi.is_valid())
#         self.assertEqual(len(abi.all_errors()), 1)

#     @responses.activate
#     def test_0_5_ok(self):
#         setup_0_5_0_ok()

#         rbi = RemoteBadgeInstance('http://oldstyle.com/instance3')
#         abi = AnalyzedBadgeInstance(rbi, recipient_id='test@example.com')

#         self.assertEqual(abi.version, 'v0.5.0')
#         self.assertEqual(len(abi.all_errors()), 0)

#     @responses.activate
#     def test_0_5_1_ok(self):
#         setup_0_5_1_ok()
#         rbi = RemoteBadgeInstance('http://oldstyle.com/instance4')
#         abi = AnalyzedBadgeInstance(rbi, recipient_id='test@example.com')

#         self.assertEqual(abi.version, 'v0.5.1')
#         self.assertEqual(len(abi.all_errors()), 0)
#         self.assertEqual(
#             abi.data.get('badge').get('issuer').get('name'), 'Basic Issuer'
#         )

#     @responses.activate
#     def test_1_0_extra_properties(self):
#         setup_1_0_extra_property()

#         rbi = RemoteBadgeInstance('http://a.com/instance3')
#         abi = AnalyzedBadgeInstance(rbi, recipient_id='test@example.com')

#         self.assertEqual(abi.version, 'v1.0')
#         self.assertEqual(len(abi.all_errors()), 0)


# class VerifierAPITests(APITestCase):

#     @responses.activate
#     def test_1_0_minimal_url(self):
#         setup_minimal()
#         post_data = {'recipient': 'test@example.com', 'url': 'http://a.com/instance'}

#         response = self.client.post(
#             '/v1/verifier', json.dumps(post_data),
#             content_type='application/json'
#         )
#         self.assertEqual(response.status_code, 200)

#     @responses.activate
#     def test_fail_for_too_many_inputs(self):
#         """
#         The IntegritySerializer should reject requests that provide multiple
#         badge inputs.
#         """
#         setup_minimal()
#         post_data = {
#             'recipient': 'test@example.com',
#             'url': 'http://a.com/instance',
#             'assertion': json.loads(test_components['1_0_basic_instance'])
#         }

#         response = self.client.post(
#             '/v1/verifier', json.dumps(post_data),
#             content_type='application/json'
#         )
#         self.assertEqual(response.status_code, 400)
#         self.assertRegexpMatches(
#             response.data.get('non_field_errors', [''])[0],
#             r'Only one instance input field allowed'
#         )

#     @responses.activate
#     def test_bad_version_via_api(self):
#         setup_bad_version()

#         post_data = {'recipient': 'test@example.com', 'url': 'http://a.com/instance2'}

#         response = self.client.post(
#             '/v1/verifier', json.dumps(post_data),
#             content_type='application/json'
#         )
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(len(response.data.get('errors')), 1)
