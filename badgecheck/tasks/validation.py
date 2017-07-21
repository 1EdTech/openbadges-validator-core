import aniso8601
from datetime import datetime
from pyld import jsonld
from pytz import utc
import re
import rfc3986
import six

from ..actions.graph import patch_node
from ..actions.tasks import add_task, report_message
from ..exceptions import TaskPrerequisitesError, ValidationError
from ..state import get_node_by_id, get_node_by_path
from ..openbadges_context import OPENBADGES_CONTEXT_V2_DICT
from ..utils import list_of, MESSAGE_LEVEL_WARNING

from .task_types import (ASSERTION_TIMESTAMP_CHECKS, ASSERTION_VERIFICATION_CHECK,
                         ASSERTION_VERIFICATION_DEPENDENCIES, CLASS_VALIDATION_TASKS,
                         CRITERIA_PROPERTY_DEPENDENCIES, FETCH_HTTP_NODE, FLATTEN_EMBEDDED_RESOURCE,
                         HOSTED_ID_IN_VERIFICATION_SCOPE, IDENTITY_OBJECT_PROPERTY_DEPENDENCIES,
                         IMAGE_VALIDATION, ISSUER_PROPERTY_DEPENDENCIES, VALIDATE_EXPECTED_NODE_CLASS,
                         VALIDATE_RDF_TYPE_PROPERTY, VALIDATE_PROPERTY, VALIDATE_REVOCATIONLIST_ENTRIES,
                         VERIFY_RECIPIENT_IDENTIFIER)
from .utils import (abbreviate_value as abv,
                    abbreviate_node_id as abv_node,
                    is_empty_list, is_null_list, is_iri, is_url, task_result,)


class OBClasses(object):
    AlignmentObject = 'AlignmentObject'
    Assertion = 'Assertion'
    BadgeClass = 'BadgeClass'
    Criteria = 'Criteria'
    CryptographicKey = 'CryptographicKey'
    Evidence = 'Evidence'
    ExpectedRecipientProfile = 'ExpectedRecipientProfile'
    Extension = 'Extension'
    IdentityObject = 'IdentityObject'
    Image = 'Image'
    Issuer = 'Issuer'
    Profile = 'Profile'
    RevocationList = 'RevocationList'
    VerificationObject = 'VerificationObject'

    VerificationObjectAssertion = 'VerificationObjectAssertion'
    VerificationObjectIssuer = 'VerificationObjectIssuer'

    ALL_CLASSES = (AlignmentObject, Assertion, BadgeClass, Criteria, CryptographicKey,
                   ExpectedRecipientProfile, Extension, Evidence, IdentityObject, Image, Issuer,
                   Profile, RevocationList, VerificationObject, VerificationObjectAssertion,
                   VerificationObjectIssuer)

    @classmethod
    def default_for(cls, class_name):
        defaults = {
            cls.Issuer: cls.Profile
        }

        if class_name not in cls.ALL_CLASSES:
            raise TypeError("Unknown class name {}".format(class_name))
        try:
            return defaults[class_name]
        except KeyError:
            return class_name


