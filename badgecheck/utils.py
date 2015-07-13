import hashlib
import json
import re

from openbadges_bakery import unbake

def get_instance_url_from_assertion(assertion):
    """
    With a python dict as input, return the URL from where it may appear
    in different versions of the Open Badges specification
    """
    options = [
        assertion.get('id'),
        assertion.get('@id'),
        assertion.get('verify', {}).get('url')
    ]
    # Return the first non-None item in options or None.
    return next(iter([item for item in options if item is not None]), None)


def get_instance_url_from_(signed_assertion):
    raise NotImplementedError("Parsing JWT tokens not implemented.")


def get_instance_url_from_image(imageFile):
    """ unbake an open file, and return the assertion URL contained within """
    image_contents = unbake(imageFile)

    if image_contents is None:
        raise ValidationError("No assertion found in image")

    return get_instance_url_from_unknown_string(image_contents)


def get_instance_url_from_unknown_string(badge_input):
    try:
        assertion = json.loads(badge_input)
    except ValueError:
        earl = re.compile(r'^https?')
        if earl.match(badge_input):
            return badge_input

        jwt_regex = re.compile(r'^\w+\.\w+\.\w+$')
        if jwt_regex.match(badge_input):
            return get_instance_url_from_jwt(badge_input)
    else:
        return get_instance_url_from_assertion(assertion)


def verify_hash(identity_string, hash_string, salt=''):
    if hash_string.startswith('sha256$'):
        return hash_string == 'sha256$' + hashlib.sha256(identity_string+salt).hexdigest()
    elif hash_string.startswith('md5$'):
        return hash_string == 'md5$' + hashlib.md5(identity_string+salt).hexdigest()
    else:
        return hash_string == identity_string


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d

    def __unicode__(self):
        return str(self.__dict__)
