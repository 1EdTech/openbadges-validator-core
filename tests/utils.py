import os
import responses

from badgecheck.openbadges_context import OPENBADGES_CONTEXT_V2_URI

from testfiles.test_components import test_components


# Make sure to decorate calling function with @responses.activate
def set_up_context_mock():
    context_data = test_components['openbadges_context']
    responses.add(
        responses.GET,
        OPENBADGES_CONTEXT_V2_URI,
        body=context_data,
        status=200,
        content_type='application/ld+json')


def set_up_image_mock(url):
    with open(os.path.join(os.path.dirname(__file__), 'testfiles', 'public_domain_heart.png'), 'r') as f:
        responses.add(responses.GET, url, body=f.read(), content_type='image/png')
