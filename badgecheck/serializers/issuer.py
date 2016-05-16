from collections import OrderedDict

from rest_framework import serializers

from badgecheck.serializers.fields import (BadgeStringField, BadgeURLField, BadgeEmailField, BadgeImageURLOrDataURIField, LDTypeField)
from badgecheck.utils import ObjectView
from badgecheck.validators import JsonLdValidator


class IssuerSerializerV0_5(serializers.Serializer):
    """
    A representation of a badge's issuing organization is found embedded in
    0.5 badge assertions.
    """
    origin = BadgeURLField(required=True)
    name = BadgeStringField(required=True)
    org = BadgeStringField(write_only=True, required=False)
    contact = BadgeEmailField(required=False)

    def to_representation(self, issuer):
        obj = ObjectView(dict(issuer))
        issuer_props = super(
            IssuerSerializerV0_5, self).to_representation(obj)

        # Update old keys to new ones
        for prop in (('origin', 'url'), ('contact', 'email')):
            if issuer_props.get(prop[0]) is not None:
                issuer_props[prop[1]] = issuer_props.pop(prop[0])

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'Issuer'

        result = OrderedDict(header.items() + issuer_props.items())

        return result


class IssuerSerializerV1_0(serializers.Serializer):
    name = BadgeStringField(required=True)
    url = BadgeURLField(required=True)
    description = BadgeStringField(required=False)
    email = BadgeEmailField(required=False)
    image = BadgeImageURLOrDataURIField(required=False)
    revocationList = BadgeURLField(required=False)

    def to_representation(self, badge):
        obj = ObjectView(dict(badge))
        issuer_props = super(
            IssuerSerializerV1_0, self).to_representation(obj)

        header = OrderedDict()
        if not self.context.get('embedded', False):
            header['@context'] = 'https://w3id.org/openbadges/v1'
        header['type'] = 'Issuer'
        header['id'] = self.context.get('instance').issuer_url

        result = OrderedDict(header.items() + issuer_props.items())

        return result


class IssuerSerializerV1_1(IssuerSerializerV1_0):
    id = BadgeURLField(required=True)
    type = LDTypeField(required=True, required_type='IssuerOrg')

    def __init__(self, *args, **kwargs):
        super(IssuerSerializerV1_1, self).__init__(*args, **kwargs)
        self.validators.append(JsonLdValidator())

    def get_fields(self):
        fields = super(IssuerSerializerV1_1, self).get_fields()
        fields.update({
            ('@context', BadgeStringField(required=True, required_value='https://w3id.org/openbadges/v1'))
        })
        return fields

