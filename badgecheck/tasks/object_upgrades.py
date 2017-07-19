import aniso8601
import datetime
import json
import pytz

from ..actions.graph import patch_node
from ..exceptions import TaskPrerequisitesError
from ..state import get_node_by_id

from .utils import task_result
from .validation import OBClasses, ValueTypes, PrimitiveValueValidator


def _upgrade_datetime(t):
    try:
        return datetime.datetime.fromtimestamp(float(t), pytz.utc).isoformat()
    except (TypeError, ValueError):
        try:
            dt = aniso8601.parse_datetime(t)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt.isoformat()
        except (ValueError, TypeError):
            dt = datetime.datetime.strptime(t, '%Y-%m-%d')
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt.isoformat()


def upgrade_1_1_node(state, task_meta, **options):
    try:
        node_id = task_meta.get('node_id')
        node = get_node_by_id(state, node_id)
        data = node.copy()
    except IndexError:
        raise TaskPrerequisitesError()

    actions = []
    expected_class = task_meta.get('expected_class')

    if expected_class == OBClasses.Assertion or data.get('recipient') is not None:
        # Do assertion upgrades
        dt_validator = PrimitiveValueValidator(ValueTypes.DATETIME)
        issued_on = data.get('issuedOn')
        patch = {}
        if not dt_validator(issued_on):
            try:
                patch['issuedOn'] = _upgrade_datetime(issued_on)
            except TypeError:
                return task_result(False, "Could not interpret datetime {}".format(issued_on))

        if data.get('expires') and not dt_validator(data['expires']):
            try:
                patch['expires'] = _upgrade_datetime(data['expires'])
            except TypeError:
                return task_result(False, "Could not interpret datetime {}".format(data['expires']))

        if patch:
            actions.append(patch_node(node_id, patch))

    elif expected_class == OBClasses.BadgeClass or data.get('criteria') is not None:
        # Do badgeclass upgrades
        if data.get('alignment'):
            alignment_fixed = False
            alignment_node = data['alignment'].copy()
            for term, new_term in [('url', 'targetUrl'), ('name', 'targetName'), ('description', 'targetDescription')]:
                if alignment_node.get(term) and not alignment_node.get(new_term):
                    alignment_fixed = True
                    alignment_node[new_term] = alignment_node[term]
                    del alignment_node[term]
            if alignment_fixed:
                patch = {'alignment': alignment_node}
                actions.append(patch_node(node_id, patch))
    if actions:
        return task_result(True, "Node {} upgraded from v1.1 to 2.0".format(node_id), actions)
    else:
        return task_result(True, "Node {} needed no content upgrades from v1.1 to 2.0".format(node_id))
