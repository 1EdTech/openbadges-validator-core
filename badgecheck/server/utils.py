import six


def validate_input(data):
    return isinstance(data, six.string_types)
