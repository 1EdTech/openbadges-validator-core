import re
import rfc3986
import six

from ..actions.tasks import add_task
from ..state import get_node_by_id

from .task_types import (FETCH_HTTP_NODE, VALIDATE_EXPECTED_NODE_CLASS, VALIDATE_ID_PROPERTY,
                         VALIDATE_PRIMITIVE_PROPERTY,)

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
    # TODO: RDF_TYPE = 'RDF_TYPE'
    # TODO: EMAIL = 'EMAIL'
    # TODO: TELEPHONE = 'TELEPHONE'

    PRIMITIVES = (BOOLEAN, DATETIME, IDENTITY_HASH, IRI, MARKDOWN_TEXT, TEXT, URL)


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

    @classmethod
    def _validate_iri(cls, value):
        """
        Checks if a string matches an acceptable IRI format and scheme. For now, only accepts a few schemes,
        'http', 'https', blank node identifiers, and 'urn:uuid'
        :param value: six.string_types 
        :return: bool
        """
        # TODO: Accept other IRI schemes in the future for certain classes.
        urn_regex = r'^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(
            cls._validate_url(value) or
            re.match(r'_:b\d+$', value) or
            re.match(urn_regex, value, re.IGNORECASE)
        )

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
    """
    Validates presence and data type of a single property that is
    expected to be one of the Open Badges Primitive data types.
    """
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




class OBClasses(object):
    AlignmentObject = 'AlignmentObject'
    Assertion = 'Assertion'
    BadgeClass = 'BadgeClass'
    Criteria = 'Criteria'
    CryptographicKey = 'CryptographicKey'
    Extension = 'Extension'
    Evidence = 'Evidence'
    IdentityObject = 'IdentityObject'
    Image = 'Image'
    Profile = 'Profile'
    RevocationList = 'RevocationList'
    VerificationObject = 'VerificationObject'

    ALL_CLASSES = (AlignmentObject, Assertion, BadgeClass, Criteria, CryptographicKey,
                   Extension, Evidence, IdentityObject, Image, Profile, RevocationList,
                   VerificationObject)


class ClassValidators(OBClasses):
    def __init__(self, class_name):
        self.class_name = class_name

        if class_name == OBClasses.Assertion:
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
                # TODO: {'prop_name': 'recipient', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.IdentityObject, 'required': True},
                {'prop_name': 'badge', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.BadgeClass, 'fetch': True, 'required': True},
                # TODO: {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.VerificationObject, 'required': True},
                {'prop_name': 'issuedOn', 'prop_type': ValueTypes.DATETIME, 'required': True},
                {'prop_name': 'expires', 'prop_type': ValueTypes.DATETIME, 'required': False},
                {'prop_name': 'image', 'prop_type': ValueTypes.URL, 'required': False},  # TODO: ValueTypes.DATA_URI_OR_URL
                {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
                # TODO: {'prop_name': 'evidence', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.Evidence, 'many': True, 'fetch': False, required': True},
            )
        elif class_name == OBClasses.BadgeClass:
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
                {'prop_name': 'issuer', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.Profile, 'fetch': True, 'required': True},
                {'prop_name': 'name', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'image', 'prop_type': ValueTypes.URL, 'required': True},  # TODO: ValueTypes.DATA_URI_OR_URL
                # TODO: {'prop_name': 'criteria', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.Criteria, 'fetch': False, 'required': True},
                # TODO: {'prop_name': 'alignment', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.AlignmentObject, 'many': True, 'fetch': False, required': False},
                # TODO: {'prop_name': 'tags', 'prop_type': ValueTypes.TEXT, 'many': True, 'required': False},
            )
        elif class_name == OBClasses.Profile:
            # To start, required values will assume the Profile class is used as BadgeClass.issuer
            self.validators = (
                # TODO: "Most platforms to date can only handle HTTP-based IRIs."
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
                {'prop_name': 'name', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'image', 'prop_type': ValueTypes.URL, 'required': False},  # TODO: ValueTypes.DATA_URI_OR_URL
                {'prop_name': 'url', 'prop_type': ValueTypes.URL, 'required': True},
                {'prop_name': 'email', 'prop_type': ValueTypes.TEXT, 'required': True},  # TODO: Add ValueTypes.EMAIL
                {'prop_name': 'telephone', 'prop_type': ValueTypes.TEXT, 'required': False},  # TODO: Add ValueTypes.TELEPHONE
                # TODO: {'prop_name': 'publicKey', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.CryptographicKey, 'fetch': True, 'required': False},
                # TODO: {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.VerificationObject, 'fetch': False, 'required': False},
                # TODO: {'prop_name': 'revocationList', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.Revocationlist, 'fetch': True, 'required': False},  # TODO: Fetch only for relevant assertions?
            )
        elif class_name == OBClasses.IdentityObject:
            self.validators = (
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
                {'prop_name': 'identity', 'prop_type': ValueTypes.IDENTITY_HASH, 'required': True},
                {'prop_name': 'hashed', 'prop_type': ValueTypes.BOOLEAN, 'required': True},
                {'prop_name': 'salt', 'prop_type': ValueTypes.TEXT, 'required': False},
            )
        else:
            raise NotImplementedError("Chosen OBClass not implemented yet.")


def _get_validation_actions(node_id, node_class):
    validators = ClassValidators(node_class).validators
    actions = []
    for validator in validators:
        if validator['prop_type'] in ValueTypes.PRIMITIVES:
            actions.append(add_task(
                VALIDATE_PRIMITIVE_PROPERTY, node_id=node_id,
                node_class=node_class, **validator
            ))
        elif validator['prop_type'] == ValueTypes.ID:
            actions.append(add_task(
                VALIDATE_ID_PROPERTY, node_id=node_id,
                node_class=node_class, **validator
            ))
    return actions


def detect_and_validate_node_class(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    declared_node_type = node.get('type')
    node_class = None

    for ob_class in OBClasses.ALL_CLASSES:
        if declared_node_type == ob_class:
            node_class = ob_class
            break

    actions = _get_validation_actions(task_meta.get('node_id'), node_class)

    return task_result(
        True, "Declared type on node {} is {}".format(node_id, declared_node_type),
        actions
    )


def validate_expected_node_class(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)  # Raises if not exists
    node_class = task_meta.get('expected_class')
    actions = _get_validation_actions(node_id, node_class)

    return task_result(
        True, "Queued property validations for node {} of class {}".format(node_id, node_class),
        actions
    )


def validate_id_property(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    node_class = task_meta.get('node_class')
    expected_class = task_meta.get('expected_class')

    prop_name = task_meta.get('prop_name')
    required = bool(task_meta.get('required'))
    prop_value = node.get(prop_name)
    actions = []

    if not PrimitiveValueValidator(ValueTypes.IRI)(prop_value):
        return task_result(
            False,
            "ID-type property {} was not found in IRI format in {}.".format(prop_name, node_id)
        )

    if not task_meta.get('fetch', False):
        target = get_node_by_id(state, prop_value)
        message = 'Node {} has {} relation stored as node {}'.format(node_id, prop_name, prop_value)
        actions.append(add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=prop_value, expected_class=expected_class))
    else:
        message = 'Node {} has {} relation identified as URL {}'.format(node, prop_name, prop_value)
        actions.append(add_task(FETCH_HTTP_NODE, url=prop_value, expected_class=expected_class))

    return task_result(True, message, actions)

