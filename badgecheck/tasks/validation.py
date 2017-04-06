import aniso8601
import re
import rfc3986
import six

from ..actions.tasks import add_task
from ..exceptions import ValidationError
from ..state import get_node_by_id

from .task_types import (CLASS_VALIDATION_TASKS, CRITERIA_PROPERTY_DEPENDENCIES,
                         EVIDENCE_PROPERTY_DEPENDENCIES, FETCH_HTTP_NODE,
                         IDENTITY_OBJECT_PROPERTY_DEPENDENCIES, VALIDATE_EXPECTED_NODE_CLASS,
                         VALIDATE_ID_PROPERTY, VALIDATE_PRIMITIVE_PROPERTY, )

from .utils import abbreviate_value, is_empty_list, task_result


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
        try:
            # aniso at least needs to think it can get a datetime from value
            aniso8601.parse_datetime(value)
        except Exception as e:
            return False
        # we also require tzinfo specification on our datetime strings
        # NOTE -- does not catch minus-sign (non-ascii char) tzinfo delimiter
        return (isinstance(value, six.string_types) and
                (value[-1:]=='Z' or
                 bool(re.match(r'.*[+-](?:\d{4}|\d{2}|\d{2}:\d{2})$', value))))


    @staticmethod
    def _validate_email(value):
        return bool(re.match(r'(^[^@]+@[^@]+$)', value))

    @staticmethod
    def is_hashed_identity_hash(value):
        return bool(re.match(r'md5\$[\da-fA-F]{32}$', value) or re.match(r'sha256\$[\da-fA-F]{64}$', value))

    @classmethod
    def _validate_identity_hash(cls, value):
        # Validates that identity is a string. More specific rules may only be enforced at the class instance level.
        return isinstance(value, six.string_types)

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

    @classmethod
    def _validate_markdown_text(cls, value):
        # TODO Assert no render errors if relevant?
        return cls._validate_text

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
    required = bool(task_meta.get('required'))

    if prop_value is None and required:
        return task_result(
            False, "Required property {} not present in {} {}".format(
                prop_name, node_class, node_id)
        )
    elif task_meta.get('many') and required and is_empty_list(prop_value):
        return task_result(
            False, "Required property {} contains no values in {} {}".format(
                prop_name, node_class, node_id)
        )

    if prop_value is None and not required:
        return task_result(
            True, "Optional property {} not present in {} {}".format(
                prop_name, node_class, node_id)
        )

    if not isinstance(prop_value, (list, tuple,)):
        values_to_test = [prop_value]
    else:
        values_to_test = prop_value

    try:
        for val in values_to_test:
            value_check_function = PrimitiveValueValidator(prop_type)
            if not required and not val:
                continue
            if not value_check_function(val):
                raise ValidationError("{} property {} value {} not valid in {} node {}".format(
                    prop_type, prop_name, abbreviate_value(val), node_class, node_id))

    except ValidationError as e:
        return task_result(False, e.message)
    return task_result(
        True, "{} property {} value {} valid in {} node {}".format(
            prop_type, prop_name, abbreviate_value(prop_value), node_class, node_id
        )
    )


class ClassValidators(OBClasses):
    def __init__(self, class_name):
        self.class_name = class_name

        if class_name == OBClasses.Assertion:
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
                {'prop_name': 'recipient', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.IdentityObject, 'required': True},
                {'prop_name': 'badge', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.BadgeClass, 'fetch': True, 'required': True},
                # TODO: {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
                #   'expected_class': OBClasses.VerificationObject, 'required': True},
                {'prop_name': 'issuedOn', 'prop_type': ValueTypes.DATETIME, 'required': True},
                {'prop_name': 'expires', 'prop_type': ValueTypes.DATETIME, 'required': False},
                {'prop_name': 'image', 'prop_type': ValueTypes.URL, 'required': False},
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
                {'prop_name': 'criteria', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.Criteria, 'fetch': False, 'required': True},
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
        elif class_name == OBClasses.Criteria:
            self.validators = (
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE,
                #   'required': False, 'default': OBClasses.Criteria},
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
                {'task_type': CRITERIA_PROPERTY_DEPENDENCIES}
            )
        elif class_name == OBClasses.IdentityObject:
            self.validators = (
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True},
                {'prop_name': 'identity', 'prop_type': ValueTypes.IDENTITY_HASH, 'required': True},
                {'prop_name': 'hashed', 'prop_type': ValueTypes.BOOLEAN, 'required': True},
                {'prop_name': 'salt', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'task_type': IDENTITY_OBJECT_PROPERTY_DEPENDENCIES}
            )
        elif class_name == OBClasses.Evidence:
            self.validators = (
                # TODO: {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': False},
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
                {'task_type': EVIDENCE_PROPERTY_DEPENDENCIES}
            )
        else:
            raise NotImplementedError("Chosen OBClass not implemented yet.")