class ValueTypes(object):
    BOOLEAN = 'BOOLEAN'
    DATA_URI = 'DATA_URI'
    DATA_URI_OR_URL = 'DATA_URI_OR_URL'
    DATETIME = 'DATETIME'
    EMAIL = 'EMAIL'
    ID = 'ID'
    IDENTITY_HASH = 'IDENTITY_HASH'
    IRI = 'IRI'
    MARKDOWN_TEXT = 'MARKDOWN_TEXT'
    RDF_TYPE = 'RDF_TYPE'
    TELEPHONE = 'TELEPHONE'
    TEXT = 'TEXT'
    URL = 'URL'

    PRIMITIVES = (BOOLEAN, DATA_URI_OR_URL, DATETIME, ID, IDENTITY_HASH, IRI, MARKDOWN_TEXT, TELEPHONE, TEXT, URL)


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
            ValueTypes.DATA_URI: self._validate_data_uri,
            ValueTypes.DATA_URI_OR_URL: self._validate_data_uri_or_url,
            ValueTypes.DATETIME: self._validate_datetime,
            ValueTypes.EMAIL: self._validate_email,
            ValueTypes.IDENTITY_HASH: self._validate_identity_hash,
            ValueTypes.IRI: self._validate_iri,
            ValueTypes.MARKDOWN_TEXT: self._validate_markdown_text,
            ValueTypes.RDF_TYPE: self._validate_rdf_type,
            ValueTypes.TELEPHONE: self._validate_tel,
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
    def _validate_data_uri(value):
        data_uri_regex=r'(?P<scheme>^data):(?P<mimetypes>[^,]{0,}?)?(?P<encoding>base64)?,(?P<data>.*$)'
        ret = False
        try:
            if ((value and isinstance(value, six.string_types))
                and rfc3986.is_valid_uri(value, require_scheme=True)
                and re.match(data_uri_regex, value, re.IGNORECASE)
                and re.match(data_uri_regex, value, re.IGNORECASE).group('scheme').lower() == 'data'):
                ret = True
        except ValueError as e:
            pass
        return ret

    @classmethod
    def _validate_data_uri_or_url(cls, value):
        return bool(cls._validate_url(value) or cls._validate_data_uri(value))

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
        return bool(re.match(r'(^[^@\s]+@[^@\s]+$)', value))

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
        return is_iri(value)

    @classmethod
    def _validate_markdown_text(cls, value):
        # All markdown is "valid" if it is a string.
        return cls._validate_text

    @classmethod
    def _validate_rdf_type(cls, value):
        try:
            if not(isinstance(value, six.string_types)):
                raise ValidationError(
                    'RDF_TYPE entry {} must be a string value'.format(abv(value)))

            expanded = jsonld.expand({"@context": OPENBADGES_CONTEXT_V2_DICT, 'type': value})
            expanded_value = expanded[0]['@type'][0]
            if not cls._validate_iri(expanded_value):
                raise ValidationError(
                    'RDF_TYPE entry {} must be a valid IRI in the document context'.format(
                        abv(value))
                )
        except (ValidationError, jsonld.JsonLdError,):
            return False

        return True

    @staticmethod
    def _validate_tel(value):
        """ Validates whether item passes E.164 validation (allows extensions)"""
        return bool(re.match(r'^\+?[1-9]\d{1,14}(;ext=\d+)?$', value))

    @staticmethod
    def _validate_text(value):
        return isinstance(value, six.string_types)

    @staticmethod
    def _validate_url(value):
        return is_url(value)


