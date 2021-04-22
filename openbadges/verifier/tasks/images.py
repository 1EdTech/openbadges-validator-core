import base64
import puremagic
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

SVG_MIME_TYPE = 'image/svg+xml'
PNG_MIME_TYPE = 'image/png'

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
                validate_image_mime_type_for_node_class(result.content, node_class)
                content_type = result.headers['content-type']
                encoded_body = base64.b64encode(result.content)
                data_uri = "data:{};base64,{}".format(content_type, encoded_body)

            except (requests.ConnectionError,
                    requests.HTTPError,
                    KeyError):
                return task_result(False, "Could not fetch image at {}".format(url))
            except (ValueError,
                    puremagic.PureError) as e:
                return task_result(False, "{}".format(e))
            else:
                actions.append(store_original_resource(url, data_uri))

    return task_result(True, "Validated image for node {}".format(abv_node(node_id, node_path)), actions)


def validate_image_mime_type_for_node_class(content, node_class):
    allowed_mime_types = [SVG_MIME_TYPE, PNG_MIME_TYPE]
    magic_strings = puremagic.magic_string(content)
    if magic_strings:
        derived_mime_type = None
        derived_ext = None

        for magic_string in magic_strings:
            if getattr(magic_string, 'mime_type', None) in allowed_mime_types:
                derived_mime_type = getattr(magic_string, 'mime_type', None)
                derived_ext = getattr(magic_string, 'extension', None)
                break

        if not derived_mime_type and re.search(b'<svg', content[:1024]) and content.strip()[-6:] == b'</svg>':
            derived_mime_type = SVG_MIME_TYPE
            derived_ext = '.svg'

        if derived_mime_type not in allowed_mime_types:
            magic_string_info = max(magic_strings, key=lambda ms: ms.confidence and ms.extension and ms.mime_type)
            raise ValueError("{} image of type '{} {}' is unsupported".format(
                node_class,
                getattr(magic_string_info, 'mime_type', 'Unknown'),
                getattr(magic_string_info, 'extension', 'Unknown')
            ))

        if not derived_ext or not derived_mime_type:
            raise ValueError("{} image is an unknown file type").format(node_class)
    else:
        raise ValueError("Unable to determine file type for {} image").format(node_class)
