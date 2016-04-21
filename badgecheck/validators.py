import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator


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

