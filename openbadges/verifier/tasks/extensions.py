import json
import jsonschema
from pyld import jsonld

from ..actions.tasks import add_task
from ..exceptions import TaskPrerequisitesError
from ..extensions import ALL_KNOWN_EXTENSIONS
from ..openbadges_context import OPENBADGES_CONTEXT_V2_URI
from ..state import get_node_by_id, get_node_by_path
from ..utils import jsonld_use_cache, list_of

from .task_types import VALIDATE_EXTENSION_NODE, VALIDATE_EXTENSION_SINGLE
from .utils import abbreviate_value as abv, abbreviate_node_id as abv_node, is_iri, filter_tasks, task_result


def validate_single_extension(state, task_meta, **options):
    # node, extension, node_json=None, node_id_string=None, context_urls=None
    try:
        extension = task_meta['extension']

        node_id = task_meta.get('node_id')
        node_path = task_meta.get('node_path')
        if node_id:
            node = get_node_by_id(state, node_id)
        else:
            node = get_node_by_path(state, node_path)
        if not node:
            node = json.loads(task_meta['node_json'])

        node_id_string = abv_node(node_id, node_path)
        if node_id_string is None:
            node_id_string = node.get('id', 'unknown node')
    except (IndexError, TypeError, KeyError):
        raise TaskPrerequisitesError()

    node_data = node.copy()

    # Validate against JSON-schema
    context = extension['context_json']
    extension_type = extension['validates_type']
    schema = extension['validation_schema']

    node_data['@context'] = OPENBADGES_CONTEXT_V2_URI
    compact_data = jsonld.compact(
        node_data, {'@context': [OPENBADGES_CONTEXT_V2_URI, context]},
        options=options.get('jsonld_options', jsonld_use_cache))

    try:
        jsonschema.validate(compact_data, schema)
    except jsonschema.ValidationError as e:
        return task_result(
            False, "Extension {} did not validate on node {}: {}".format(
                extension_type, node_id_string, e.message
            )
        )

    return task_result(True, "Extension {} validated on node {}".format(
        extension_type, node_id_string
    ))


def validate_extension_node(state, task_meta, **options):
    try:
        node_id = task_meta.get('node_id')
        node_path = task_meta.get('node_path')
        context_urls = task_meta.get('context_urls')
        node_types = list_of(task_meta.get('types_to_test', []))
        if node_id:
            node = get_node_by_id(state, node_id)
        else:
            node = get_node_by_path(state, node_path)

        node_json = task_meta.get('node_json')  # Ok to be None
    except (KeyError, ValueError, IndexError, TypeError):
        raise TaskPrerequisitesError()

    if not context_urls:
        return task_result(False, "Could not determine extension type to test: no contexts defined")

    if not node_types:
        node_types = [t for t in node['type'] if t != 'Extension']

    jsonld_options = options.get('jsonld_options', jsonld_use_cache)
    loader = jsonld_options['documentLoader']

    extensions_to_test = []
    for context_url in context_urls:
        if context_url == OPENBADGES_CONTEXT_V2_URI:
            continue

        response = loader.session.get(context_url, headers={'Accept': 'application/ld+json, application/json'})
        try:
            context_json = response.json()
        except TypeError:
            continue
        context_compact = jsonld.compact(context_json, OPENBADGES_CONTEXT_V2_URI, options=jsonld_options)

        validation = list_of(context_compact.get('validation'))
        for val_entry in validation:
            if val_entry.get('validatesType') in node_types:
                try:
                    schema_url = val_entry['validationSchema']
                    schema_json = loader.session.get(
                        schema_url, headers={'Accept': 'application/ld+json, application/json'}).json()
                except TypeError:
                    return task_result(False, 'Could not load JSON-schema from URL {}'.format(abv(schema_url)))

                extensions_to_test.append({
                    'context_url': context_url,
                    'context_json': context_json,
                    'validates_type': val_entry['validatesType'],
                    'validation_schema': schema_json
                })

    if not extensions_to_test:
        return task_result(False, "Could not determine extension type to test")
    elif len(extensions_to_test) > 1:
        # If there is more than one extension, return each validation as a separate task
        actions = [
            add_task(VALIDATE_EXTENSION_SINGLE, node_id=node_id, node_path=node_path,
                     node_json=node_json, extension=t)
            for t in extensions_to_test
        ]
        return task_result(
            True, "Multiple extension types {} discovered in node {}".format(
                abv([e['validates_type'] for e in extensions_to_test]), abv_node(node_id, node_path)
            ), actions)
    else:
        return validate_single_extension(
            state, add_task(
                VALIDATE_EXTENSION_SINGLE,
                node_id=node_id, node_path=node_path, node_json=node_json,
                extension=extensions_to_test[0], **options))
