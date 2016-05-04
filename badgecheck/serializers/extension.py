# Created by wiggins@concentricsky.com on 4/21/16.
from rest_framework import serializers

from badgecheck.serializers import LDTypeField, BadgeStringField


class ExtensionSerializerV1_1(serializers.Serializer):
    type = LDTypeField(required=True, required_type='Extension')

    def get_fields(self):
        fields = super(ExtensionSerializerV1_1, self).get_fields()
        fields.update({
            ('@context', BadgeStringField(required=True, required_value='https://w3id.org/openbadges/v1'))
        })
        return fields

