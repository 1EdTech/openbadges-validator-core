import json
from pyld import jsonld
import re
import requests
import requests_cache
import six

from ..actions.graph import add_node, patch_node
from ..actions.input import store_original_resource
from ..actions.tasks import add_task, report_message
from ..actions.validation_report import set_openbadges_version
from ..exceptions import TaskPrerequisitesError
from ..openbadges_context import OPENBADGES_CONTEXT_V2_URI
from ..reducers.graph import get_next_blank_node_id
from ..state import get_node_by_id, node_match_exists
from ..utils import list_of, jsonld_use_cache

from .task_types import (DETECT_AND_VALIDATE_NODE_CLASS, FETCH_HTTP_NODE, INTAKE_JSON, JSONLD_COMPACT_DATA,
                         UPGRADE_1_0_NODE, UPGRADE_1_1_NODE, VALIDATE_EXPECTED_NODE_CLASS, VALIDATE_EXTENSION_NODE, )
from .utils import abbreviate_node_id as abv_node, filter_tasks, is_iri, is_url, task_result, URN_REGEX
from .validation import OBClasses


def fetch_http_node(state, task_meta, **options):
    url = task_meta['url']

    if options.get('cache_backend'):
        session = requests_cache.CachedSession(
            backend=options['cache_backend'], expire_after=options.get('cache_expire_after', 300))
    else:
        session = requests.Session()

    result = session.get(
        url, headers={'Accept': 'application/ld+json, application/json, image/png, image/svg+xml'}
    )

    try:
        json.loads(result.text)
    except ValueError:
        if result.headers.get('Content-Type', 'UNKNOWN') in ['image/png', 'image/svg+xml']:
            return task_result(
                True, 'Successfully fetched image from {}'.format(url),
                store_original_resource(node_id=url, data=result.content))
        return task_result(success=False, message="Response could not be interpreted from url {}".format(url))

    actions = [
        store_original_resource(node_id=url, data=result.text),
        add_task(INTAKE_JSON, data=result.text, node_id=url,
                 expected_class=task_meta.get('expected_class'))]
    return task_result(message="Successfully fetched JSON data from {}".format(url), actions=actions)


def _detect_openbadges_version(data):
    context = data.get('@context')
    if isinstance(context, six.string_types):
        if 'v1' in context:
            return '1.1'
        elif 'v2' in context:
            return '2.0'
    elif context is None:
        if isinstance(data.get('recipient'), six.string_types):
            return '0.5'
        return '1.0'

    return '2.0'  # Default to latest version if we cannot interpret version


def intake_json(state, task_meta, **options):
    input_data = task_meta['data']
    node_id = task_meta.get('node_id')
    expected_class = task_meta.get('expected_class')
    openbadges_version = None
    actions = []

    try:
        data = json.loads(input_data)
    except TypeError:
        return task_result(False, "Could not load JSON from data")

    openbadges_version = _detect_openbadges_version(data)
    actions.append(set_openbadges_version(openbadges_version))

    if openbadges_version in ['1.1', '2.0']:
        compact_action = add_task(
            JSONLD_COMPACT_DATA, node_id=node_id, openbadges_version=openbadges_version,
            expected_class=expected_class, data=input_data
        )
        actions.append(compact_action)

    if openbadges_version == '2.0':
        pass
    elif openbadges_version == '1.1':
        actions.append(add_task(
            UPGRADE_1_1_NODE, node_id=node_id, expected_class=expected_class,
            prerequisites=[compact_action['task_key']]
        ))
    elif openbadges_version == '1.0':
        actions.append(add_task(
            UPGRADE_1_0_NODE, node_id=node_id, expected_class=expected_class, data=input_data
        ))
    else:
        return task_result(False, "Could not determine supported Open Badges object version for {}".format(node_id))

    return task_result(True, "Processed node {}".format(node_id), actions)


def _get_extension_actions(current_node, entry_path):
    new_actions = []

    if not isinstance(current_node, dict):
        return new_actions

    if current_node.get('type'):
        types = list_of(current_node['type'])
        if 'Extension' in types:
            new_actions += [add_task(
                VALIDATE_EXTENSION_NODE,
                node_path=entry_path,
                node_json=json.dumps(current_node)
            )]

    for key in [k for k in current_node.keys() if k not in ('id', 'type',)]:
        val = current_node.get(key)
        if isinstance(val, list):
            for i in range(len(val)):
                new_actions += _get_extension_actions(val[i], entry_path + [key] + [i])
        else:
            new_actions += _get_extension_actions(val, entry_path + [key])

    return new_actions


def jsonld_compact_data(state, task_meta, **options):
    try:
        input_data = json.loads(task_meta.get('data'))
    except TypeError:
        return task_result(False, "Could not load data")

    result = jsonld.compact(input_data, OPENBADGES_CONTEXT_V2_URI,
                            options=options.get('jsonld_options', jsonld_use_cache))
    node_id = result.get('id', task_meta.get('node_id', get_next_blank_node_id()))

    actions = [
        add_node(node_id, data=result)
    ] + _get_extension_actions(result, [node_id])

    if task_meta.get('expected_class'):
        actions.append(
            add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=node_id,
                     expected_class=task_meta['expected_class'])
        )
    else:
        actions.append(add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=node_id))

    return task_result(
        True,
        "Successfully compacted node {}".format(node_id),
        actions
    )


def flatten_refetch_embedded_resource(state, task_meta, **options):
    try:
        node_id = task_meta['node_id']
        node = get_node_by_id(state, node_id)
        prop_name = task_meta['prop_name']
        node_class = task_meta['node_class']
    except (IndexError, KeyError):
        raise TaskPrerequisitesError()

    actions = []
    value = node.get(prop_name)
    if value is None:
        return task_result(True, "Expected property {} was missing in node {}".format(node_id))

    if isinstance(value, six.string_types):
        return task_result(
            True, "Property {} referenced from {} is not embedded in need of flattening".format(
                prop_name, abv_node(node_id=node_id)
            ))

    if not isinstance(value, dict):
        return task_result(
            False, "Property {} referenced from {} is not a JSON object or string as expected".format(
                prop_name, abv_node(node_id=node_id)
            ))
    embedded_node_id = value.get('id')
    if embedded_node_id is None or \
            not isinstance(embedded_node_id, six.string_types) or \
            not is_iri(embedded_node_id):
        return task_result(False, "Embedded JSON object at {} has no proper assigned id.".format(
            abv_node(node_path=[node_id, prop_name])))

    elif node_class == OBClasses.Assertion and not is_url(embedded_node_id):
            if not re.match(URN_REGEX, embedded_node_id, re.IGNORECASE):
                actions.append(report_message(
                    'ID format for {} at {} not in an expected HTTP or URN:UUID scheme'.format(
                        embedded_node_id, abv_node(node_path=[node_id, prop_name])
                    )))
            actions.append(add_node(embedded_node_id, data=value))
            actions.append(actions.append(patch_node(node_id, {prop_name: embedded_node_id})))

    else:
        actions.append(patch_node(node_id, {prop_name: embedded_node_id}))
        if not node_match_exists(state, embedded_node_id) and not filter_tasks(
                state, node_id=embedded_node_id, task_type=FETCH_HTTP_NODE):
            # fetch
            actions.append(add_task(FETCH_HTTP_NODE, url=embedded_node_id))

    return task_result(True, "Embedded {} node in {} queued for storage and/or refetching as needed", actions)
