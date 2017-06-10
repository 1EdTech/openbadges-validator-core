import json
from pyld import jsonld
import responses
import unittest

from badgecheck.utils import CachableDocumentLoader

from testfiles.test_components import test_components
from utils import setUpContextMock


class DocumentLoaderTests(unittest.TestCase):
    @responses.activate
    def test_that_caching_loader_uses_local_cache(self):
        url = 'http://example.com/assertionmaybe'
        loadurl = CachableDocumentLoader(use_cache=True)
        data = test_components['2_0_basic_assertion']
        responses.add(
            responses.GET, url, body=data, status=200, content_type='application/ld+json')

        first_remote_document = loadurl(url)
        second_remote_document = loadurl(url)

        self.assertFalse(first_remote_document.get('from_cache'))
        self.assertTrue(second_remote_document.get('from_cache'))
        self.assertEqual(
            first_remote_document.get('document'), second_remote_document.get('document'))
        self.assertEqual(first_remote_document.get('document'), data)

    @responses.activate
    def test_that_noncaching_loader_loads_url(self):
        url = 'http://example.com/assertionmaybe'
        loadurl = CachableDocumentLoader(use_cache=False)
        data = test_components['2_0_basic_assertion']
        responses.add(
            responses.GET, url, body=data, status=200, content_type='application/ld+json')

        document = loadurl(url)

        self.assertEqual(document.get('from_cache', 'Uncached'), 'Uncached')
        self.assertEqual(document.get('document'), data)

    @responses.activate
    def test_that_pyld_accepts_caching_loader_for_compaction(self):
        assertion_data = json.loads(test_components['2_0_basic_assertion'])
        context_url = assertion_data['@context']
        loadurl = CachableDocumentLoader(use_cache=True)
        setUpContextMock()

        first_compacted = jsonld.compact(
            assertion_data, context_url, options={'documentLoader': loadurl})
        second_compacted = jsonld.compact(
            assertion_data, context_url, options={'documentLoader': loadurl})
        # in order to have 'HostedBadge' as the verification type, the assertion_data
        # needs to have gone through compaction against the openbadges context document
        self.assertEqual(first_compacted['verification']['type'], u'HostedBadge')
        # second compaction should have built from the cache
        self.assertEqual(first_compacted['verification']['type'],
                         second_compacted['verification']['type'])
