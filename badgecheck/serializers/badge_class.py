from collections import OrderedDict

from rest_framework import serializers

from badgecheck.validators import JsonLdValidator
from badgecheck.serializers.fields import (AlignmentObjectSerializer, BadgeStringField,
                                           BadgeURLField, BadgeImageURLField, BadgeImageURLOrDataURIField, LDTypeField, ExtensionMixin)
from badgecheck.utils import ObjectView
from badgecheck.serializers.issuer import IssuerSerializerV1_1, IssuerSerializerV1_0, IssuerSerializerV0_5


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
    issuer = IssuerSerializerV0_5(write_only=True, required=True)

    def to_representation(self, badge):
        obj = ObjectView(dict(badge))
        badge_props = super(
            BadgeClassSerializerV0_5, self).to_representation(obj)

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'BadgeClass'

        result = OrderedDict(header.items() + badge_props.items())
        issuer_serializer = IssuerSerializerV0_5(
            badge.get('issuer'),
            context=self.context
        )
        result['issuer'] = issuer_serializer.data

        return result


class BadgeClassSerializerV1_0(serializers.Serializer):
    name = BadgeStringField(required=True)
    description = BadgeStringField(required=True)
    image = BadgeImageURLOrDataURIField(required=True)
    criteria = BadgeURLField(required=True)
    issuer = serializers.URLField(write_only=True, required=True)
    alignment = serializers.ListField(
        child=AlignmentObjectSerializer(),
        required=False, write_only=True
    )  # TODO: implement to_representation
    tags = serializers.ListField(child=BadgeStringField(), required=False)

    def to_representation(self, badge):
        obj = ObjectView(dict(badge))
        badge_props = super(BadgeClassSerializerV1_0, self).to_representation(obj)

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'BadgeClass'
        header['id'] = self.context.get('instance').badge_url

        result = OrderedDict(header.items() + badge_props.items())

        issuer_serializer_class = self.get_issuer_serializer_class()
        issuer_serializer = issuer_serializer_class(
            self.context.get('instance').issuer, context=self.context
        )
        result['issuer'] = issuer_serializer.data

        return result

    def get_issuer_serializer_class(self):
        return IssuerSerializerV1_0


class BadgeClassSerializerV1_1(ExtensionMixin, BadgeClassSerializerV1_0):
    id = BadgeURLField(required=True)
    type = LDTypeField(required=True, required_type='BadgeClass')

    def __init__(self, *args, **kwargs):
        super(BadgeClassSerializerV1_1, self).__init__(*args, **kwargs)
        self.validators.append(JsonLdValidator())

    def get_issuer_serializer_class(self):
        return IssuerSerializerV1_1

    def get_fields(self):
        fields = super(BadgeClassSerializerV1_1, self).get_fields()
        fields.update({
            ('@context', BadgeStringField(required=True, required_value='https://w3id.org/openbadges/v1'))
        })
        return fields
