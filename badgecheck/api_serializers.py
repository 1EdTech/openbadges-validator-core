import json
from collections import OrderedDict

from rest_framework import serializers

from badgecheck import RemoteBadgeInstance, AnalyzedBadgeInstance
from badgecheck.utils import get_instance_url_from_unknown_string, get_instance_url_from_image, jsonld_document_loader


class UndefinableImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if data == "undefined":
            return None
        return super(UndefinableImageField, self).to_internal_value(data)


class IntegritySerializer(serializers.Serializer):
    recipient = serializers.CharField(required=True, source='recipient_id')

    assertion = serializers.CharField(required=False, write_only=True)
    url = serializers.URLField(required=False, write_only=True)
    image = UndefinableImageField(required=False, write_only=True)

    is_valid = serializers.BooleanField(read_only=True)
    version = serializers.CharField(read_only=True)
    errors = serializers.ListField(read_only=True, source='all_errors')
    json = serializers.DictField(read_only=True, source='data')

    instance = serializers.DictField(read_only=True, source='badge_instance')
    instance_url = serializers.URLField(read_only=True)
    badge = serializers.DictField(read_only=True)
    badge_url = serializers.URLField(read_only=True)
    issuer = serializers.DictField(read_only=True)
    issuer_url = serializers.URLField(read_only=True)

    def validate(self, data):
        # make sure empty {} assertion data doesn't exist.
        try:
            assertion = data['assertion']
        except KeyError:
            pass
        else:
            try:
                json.loads(assertion)
            except ValueError:
                data.pop('assertion')


        # if django-rest-swagger sent us "undefined" strip it
        if 'image' in data and not data.get('image', None):
            data.pop('image')

        # Make sure there is only input of one type.
        valid_inputs = \
            dict(filter(lambda tuple: tuple[0] in ['url', 'image', 'assertion'],
                        data.items()))

        if len(valid_inputs.keys()) != 1:
            raise serializers.ValidationError(
                "Only one instance input field allowed. Recieved "
                + json.dumps(valid_inputs.keys())
            )

        return data

    def create(self, validated_data):
        if validated_data.get('url'):
            url = validated_data.get('url')
        elif validated_data.get('image') is not None:
            image = validated_data.get('image')
            image.open()
            url = get_instance_url_from_image(image)
        elif validated_data.get('assertion'):
            url = get_instance_url_from_unknown_string(
                validated_data.get('assertion')
            )

        rbi = RemoteBadgeInstance(
            instance_url=url,
            recipient_id=validated_data.get('recipient_id'),
            **{'document_loader': self.context.get('document_loader', jsonld_document_loader)}
        )

        abi = AnalyzedBadgeInstance(rbi)
        return abi


class IntegritySerializerV2(IntegritySerializer):
    def to_representation(self, instance):
        errors = [
            {
                "level": e[0].split(".")[0],
                "source": e[0].split(".")[1],
                "message": e[1],
            } for e in instance.all_errors()
        ]
        ret = OrderedDict([
            ("@context", "https://badgecheck.io/public/context"),
            ("@type", "BadgeVerificationReport"),
            ("request", dict(self.initial_data)),
            ("results", OrderedDict([
                ("is_valid", instance.is_valid()),
                ("version", instance.badge_instance.version),
                ("errors", errors),

                ("instance", instance.badge_instance),
                ("badge", instance.badge),
                ("issuer", instance.issuer),
            ])),
            ("updated", {})
        ])
        return ret
