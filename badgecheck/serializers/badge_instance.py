from collections import OrderedDict

from rest_framework import serializers

import badge_class
from .fields import (BadgeDateTimeField, HashString,
                     RecipientSerializer, VerificationObjectSerializer,
                     BadgeURLField, BadgeImageURLField, BadgeStringField)
from ..utils import ObjectView


class V0_5Base(serializers.Serializer):
    """
    Shared requirements between both 0.5 versions of the Open Badges
    specification for badge assertions.
    """
    badge = badge_class.BadgeClassSerializerV0_5(write_only=True, required=True)
    issued_on = BadgeDateTimeField(required=False)
    expires = BadgeDateTimeField(required=False)
    evidence = BadgeURLField(required=False)

    def to_representation(self, instance):
        obj = ObjectView(instance.json)
        self.context['recipient_id'] = instance.recipient_id

        props = super(V0_5Base, self).to_representation(obj)
        props['recipient'] = RecipientSerializer({
            'recipient': instance.recipient_id,
            'hashed': False,
            'type': 'email'
        }, context={'recipient_id': instance.recipient_id}).data

        for prop in (('issued_on', 'issuedOn'),):
            if props.get(prop[0]) is not None:
                props[prop[1]] = props.pop(prop[0])

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'Assertion'
        header['id'] = instance.instance_url

        result = OrderedDict(header.items() + props.items())

        badge_class_serializer = badge_class.BadgeClassSerializerV0_5(
            instance.json.get('badge'), context={'instance': instance, 'embedded': True}
        )
        result['badge'] = badge_class_serializer.data

        return result


class BadgeInstanceSerializerV0_5_1(V0_5Base):
    """
    Serializer for 0.5 Open Badge assertions that have hashed recipient
    email addresses.
    """
    recipient = HashString(write_only=True, required=True)
    salt = BadgeStringField(write_only=True, required=False)


class BadgeInstanceSerializerV0_5_0(V0_5Base):
    """
    Serializer for the 0.5.0 specification version before the possibility of
    hashing a recipient identifier was introduced.
    """
    recipient = serializers.EmailField(write_only=True, required=True)


class BadgeInstanceSerializerV1_0(serializers.Serializer):
    """
    Serializer for 1.0 Open Badge assertions, which require a uid, have no
    linked data context.
    """
    uid = BadgeStringField(required=True)
    recipient = RecipientSerializer(required=True)
    badge = serializers.URLField(write_only=True, required=True)
    issuedOn = BadgeDateTimeField(required=True)
    verify = VerificationObjectSerializer(write_only=True, required=True)
    image = BadgeImageURLField(required=False)
    expires = BadgeDateTimeField(required=False)
    evidence = BadgeURLField(required=False)

    def to_representation(self, instance):
        """
        Converts a 1.0 Badge Instance to serialized verbose v1.1 style output
        """
        obj = ObjectView(instance.json)
        self.context['recipient_id'] = instance.recipient_id

        instance_props = super(
            BadgeInstanceSerializerV1_0, self).to_representation(obj)
        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'Assertion'
        header['id'] = instance.instance_url

        result = OrderedDict(header.items() + instance_props.items())

        badge_class_serializer = badge_class.BadgeClassSerializerV1_0(
            instance.badge, context={'instance': instance, 'embedded': True}
        )
        result['badge'] = badge_class_serializer.data

        return result
