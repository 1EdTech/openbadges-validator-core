import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from pyld import jsonld


class DataURIValidator(RegexValidator):
    regex = re.compile(
        r'^data:'              # required scheme
        r'(\w+\/\w+)?'         # optional media type
        r'(;charset=[\w-]+)?'  # optional charset
        r'(;base64)?'          # optional base64
        r',(.+)'               # data
    )

    def __call__(self, *args, **kwargs):
        super(DataURIValidator, self).__call__(*args, **kwargs)


class URLOrDataURIValidator(object):

    def __init__(self, *args, **kwargs):
        self.data_uri_validator = DataURIValidator(*args, **kwargs)
        self.url_validator = URLValidator(*args, **kwargs)

    def __call__(self, value):
        try:
            self.data_uri_validator(value)
        except ValidationError as e:
            self.url_validator(value)


class LDTypeValidator(object):
    message = 'Type does not match.'

    def __init__(self, type_name=None, message=None):
        self.type_name = type_name
        if message is not None:
            self.message = message

    def __call__(self, value):
        if isinstance(value, basestring):
            if self.type_name != value:
                raise ValidationError(message=self.message)
        else:
            if self.type_name not in value:
                raise ValidationError(message=self.message)


class JsonLdValidator(object):
    message = 'Invalid JSON LD document: {}'

    def __call__(self, value):
        context = value.get('@context', None)
        if context is None:
            raise ValidationError(message=self.message.format('@context is missing'))
        try:
            expanded = jsonld.expand(value)
        except Exception as e:
            raise ValidationError(message=self.message.format('error during expansion: {}'.format(e.message)))

        try:
            compacted = jsonld.compact(expanded, context)
        except Exception as e:
            raise ValidationError(message=self.message.format('error during compaction: {}'.format(e.message)))