def _get_validation_actions(node_id, node_class):
    validators = ClassValidators(node_class).validators
    actions = []
    for validator in validators:
        if validator.get('prop_type') in ValueTypes.PRIMITIVES:
            actions.append(add_task(
                VALIDATE_PRIMITIVE_PROPERTY, node_id=node_id,
                node_class=node_class, **validator
            ))
        elif validator.get('prop_type') == ValueTypes.ID:
            actions.append(add_task(
                VALIDATE_ID_PROPERTY, node_id=node_id,
                node_class=node_class, **validator
            ))
        elif validator.get('task_type') in CLASS_VALIDATION_TASKS:
            actions.append(add_task(
                validator['task_type'], node_id=node_id,
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

    if prop_value is None and required:
        return task_result(
            False, "Required property {} not present in {} {}".format(
                prop_name, node_class, node_id)
        )

    if not isinstance(prop_value, (list, tuple,)):
        values_to_test = [prop_value]
    else:
        values_to_test = prop_value

    try:
        for val in values_to_test:
            if not PrimitiveValueValidator(ValueTypes.IRI)(val):
                raise ValidationError(
                    "ID-type property {} had value `{}` not in IRI format in {}.".format(
                        prop_name, abbreviate_value(val), node_id)
                )

            if not task_meta.get('fetch', False):
                try:
                    target = get_node_by_id(state, val)
                except IndexError:
                    if task_meta.get('allow_remote_url') and PrimitiveValueValidator(ValueTypes.URL)(val):
                        continue
                    raise ValidationError(
                        'Node {} has {} property value `{}` that appears not to be in URI format'.format(
                          node_id, prop_name, abbreviate_value(val)
                        ))
                actions.append(
                    add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=val, expected_class=expected_class))
            else:
                actions.append(add_task(FETCH_HTTP_NODE, url=val, expected_class=expected_class))
    except ValidationError as e:
        return task_result(False, e.message)

    label = 'references are' if len(values_to_test) > 1 else 'reference is'
    return task_result(True, "{} property {} {} valid in {} {}".format(
        ValueTypes.ID, prop_name, label, node_class, node_id), actions)


"""
Class Validation Tasks
"""
def identity_object_property_dependencies(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    node_class = task_meta.get('node_class')
    identity = node.get('identity')
    is_hashed = PrimitiveValueValidator.is_hashed_identity_hash(identity)
    is_email = bool(re.match(r'[^@]+@[^@]+$', identity))

    if node.get('hashed') and not is_hashed:
        return task_result(
            False,
            "Identity {} must match known hash style if hashed is true".format(identity))
    elif is_hashed and not node.get('hashed'):
        return task_result(
            False,
            "Identity {} must not be hashed if hashed is false".format(identity)
        )
    if not node.get('hashed') and 'email' in node.get('type') and not is_email:
        return task_result(False, "Email type identity must match email format.")

    return task_result(True, "IdentityObject passes validation rules.")


def criteria_property_dependencies(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    is_blank_id_node = bool(re.match(r'_:b\d+$', node_id))

    if is_blank_id_node and not node.get('narrative'):
        return task_result(False,
            "Criteria node {} has no narrative. Either external id or narrative is required.".format(node_id)
        )
    elif is_blank_id_node:
        return task_result(
            True, "Criteria node {} is a narrative-based piece of evidence.".format(node_id)
        )
    elif not is_blank_id_node and node.get('narrative'):
        return task_result(
            True, "Criteria node {} has a URL and narrative."
        )
    # Case to handle no narrative but other props preventing compaction down to simple id string:
    # {'id': 'http://example.com/1', 'name': 'Criteria Name'}
    return task_result(True, "Criteria node {} has a URL.")


def evidence_property_dependencies(state, task_meta):
    node_id = task_meta.get('node_id')
    node = get_node_by_id(state, node_id)
    is_blank_id_node = bool(re.match(r'_:b\d+$', node_id))

    if is_blank_id_node and not node.get('narrative'):
        return task_result(False,
            "Evidence node {} has no narrative. Either external id or narrative is required.".format(node_id)
        )
    elif is_blank_id_node:
        return task_result(
            True, "Evidence node {} is a narrative-based piece of evidence.".format(node_id)
        )
    elif not is_blank_id_node and node.get('narrative'):
        return task_result(
            True, "Evidence node {} has a URL and narrative."
        )
    # Case to handle no narrative but other props preventing compaction down to simple id string:
    # {'id': 'http://example.com/1', 'name': 'Evidence Name'}
    return task_result(True, "Evidence node {} has a URL.")