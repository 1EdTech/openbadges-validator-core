import responses

from openbadges_context import OPENBADGES_CONTEXT_V2_URI

from testfiles.test_components import test_components


# Make sure to decorate calling function with @responses.activate
def setUpContextMock():
    context_data = test_components['openbadges_context']
    responses.add(
        responses.GET,
        OPENBADGES_CONTEXT_V2_URI,
        body=context_data,
        status=200,
        content_type='application/ld+json')
