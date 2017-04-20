import json
from pyld import jsonld
import requests

from ..actions.graph import add_node
from ..actions.tasks import add_task
from ..openbadges_context import OPENBADGES_CONTEXT_V2_URI
from ..utils import CachableDocumentLoader
from task_types import (DETECT_AND_VALIDATE_NODE_CLASS, JSONLD_COMPACT_DATA,
                        VALIDATE_EXPECTED_NODE_CLASS,)
from utils import task_result


def fetch_http_node(state, task_meta):
    url = task_meta['url']

    result = requests.get(
        url, headers={'Accept': 'application/ld+json, application/json, image/png, image/svg+xml'}
    )

    try:
        json.loads(result.text)
    except ValueError:
        if result.headers.get('Content-Type', 'UNKNOWN') in ['image/png', 'image/svg+xml']:
            return task_result(message='Successfully fetched image from {}'.format(url))
        return task_result(success=False, message="Response could not be interpreted from url {}".format(url))

    actions = [add_task(JSONLD_COMPACT_DATA, data=result.text, node_id=url,
                        expected_class=task_meta.get('expected_class'))]
    return task_result(message="Successfully fetched JSON data from {}".format(url), actions=actions)


def jsonld_compact_data(state, task_meta):
    try:
        input_data = json.loads(task_meta.get('data'))
    except TypeError:
        return task_result(False, "Could not load data")

    options = {'documentLoader': CachableDocumentLoader(cachable=task_meta.get('use_cache', True))}
    result = jsonld.compact(input_data, OPENBADGES_CONTEXT_V2_URI, options=options)
    # TODO: We should not necessarily trust this ID over the source URL
    node_id = result.get('id', task_meta.get('node_id'))

    actions = [add_node(node_id, data=result)]

    if task_meta.get('expected_class'):
        actions.append(
            add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=node_id,
                     expected_class=task_meta['expected_class'])
        )
    else:
        actions.append(add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=node_id))

    return task_result(
        True,
        "Successfully compacted node {}".format(node_id or "with unknown id"),
        actions
    )
