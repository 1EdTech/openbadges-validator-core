import six
import rfc3986

from ..state import get_node_by_id

from .utils import task_result


class ValueTypes(object):
    BOOLEAN = 'BOOLEAN'
    DATETIME = 'DATETIME'
    ID = 'ID'
    IDENTITY_HASH = 'IDENTITY_HASH'
    IRI = 'IRI'
    MARKDOWN_TEXT = 'MARKDOWN_TEXT'
    TEXT = 'TEXT'
    URL = 'URL'


class PrimitiveValueValidator(object):
    """
    A callable validator for primitive Open Badges value types. 
    
    Example usage: 
    PrimitiveValueValidator(ValueTypes.TEXT)("test value")
    > True
    """
    def __init__(self, value_type):
        value_check_functions = {
            ValueTypes.BOOLEAN: self._validate_boolean,
            ValueTypes.DATETIME: self._validate_datetime,
            ValueTypes.IDENTITY_HASH: self._validate_identity_hash,
            ValueTypes.IRI: self._validate_iri,
            ValueTypes.MARKDOWN_TEXT: self._validate_markdown_text,
            ValueTypes.TEXT: self._validate_text,
            ValueTypes.URL: self._validate_url
        }
        self.value_type = value_type
        self.is_valid = value_check_functions[value_type]

    def __call__(self, value):
        return self.is_valid(value)

    @staticmethod
    def _validate_boolean(value):
        return isinstance(value, bool)

    @staticmethod
    def _validate_datetime(value):
        raise NotImplementedError("TODO: Add validator")

    @staticmethod
    def _validate_identity_hash(value):
        raise NotImplementedError("TODO: Add validator")

    @staticmethod
    def _validate_iri(value):
        raise NotImplementedError("TODO: Add validator")

    @staticmethod
    def _validate_markdown_text(value):
        raise NotImplementedError("TODO: Add validator")

    @staticmethod
    def _validate_text(value):
        return isinstance(value, six.string_types)

    @staticmethod
    def _validate_url(value):
        ret = False
        try:
            if ((value and isinstance(value, six.string_types))
                and rfc3986.is_valid_uri(value, require_scheme=True)
                and rfc3986.uri_reference(value).scheme.lower() in ['http', 'https']):
                ret = True
        except ValueError as e:
            pass
        return ret

def validate_primitive_property(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    node_class = task_meta.get('node_class', 'unknown type node')

    prop_name = task_meta.get('prop_name')
    prop_type = task_meta.get('prop_type')
    prop_value = node.get(prop_name)
    required = bool(task_meta.get('prop_required'))

    if not prop_value and required:
        return task_result(
            False, "Required property {} not present in {} {}".format(
                prop_name, node_class, node_id)
        )

    if not prop_value and not required:
        return task_result(
            True, "Optional property {} not present in {} {}".format(
                prop_name, node_class, node_id)
        )

    value_check_function = PrimitiveValueValidator(prop_type)
    if value_check_function(prop_value):
        return task_result(
            True, "{} property {} valid in {} {}".format(
                prop_type, prop_name, node_class, node_id
            )
        )

    return task_result(
        False, "{} property {} not valid in {} {}".format(
            prop_type, prop_name, node_class, node_id
        )
    )