def validate_property(state, task_meta, **options):
    """
    Validates presence and data type of a single property that is
    expected to be one of the Open Badges Primitive data types or an ID.
    """
    node_id = task_meta.get('node_id')
    node_path = task_meta.get('node_path')
    if node_id:
        node = get_node_by_id(state, node_id)
    elif node_path:
        node = get_node_by_path(state, node_path)
    node_class = task_meta.get('node_class', 'unknown type node')

    prop_name = task_meta.get('prop_name')
    prop_type = task_meta.get('prop_type')
    required = bool(task_meta.get('required'))
    allow_many = task_meta.get('many')
    actions = []

    try:
        prop_value = node[prop_name]
    except KeyError:
        if not required:
            return task_result(
                True, "Optional property {} not present in {} {}".format(
                    prop_name, node_class, abv_node(node_id, node_path))
            )
        return task_result(
            False, "Required property {} not present in {} {}".format(
                prop_name, node_class, abv_node(node_id, node_path))
            )

    if not isinstance(prop_value, (list, tuple,)):
        values_to_test = [prop_value]
    else:
        values_to_test = prop_value

    if required and (is_empty_list(values_to_test) or is_null_list(values_to_test)):
        return task_result(
            False, "Required property {} value {} is not acceptable in {} {}".format(
                prop_name, abv(prop_value), node_class, abv_node(node_id, node_path))
        )
    if not required and (is_empty_list(values_to_test) or is_null_list(values_to_test)):
        return task_result(True, "Optional property {} is null in {} {}".format(
            prop_name, node_class, abv_node(node_id, node_path)
        ))

    if not allow_many and len(values_to_test) > 1:
        return task_result(
            False, "Property {} in {} {} has more than the single allowed value.".format(
                prop_name, node_class, abv_node(node_id, node_path)
            ))

    try:
        if prop_type != ValueTypes.ID:
            for val in values_to_test:
                value_check_function = PrimitiveValueValidator(prop_type)
                if not value_check_function(val):
                    raise ValidationError("{} property {} value {} not valid in {} {}".format(
                        prop_type, prop_name, abv(val), node_class, abv_node(node_id, node_path)))
        else:
            for i in range(len(values_to_test)):
                val = values_to_test[i]
                if isinstance(val, dict):
                    if isinstance(prop_value, (list, tuple,)):
                        value_to_test_path = [node_id, prop_name, i]
                    else:
                        value_to_test_path = [node_id, prop_name]
                    actions.append(
                        add_task(VALIDATE_EXPECTED_NODE_CLASS, node_path=value_to_test_path,
                                 expected_class=task_meta.get('expected_class')))
                    continue
                elif task_meta.get('allow_data_uri', False) and not PrimitiveValueValidator(ValueTypes.DATA_URI_OR_URL)(val):
                    raise ValidationError("ID-type property {} had value `{}` that isn't URI or DATA URI in {}.".format(
                        prop_name, abv(val), abv_node(node_id, node_path))
                    )
                elif not PrimitiveValueValidator(ValueTypes.IRI)(val):
                    raise ValidationError(
                        "ID-type property {} had value `{}` not embedded node or in IRI format in {}.".format(
                            prop_name, abv(val), abv_node(node_id, node_path))
                    )
                try:
                    target = get_node_by_id(state, val)
                except IndexError:
                    if not task_meta.get('fetch', False):
                        if task_meta.get('allow_remote_url') and PrimitiveValueValidator(ValueTypes.URL)(val):
                            continue
                        raise ValidationError(
                            'Node {} has {} property value `{}` that appears not to be in URI format'.format(
                                abv_node(node_id, node_path), prop_name, abv(val)
                            ) + ' or did not correspond to a known local node.')
                    else:
                        actions.append(
                            add_task(FETCH_HTTP_NODE, url=val,
                                     expected_class=task_meta.get('expected_class')))
                else:
                    actions.append(
                        add_task(VALIDATE_EXPECTED_NODE_CLASS, node_id=val,
                                 expected_class=task_meta.get('expected_class')))

    except ValidationError as e:
        return task_result(False, e.message)
    return task_result(
        True, "{} property {} is valid in {} {}".format(
            prop_type, prop_name, node_class, abv_node(node_id, node_path)
        ), actions
    )


def validate_rdf_type_property(state, task_meta, **options):
    prop_result = validate_property(state, task_meta)
    if not prop_result[0]:
        return prop_result

    node_id = task_meta.get('node_id')
    node_path = task_meta.get('node_path')
    if node_id:
        node = get_node_by_id(state, node_id)
    elif node_path:
        node = get_node_by_path(state, node_path)
    prop_value = node.get('type')
    required = bool(task_meta.get('required'))
    default = task_meta.get('default')
    must_contain_one = task_meta.get('must_contain_one')
    allow_many = task_meta.get('many', False)
    actions = []

    # Set node type to default value
    if not prop_value and default:
        actions.append(patch_node(node_id, {'type': default}))
        return task_result(True, prop_result[1], actions)

    if not isinstance(prop_value, (list, tuple,)):
        values_to_test = [prop_value]
    else:
        values_to_test = prop_value

    # Reject if value not in allowed set of values.
    if must_contain_one and not any(val in must_contain_one for val in values_to_test):
        return task_result(False, 'Node {} of type {} does not have type among allowed values ({})'.format(
            abv_node(node_id, node_path), abv(prop_value), abv(must_contain_one)))

    return prop_result


