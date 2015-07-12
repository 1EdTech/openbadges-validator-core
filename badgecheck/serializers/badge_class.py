from collections import OrderedDict

from rest_framework import serializers

import issuer
from .fields import (AlignmentObjectSerializer, BadgeStringField,
                     BadgeURLField, BadgeImageURLField)
from ..utils import ObjectView


class BadgeClassSerializerV0_5(serializers.Serializer):
    """
    A 0.5 Open Badge assertion embedded a representation of the accomplishment
    awarded.
    """
    version = serializers.ChoiceField(['0.5.0'], write_only=True, required=False)
    name = BadgeStringField(required=True)
    description = BadgeStringField(required=True)
    image = BadgeImageURLField(required=True)
    criteria = BadgeURLField(required=True)
    issuer = issuer.IssuerSerializerV0_5(write_only=True, required=True)

    def to_representation(self, badge):
        obj = ObjectView(dict(badge))
        badge_props = super(
            BadgeClassSerializerV0_5, self).to_representation(obj)

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'BadgeClass'

        result = OrderedDict(header.items() + badge_props.items())
        issuer_serializer = issuer.IssuerSerializerV0_5(
            badge.get('issuer'),
            context=self.context
        )
        result['issuer'] = issuer_serializer.data

        return result


class BadgeClassSerializerV1_0(serializers.Serializer):
    name = BadgeStringField(required=True)
    description = BadgeStringField(required=True)
    image = BadgeImageURLField(required=True)
    criteria = BadgeURLField(required=True)
    issuer = serializers.URLField(write_only=True, required=True)
    alignment = serializers.ListField(
        child=AlignmentObjectSerializer(),
        required=False, write_only=True
    )  # TODO: implement to_representation
    tags = serializers.ListField(child=BadgeStringField(), required=False)

    def to_representation(self, badge):
        obj = ObjectView(dict(badge))
        badge_props = super(
            BadgeClassSerializerV1_0, self).to_representation(obj)

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'BadgeClass'
        header['id'] = self.context.get('instance').badge_url

        result = OrderedDict(header.items() + badge_props.items())

        issuer_serializer = issuer.IssuerSerializerV1_0(
            self.context.get('instance').issuer, context=self.context
        )
        result['issuer'] = issuer_serializer.data

        return result
