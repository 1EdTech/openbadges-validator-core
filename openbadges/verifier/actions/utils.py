import hashlib
import six
import uuid


def generate_task_key():
    return uuid.uuid4().hex


def generate_task_signature(task_name, *args):
    content = b''
    for arg in args:
        try:
            content += six.ensure_binary(str(arg))
        except TypeError:
            pass

    return b'__'.join([
        six.ensure_binary(task_name),
        six.ensure_binary(hashlib.md5(content).hexdigest())
    ]).decode('utf-8')