class ClassValidators(OBClasses):
    def __init__(self, class_name):
        self.class_name = class_name

        if class_name == OBClasses.Assertion:
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True,
                    'many': True, 'must_contain_one': ['Assertion']},
                {'prop_name': 'recipient', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.IdentityObject, 'required': True},
                {'prop_name': 'badge', 'prop_type': ValueTypes.ID, 'prerequisites': 'ASN_FLATTEN_BC',
                    'expected_class': OBClasses.BadgeClass, 'fetch': True, 'required': True},
                {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.VerificationObjectAssertion, 'required': True},
                {'prop_name': 'issuedOn', 'prop_type': ValueTypes.DATETIME, 'required': True},
                {'prop_name': 'expires', 'prop_type': ValueTypes.DATETIME, 'required': False},
                {'prop_name': 'image', 'prop_type': ValueTypes.ID, 'required': False, 'allow_remote_url': True,
                 'expected_class': OBClasses.Image, 'fetch': False, 'allow_data_uri': True},
                {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
                {'prop_name': 'evidence', 'prop_type': ValueTypes.ID, 'allow_remote_url': True,
                    'expected_class': OBClasses.Evidence, 'many': True, 'fetch': False, 'required': False},
                {'task_type': ASSERTION_VERIFICATION_DEPENDENCIES, 'prerequisites': ISSUER_PROPERTY_DEPENDENCIES},
                {'task_type': ASSERTION_TIMESTAMP_CHECKS},
                {'task_type': IMAGE_VALIDATION, 'prop_name': 'image', 'node_class': OBClasses.Assertion,
                    'required': False, 'many': False},
                {'task_type': FLATTEN_EMBEDDED_RESOURCE, 'prop_name': 'badge', 'node_class': OBClasses.Assertion,
                    'task_key': 'ASN_FLATTEN_BC'}
            )
        elif class_name == OBClasses.BadgeClass:
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True,
                    'many': True, 'must_contain_one': ['BadgeClass']},
                {'prop_name': 'issuer', 'prop_type': ValueTypes.ID, 'prerequisites': 'BC_FLATTEN_ISS',
                    'expected_class': OBClasses.Profile, 'fetch': True, 'required': True},
                {'prop_name': 'name', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'image', 'prop_type': ValueTypes.ID, 'required': False, 'allow_remote_url': True,
                 'expected_class': OBClasses.Image, 'fetch': False, 'allow_data_uri': True},
                {'prop_name': 'criteria', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.Criteria, 'fetch': False,
                    'required': True, 'allow_remote_url': True},
                {'prop_name': 'alignment', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.AlignmentObject, 'many': True, 'fetch': False, 'required': False},
                {'prop_name': 'tags', 'prop_type': ValueTypes.TEXT, 'many': True, 'required': False},
                {'task_type': IMAGE_VALIDATION, 'prop_name': 'image', 'node_class': OBClasses.BadgeClass,
                    'required': True, 'many': False},
                {'task_type': FLATTEN_EMBEDDED_RESOURCE, 'prop_name': 'issuer', 'node_class': OBClasses.BadgeClass,
                    'task_key': 'BC_FLATTEN_ISS'}
            )
        elif class_name == OBClasses.CryptographicKey:
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': False, 'many': True,
                 'default': 'CryptographicKey'},
                {'prop_name': 'owner', 'prop_type': ValueTypes.IRI, 'required': False, 'fetch': True},
                {'prop_name': 'publicKeyPem', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'task_type': ASSERTION_VERIFICATION_CHECK, 'triggers_completion': 'SIGNING_KEY_FETCHED'}
            )
        elif class_name == OBClasses.Profile or class_name == OBClasses.Issuer:
            # To start, required values will assume the Profile class is used as BadgeClass.issuer
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': True},
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True,
                    'many': True, 'must_contain_one': ['Issuer', 'Profile']},
                {'prop_name': 'name', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'image', 'prop_type': ValueTypes.ID, 'required': False, 'allow_remote_url': True,
                 'expected_class': OBClasses.Image, 'fetch': False, 'allow_data_uri': True},
                {'prop_name': 'url', 'prop_type': ValueTypes.URL, 'required': True},
                {'prop_name': 'email', 'prop_type': ValueTypes.EMAIL, 'required': True},
                {'prop_name': 'telephone', 'prop_type': ValueTypes.TELEPHONE, 'required': False},
                {'prop_name': 'publicKey', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.CryptographicKey, 'fetch': True, 'required': False},
                {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
                 'expected_class': OBClasses.VerificationObjectIssuer, 'fetch': False, 'required': False},
                {'task_type': ISSUER_PROPERTY_DEPENDENCIES, 'messageLevel': MESSAGE_LEVEL_WARNING}
            )
        elif class_name == OBClasses.ExpectedRecipientProfile:
            # For ephemeral profiles representing recipients, there are few required properties.
            self.validators = (
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': False, 'many': True,
                 'must_contain_one': ['Issuer', 'Profile'], 'default': OBClasses.Profile},
                {'prop_name': 'name', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'image', 'prop_type': ValueTypes.ID, 'required': False,
                 'expected_class': OBClasses.Image, 'fetch': False, 'allow_data_uri': True},
                {'prop_name': 'url', 'prop_type': ValueTypes.URL, 'required': False, 'many': True},
                {'prop_name': 'email', 'prop_type': ValueTypes.EMAIL, 'required': False, 'many': True},
                {'prop_name': 'telephone', 'prop_type': ValueTypes.TELEPHONE, 'required': False, 'many': True},
                {'prop_name': 'publicKey', 'prop_type': ValueTypes.ID, 'many': True,
                   'expected_class': OBClasses.CryptographicKey, 'fetch': False, 'required': False},
                {'prop_name': 'verification', 'prop_type': ValueTypes.ID,
                 'expected_class': OBClasses.VerificationObjectIssuer, 'fetch': False, 'required': False},
                {'task_type': VERIFY_RECIPIENT_IDENTIFIER, 'prerequisites': ASSERTION_VERIFICATION_DEPENDENCIES}
            )
        elif class_name == OBClasses.AlignmentObject:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE,
                    'many': True, 'required': False, 'default': OBClasses.AlignmentObject},
                {'prop_name': 'targetName', 'prop_type': ValueTypes.TEXT, 'required': True},
                {'prop_name': 'targetUrl', 'prop_type': ValueTypes.URL, 'required': True},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'targetFramework', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'targetCode', 'prop_type': ValueTypes.TEXT, 'required': False},
            )
        elif class_name == OBClasses.Criteria:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE,
                    'many': True, 'required': False, 'default': OBClasses.Criteria},
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
                {'task_type': CRITERIA_PROPERTY_DEPENDENCIES}
            )
        elif class_name == OBClasses.IdentityObject:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True, 'many': False,
                    'must_contain_one': ['id', 'email', 'url', 'telephone']},
                {'prop_name': 'identity', 'prop_type': ValueTypes.IDENTITY_HASH, 'required': True},
                {'prop_name': 'hashed', 'prop_type': ValueTypes.BOOLEAN, 'required': True},
                {'prop_name': 'salt', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'task_type': IDENTITY_OBJECT_PROPERTY_DEPENDENCIES}
            )
        elif class_name == OBClasses.Evidence:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'many': True,
                    'required': False, 'default': 'Evidence'},
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'narrative', 'prop_type': ValueTypes.MARKDOWN_TEXT, 'required': False},
                {'prop_name': 'name', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'description', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'genre', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'audience', 'prop_type': ValueTypes.TEXT, 'required': False},
            )
        elif class_name == OBClasses.Image:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'many': True,
                    'required': False, 'default': 'schema:ImageObject'},
                {'prop_name': 'id', 'prop_type': ValueTypes.DATA_URI_OR_URL, 'required': True},
                {'prop_name': 'caption', 'prop_type': ValueTypes.TEXT, 'required': False},
                {'prop_name': 'author', 'prop_type': ValueTypes.IRI, 'required': False},
                {'task_type': IMAGE_VALIDATION, 'prop_name': 'id'}
            )
        elif class_name == OBClasses.VerificationObjectAssertion:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True, 'many': False,
                    'must_contain_one': ['HostedBadge', 'SignedBadge']},
                {'prop_name': 'creator', 'prop_type': ValueTypes.ID,
                    'expected_class': OBClasses.CryptographicKey, 'fetch': True, 'required': False,
                    'prerequisites': ASSERTION_VERIFICATION_DEPENDENCIES},
            )
        elif class_name == OBClasses.VerificationObjectIssuer:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': False, 'many': True,
                    'default': 'VerificationObject'},
                {'prop_name': 'verificationProperty', 'prop_type': ValueTypes.IRI, 'required': False},
                {'prop_name': 'startsWith', 'prop_type': ValueTypes.URL, 'required': False},
                {'prop_name': 'allowedOrigins', 'prop_type': ValueTypes.TEXT, 'required': False,
                 'many': True}
            )
        elif class_name == OBClasses.RevocationList:
            self.validators = (
                {'prop_name': 'type', 'prop_type': ValueTypes.RDF_TYPE, 'required': True, 'many': True,
                 'must_contain_one': OBClasses.RevocationList},
                {'prop_name': 'id', 'prop_type': ValueTypes.IRI, 'required': False},
                {'task_type': VALIDATE_REVOCATIONLIST_ENTRIES}
            )
        else:
            raise NotImplementedError("Chosen OBClass not implemented yet.")


