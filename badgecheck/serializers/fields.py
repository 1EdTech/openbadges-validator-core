import re
from datetime import datetime

from django.core.validators import RegexValidator
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import SkipField, DictField

from badgecheck.validators import URLOrDataURIValidator, LDTypeValidator


class BadgePotentiallyEmptyField(serializers.Field):
    def get_attribute(self, instance):
        value = serializers.Field.get_attribute(self, instance)

        if value == '' or value is None or value == {}:
            if not self.required or not self.allow_blank:
                raise SkipField()
        return value

    def validate_empty_values(self, data):
        """
        If an empty value (empty string, null) exists in an optional
        field, SkipField.
        """
        (is_empty_value, data) = serializers.Field.validate_empty_values(self, data)

        if is_empty_value or data == '':
            if self.required:
                self.fail('required')
            raise SkipField()

        return (False, data)


class BadgeCharField(object):
    def run_validation(self, data):
        # Reject empty strings only if field is required.
        # Otherwise SkipField on encountering an empty string.
        if data == '':
            if not self.allow_blank and not self.required:
                raise SkipField()
            elif not self.allow_blank:
                self.fail('blank')
            return ''
        return super(serializers.CharField, self).run_validation(data)


class BadgeURLField(BadgePotentiallyEmptyField, BadgeCharField, serializers.URLField):
    def to_representation(self, value):
        return value


class BadgeImageURLField(BadgePotentiallyEmptyField, BadgeCharField, serializers.URLField):
    def to_representation(self, value):
        return value


class URLOrDataURIField(serializers.CharField):
    default_error_messages = {
        'invalid': _('Enter a valid URL or Data URI.')
    }

    def __init__(self, **kwargs):
        super(URLOrDataURIField, self).__init__(**kwargs)
        validator = URLOrDataURIValidator(message=self.error_messages['invalid'])
        self.validators.append(validator)


class BadgeImageURLOrDataURIField(BadgePotentiallyEmptyField, BadgeCharField, URLOrDataURIField):
    def to_representation(self, value):
        return value


class BadgeStringField(BadgePotentiallyEmptyField, BadgeCharField, serializers.CharField):

    def __init__(self, **kwargs):
        self.required_value = kwargs.pop('required_value', None)
        super(BadgeStringField, self).__init__(**kwargs)
        if self.required_value:
            self.validators.append(RegexValidator(regex=self.required_value))

    def to_representation(self, value):
        return value


class LDTypeField(BadgeCharField, serializers.CharField):
    def __init__(self, **kwargs):
        required_type = kwargs.pop('required_type', None)
        super(LDTypeField, self).__init__(**kwargs)
        self.validators.append(LDTypeValidator(type_name=required_type))


class BadgeEmailField(BadgePotentiallyEmptyField, BadgeCharField, serializers.EmailField):
    def to_representation(self, value):
        return value


class BadgeDateTimeField(BadgePotentiallyEmptyField, serializers.Field):

    default_error_messages = {
        'not_int_or_str': 'Invalid format. Expected an int or str.',
        'bad_str': 'Invalid format. String is not ISO 8601 or unix timestamp.',
        'bad_int': 'Invalid format. Unix timestamp is out of range.',
    }

    def to_internal_value(self, value):
        if isinstance(value, (str, unicode)):
            try:
                return datetime.utcfromtimestamp(float(value))
            except ValueError:
                pass

            result = parse_datetime(value)
            if not result:
                try:
                    result = datetime.combine(
                        parse_date(value), datetime.min.time()
                    )
                except TypeError:
                    self.fail('bad_str')
            return result
        elif isinstance(value, (int, float)):
            try:
                return datetime.utcfromtimestamp(value)
            except ValueError:
                self.fail('bad_int')
        else:
            self.fail('not_int_or_str')

    def to_representation(self, string_value):
        if isinstance(string_value, (str, unicode, int, float)):
            value = self.to_internal_value(string_value)
        else:
            value = string_value

        return value.isoformat()


class HashString(BadgePotentiallyEmptyField, serializers.Field):
    """
    A representation of a badge recipient identifier that indicates a hashing
    algorithm and hashed value.
    """

    def to_internal_value(self, data):
        try:
            data = data.lower()
        except AttributeError:
            raise serializers.ValidationError("Invalid data. Expected a str.")

        patterns = (
            r'^sha1\$[a-f0-9]{40}$',
            r'^sha256\$[a-f0-9]{64}$',
            r'^md5\$[a-fA-F0-9]{32}$'
        )

        if not any(re.match(pattern, data) for pattern in patterns):
            raise serializers.ValidationError(
                "Invalid data. String is not recognizably formatted.")

        return data


class AlignmentObjectSerializer(BadgePotentiallyEmptyField, serializers.Serializer):
    """
    A small JSON object literal describing a BadgeClass's alignment to
    a particular standard or competency map URL.
    """
    name = serializers.CharField(required=True)
    url = serializers.URLField(required=True)
    description = serializers.CharField(required=False)

    def to_representation(self, value):
        # Not implemented yet. This is going to be tricky.
        return {}


class RecipientSerializer(serializers.Serializer):
    """
    A representation of a 1.0 Open Badge recipient has either a hashed or
    plaintext identifier (email address).
    """
    identity = serializers.CharField(required=True)  # TODO: email | HashString
    type = serializers.CharField(required=True)
    hashed = serializers.BooleanField(required=True)

    def to_representation(self, value):
        return {
            'type': self.context.get('type', 'email'),
            'recipient': self.context.get('recipient_id')
        }


class VerificationObjectSerializer(serializers.Serializer):
    """
    1.0 Open Badges use a VerificationObject to indicate what authentication
    procedure a consumer should attempt and link to the relevant hosted
    verification resource, which is either a hosted copy of a badge instance
    or the issuer's public key.
    """
    type = serializers.ChoiceField(['hosted', 'signed'], required=True)
    url = serializers.URLField(required=True)


class ExtensionsValidator(object):
    def __init__(self, message="Invalid Extension"):
        super(ExtensionsValidator, self).__init__()
        self.message = message

    def __call__(self, value):
        return


class BadgeExtensionsField(DictField):
    def run_validation(self, *args, **kwargs):
        return super(BadgeExtensionsField, self).run_validation(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(BadgeExtensionsField, self).__init__(*args, **kwargs)
        validator = ExtensionsValidator()
        self.validators.append(validator)

    def get_value(self, dictionary):
        value = {k: dictionary.get(k) for k in filter(lambda k: k.startswith('extension:'), dictionary.keys())}
        return value


class ExtensionMixin(serializers.Serializer):
    extensions = BadgeExtensionsField(required=False)


