import json
from pyld import jsonld
import requests

from ..actions.graph import add_node
from ..actions.tasks import add_task
from ..util import CachableDocumentLoader, OPENBADGES_CONTEXT_URI_V2
from task_types import JSONLD_COMPACT_DATA
from utils import task_result


def fetch_http_node(state, task_meta):
    url = task_meta['url']

    result = requests.get(
        url, headers={'Accept': 'application/ld+json, application/json, image/png, image/svg+xml'}
    )

    try:
        data = json.loads(result.text)
    except ValueError:
        if result.headers.get('Content-Type', 'UNKNOWN') in ['image/png', 'image/svg+xml']:
            return task_result(message='Successfully fetched image from {}'.format(url))
        return task_result(success=False, message="Response could not be interpreted from url {}".format(url))

    actions = [add_task(JSONLD_COMPACT_DATA, data=data, node_id=url)]
    return task_result(message="Successfully fetched JSON data from {}".format(url), actions=actions)


def jsonld_compact_data(state, task_meta):
    # TODO: Cache-friendly JSON-LD compaction into the Open Badges context
    input_data = json.loads(task_meta.get('data'))

    node_id = task_meta.get('node_id')
    options = {'documentLoader': CachableDocumentLoader(cachable=task_meta.get('use_cache', True))}

    result = jsonld.compact(input_data, OPENBADGES_CONTEXT_URI_V2, options=options)
    actions = [add_node(node_id, data=result)]

    return task_result(
        True,
        "Successfully compacted node {}".format(node_id or "with unknown id"),
        actions
    )