def _get_validation_actions(node_class, node_id=None, node_path=None):
    validators = ClassValidators(node_class).validators
    actions = []
    for validator in validators:
        if validator.get('prop_type') == ValueTypes.RDF_TYPE:
            action = add_task(VALIDATE_RDF_TYPE_PROPERTY, **validator)
        if validator.get('prop_type') in ValueTypes.PRIMITIVES:
            action = add_task(VALIDATE_PROPERTY, **validator)
        elif validator.get('task_type') in CLASS_VALIDATION_TASKS:
            action = add_task(validator['task_type'], **validator)
        else:
            continue

        if node_id:
            action['node_id'] = node_id
        else:
            action['node_path'] = node_path

        actions.append(action)
    return actions


def detect_and_validate_node_class(state, task_meta, **options):
    node_id = task_meta.get('node_id')
    node_path = task_meta.get('node_path')

    if node_id:
        node = get_node_by_id(state, node_id)
    else:
        node = get_node_by_path(state, node_path)

    declared_node_type = node.get('type')
    node_class = None

    for ob_class in OBClasses.ALL_CLASSES:
        if declared_node_type == ob_class:
            node_class = OBClasses.default_for(ob_class)
            break

    actions = _get_validation_actions(node_class, node_id, node_path)

    return task_result(
        True, "Declared type on node {} is {}".format(abv_node(node_id, node_path), declared_node_type),
        actions
    )


