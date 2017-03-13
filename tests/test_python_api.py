import json
import responses
import unittest

from testfiles.test_components import test_components

class TestLoadComponents(unittest.TestCase):
    def test_load_assertion_from_test_components(self):
        assertion = test_components['2_0_basic_assertion']
        assertion_value = json.loads(assertion)
        self.assertEqual(assertion_value['issuedOn'], "2016-12-31T23:59:59Z")
