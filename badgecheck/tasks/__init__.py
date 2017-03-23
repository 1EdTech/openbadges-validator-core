from input import detect_input_type
from task_types import (DETECT_INPUT_TYPE,)


functions = {
    DETECT_INPUT_TYPE: detect_input_type
}


def task_named(key):
    return functions[key]