def validate_expected_node_class(state, task_meta, **options):
    node_id = task_meta.get('node_id')
    node_path = task_meta.get('node_path')

    node_class = OBClasses.default_for(task_meta['expected_class'])
    actions = _get_validation_actions(node_class, node_id, node_path)

    return task_result(
        True, "Queued property validations for class {} instance {}".format(
            node_class, abv_node(node_id, node_path)),
        actions
    )


"""
Class Validation Tasks
"""
def identity_object_property_dependencies(state, task_meta, **options):
    node_id = task_meta.get('node_id')
    node_path = task_meta.get('node_path')
    if node_id:
        node = get_node_by_id(state, node_id)
    else:
        node = get_node_by_path(state, node_path)

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


def criteria_property_dependencies(state, task_meta, **options):
    try:
        node_id = task_meta.get('node_id')
        node_path = task_meta.get('node_path')
        if node_id:
            node = get_node_by_id(state, node_id)
        else:
            node = get_node_by_path(state, node_path)
            node_id = node.get('id', '')
    except (IndexError, KeyError, TypeError):
        raise TaskPrerequisitesError()

    is_blank_id_node = bool(re.match(r'_:b\d+$', node_id))
    if is_blank_id_node and not node.get('narrative'):
        return task_result(False,
            "Criteria node {} has no narrative. Either external id or narrative is required.".format(
                abv_node(node_id, node_path))
        )
    elif is_blank_id_node:
        return task_result(
            True, "Criteria node {} is a narrative-based piece of evidence.".format(
                abv_node(node_id, node_path)
            )
        )
    elif not is_blank_id_node and node.get('narrative'):
        return task_result(
            True, "Criteria node {} has a URL and narrative.".format(abv_node(node_id, node_path))
        )
    # Case to handle no narrative but other props preventing compaction down to simple id string:
    # {'id': 'http://example.com/1', 'name': 'Criteria Name'}
    return task_result(True, "Criteria node {} has a URL.".format(abv_node(node_id, node_path)))


