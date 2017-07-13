import hashlib
import string
from urlparse import urlparse

import requests
import requests_cache
from pyld.jsonld import JsonLdError


MESSAGE_LEVEL_ERROR = 'ERROR'
MESSAGE_LEVEL_WARNING = 'WARNING'
MESSAGE_LEVEL_INFO = 'INFO'
MESSAGE_LEVELS = (MESSAGE_LEVEL_ERROR, MESSAGE_LEVEL_WARNING, MESSAGE_LEVEL_INFO,)


class CachableDocumentLoader(object):
    def __init__(self, use_cache=False, backend='memory', expire_after=300, session=None):
        self.use_cache = use_cache

        if session is not None:
            self.session = session
        elif self.use_cache:
            self.session = requests_cache.CachedSession(backend=backend, expire_after=expire_after)
        else:
            self.session = requests.Session()

    def __call__(self, url):
        try:
            # validate URLs
            pieces = urlparse(url)
            if (not all([pieces.scheme, pieces.netloc]) or
                    pieces.scheme not in ['http', 'https'] or
                    set(pieces.netloc) > set(string.ascii_letters + string.digits + '-.:')):
                raise JsonLdError(
                    'Could not dereference URL; can only load URLs using',
                    'the "http" and "https" schemes.',
                    'jsonld.InvalidUrl', {'url': url},
                    code='loading document failed')

            response = self.session.get(
                url, headers={'Accept': 'application/ld+json, application/json'})

            doc = {'contextUrl': None, 'documentUrl': url, 'document': response.text}

            if self.use_cache:
                doc['from_cache'] = response.from_cache
                self.session.remove_expired_responses()

            return doc

        except JsonLdError as e:
            raise e
        except Exception as cause:
            raise JsonLdError(
                'Could not retrieve JSON-LD document from URL.',
                'jsonld.LoadDocumentError',
                code='loading document failed',
                cause=cause)


jsonld_use_cache = {'documentLoader': CachableDocumentLoader(use_cache=True)}
jsonld_no_cache = {'documentLoader': CachableDocumentLoader(use_cache=False)}


def list_of(value):
    if isinstance(value, list):
        return value
    return [value]


def identity_hash(identfier, salt='', alg='sha256'):
    if alg == 'sha256':
        return alg + '$' + hashlib.sha256(identfier + salt).hexdigest()
    elif alg == 'md5':
        return alg + '$' + hashlib.md5(identfier + salt).hexdigest()
    raise ValueError("Alg {} not supported.".format(alg))
