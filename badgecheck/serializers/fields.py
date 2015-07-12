from datetime import datetime
import re

from django.utils.dateparse import parse_datetime, parse_date

from rest_framework import serializers
from rest_framework.fields import SkipField


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


class BadgeStringField(BadgePotentiallyEmptyField, BadgeCharField, serializers.CharField):
    def to_representation(self, value):
        return value


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
