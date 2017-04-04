import six

from ..actions.tasks import add_task
from ..state import get_node_by_id

from .task_types import VALIDATE_PRIMITIVE_PROPERTY
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
        raise NotImplementedError("TODO: Add validator")


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


ASSERTION_VALIDATORS = (
    {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
    # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
    # TODO: {'prop_name': 'recipient', 'prop_type': ValueTypes.ID,
    #   'expected_class': 'IdentityObject', 'required': True},
    # TODO: {'prop_name': 'badge', 'prop_type': ValueTypes.ID,
    #   'expected_class': 'BadgeClass', 'required': True},
    # TODO: {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
    #   'expected_class': 'VerificationObject', 'required': True},
    {'prop_name': 'issuedOn', 'prop_type': ValueTypes.DATETIME, 'required': True},
    {'prop_name': 'expires', 'prop_type': ValueTypes.DATETIME, 'required': False},
    {'prop_name': 'image', 'prop_type': ValueTypes.URL, 'required': False},  # Todo: ValueTypes.DATA_URI_OR_URL
    {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
    # TODO: {'prop_name': 'evidence', 'prop_type': ValueTypes.ID,
    #   'expected_class': 'Evidence', many=True, 'fetch': False, required': True},
)
BADGECLASS_VALIDATORS = ()
ISSUER_PROFILE_VALIDATORS = ()


def detect_and_validate_node_class(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    declared_node_type = node.get('type')

    if declared_node_type == 'Assertion':
        validators = ASSERTION_VALIDATORS
    elif declared_node_type == 'BadgeClass':
        validators = BADGECLASS_VALIDATORS
    elif declared_node_type in ('Issuer', 'Profile',):
        validators = ISSUER_PROFILE_VALIDATORS
    else:
        raise NotImplementedError("Only Assertion, BadgeClass, and Profile supported so far")

    actions = []
    for validator in validators:
        actions.append(add_task(
            VALIDATE_PRIMITIVE_PROPERTY, node_id=task_meta.get('node_id'), **validator
        ))

    return task_result(
        True, "Declared type on node {} is {}".format(node_id, declared_node_type),
        actions
    )