def assertion_verification_dependencies(state, task_meta, **options):
    """
    Performs and/or queues some security checks for hosted assertions.
    """
    try:
        assertion_id = task_meta.get('node_id')
        node_path = task_meta.get('node_path')
        if assertion_id:
            node = get_node_by_id(state, assertion_id)
        elif node_path:
            node = get_node_by_path(state, node_path)
        node_id = node['verification']
        if isinstance(node_id, six.string_types):
            node = get_node_by_id(state, node_id)
        else:
            node = node_id
    except (IndexError, KeyError,):
        raise TaskPrerequisitesError()

    actions = []

    if node.get('type') == 'HostedBadge':
        actions.append(add_task(HOSTED_ID_IN_VERIFICATION_SCOPE, node_id=assertion_id))

    return task_result(
        True, '{} Assertion {} verification dependencies noted.'.format(
            node.get('type'), assertion_id),
        actions
    )


def assertion_timestamp_checks(state, task_meta, **options):
    try:
        node_id = task_meta['node_id']
        assertion = get_node_by_id(state, node_id)
        issued_on = aniso8601.parse_datetime(assertion['issuedOn'])
    except (IndexError, KeyError, ValueError,):
        raise TaskPrerequisitesError(task_meta)

    now = datetime.now(utc)
    if issued_on > now:
        return task_result(
            False, "Assertion {} has issue date {} in the future.".format(node_id, issued_on))

    if assertion.get('expires'):
        expires = aniso8601.parse_datetime(assertion['expires'])
        if expires < issued_on:
            return task_result(
                False, "Assertion {} expiration is prior to issue date.".format(node_id))

        if expires < now :
            return task_result(
                False, "Assertion {} expired on {}".format(node_id, assertion['expires'])
            )

    return task_result(
        True, "Assertion {} was issued and has not expired.".format(node_id))


def issuer_property_dependencies(state, task_meta, **options):
    try:
        node_id = task_meta['node_id']
        issuer_node = get_node_by_id(state, node_id)
    except (IndexError, KeyError,):
        raise TaskPrerequisitesError()

    if not bool(re.match('^http(s)?://', node_id)):
        return task_result(
            False, "Issuer Profile {} not hosted with HTTP-based identifier.".format(node_id) +
                  "Many platforms can only handle HTTP(s)-hosted issuers.")
    return task_result(True, "Issuer profile id meets expectations.")


def placeholder_task(state, task_meta, **options):
    return task_result(True, "Placeholder (prerequisite) task complete.")


def validate_revocationlist_entries(state, task_meta, **options):
    try:
        node_id = task_meta['node_id']
        revocation_list = get_node_by_id(state, node_id)
    except (IndexError, KeyError,):
        raise TaskPrerequisitesError()

    try:
        revoked_assertions = list_of(revocation_list['revokedAssertions'])
    except KeyError:
        return task_result(False, "RevocationList {} missing required property revokedAssertions.")

    for entry in revoked_assertions:
        if isinstance(entry, dict):
            try:
                if not PrimitiveValueValidator(ValueTypes.IRI)(entry['id']):
                    return task_result(False, "RevocationList {} has entry with id {} not in IRI format".format(
                        node_id, entry['id']
                    ))
            except KeyError:
                if not isinstance(entry.get('uid'), six.string_types):
                    return task_result(False, "RevocationList {} has entry with uid '{}' not in text format.".format(
                        node_id, abv(entry.get('uid'))
                    ))
        elif isinstance(entry, six.string_types):
            if not PrimitiveValueValidator(ValueTypes.IRI)(entry):
                return task_result(False, "RevocationList {} has entry with id {} not in IRI format".format(
                    node_id, entry
                ))
        else:
            return task_result(False, "RevocationList {} has entry with id {} not in IRI format".format(
                    node_id, entry
                ))

    # Node flattening system will insert all entries into graph.
    return task_result(True)
