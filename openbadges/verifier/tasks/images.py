import base64
import re
import requests
import requests_cache
import six

from ..actions.input import store_original_resource
from ..actions.tasks import add_task
from ..exceptions import TaskPrerequisitesError
from ..state import get_node_by_id, get_node_by_path

from .task_types import IMAGE_VALIDATION
from .utils import (task_result, abbreviate_value,
                    abbreviate_node_id as abv_node,
                    is_data_uri)

def validate_image(state, task_meta, **options):
    try:
        node_id = task_meta.get('node_id')
        node_path = task_meta.get('node_path')
        prop_name = task_meta.get('prop_name', 'image')
        node_class = task_meta.get('node_class')
        required = bool(task_meta.get('required', False))
        if node_id:
            node = get_node_by_id(state, node_id)
            node_path = [node_id]
        else:
            node = get_node_by_path(state, node_path)

        if options.get('cache_backend'):
            session = requests_cache.CachedSession(
                backend=options['cache_backend'], expire_after=options.get('cache_expire_after', 300))
        else:
            session = requests.Session()
    except (IndexError, TypeError, KeyError):
        raise TaskPrerequisitesError()

    actions = []

    image_val = node.get(prop_name)

    if image_val is None:
        return task_result(not required, "Could not load and validate image in node {}".format(abv_node(node_id, node_path)))
    if isinstance(image_val, six.string_types):
        url = image_val
    elif isinstance(image_val, dict):
        url = image_val.get('id')
    elif isinstance(image_val, list):
        return task_result(False, "many images not allowed")
    else:
        raise TypeError("Could not interpret image property value {}".format(
            abbreviate_value(image_val)
        ))
    if is_data_uri(url):
        if task_meta.get('allow_data_uri', False) is False:
            return task_result(False, "Image in node {} may not be a data URI.".format(abv_node(node_id, node_path)))
        try:
            mimetypes = re.match(r'(?P<scheme>^data):(?P<mimetypes>[^,]{0,}?)?(?P<encoding>base64)?,(?P<data>.*$)', url).group(
                'mimetypes')
            if 'image/png' not in mimetypes and 'image/svg+xml' not in mimetypes:
                raise ValueError("Disallowed filetype")
        except (AttributeError, ValueError,):
            return task_result(
                False, "Data URI image does not declare any of the allowed PNG or SVG mime types in {}".format(
                    abv_node(node_id, node_path))
            )
    elif url:
        existing_file = state.get('input', {}).get('original_json', {}).get(url)
        if existing_file:
            return task_result(True, "Image resource already stored for url {}".format(abbreviate_value(url)))
        else:
            try:
                result = session.get(
                    url, headers={'Accept': 'application/ld+json, application/json, image/png, image/svg+xml'}
                )
                result.raise_for_status()
                content_type = result.headers['content-type']
                encoded_body = base64.b64encode(result.content)
                data_uri = "data:{};base64,{}".format(content_type, encoded_body)

            except (requests.ConnectionError, requests.HTTPError, KeyError):
                return task_result(False, "Could not fetch image at {}".format(url))
            else:
                actions.append(store_original_resource(url, data_uri))

    return task_result(True, "Validated image for node {}".format(abv_node(node_id, node_path)), actions)
