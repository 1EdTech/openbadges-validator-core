import inspect
import re
import sys
from urlparse import urlparse
from UserDict import UserDict

from django.core.exceptions import ValidationError

import requests
from requests.exceptions import ConnectionError

import serializers
import utils


class RemoteBadgeInstance(object):
    """
    A RemoteBadgeInstance is a remotely fetched in-memory representation of
    a badge instance, containing its corresponding badge (class) and issuer.
    """

    def __init__(self, instance_url, recipient_id=None):
        req_head = {'Accept': 'application/json'}

        self.instance_url = instance_url
        self.recipient_id = recipient_id

        try:
            self.badge_instance = requests.get(
                instance_url, headers=req_head).json()
            self.json = self.badge_instance.copy()

            # 0.x badges embedded badge and issuer information
            if not isinstance(self.badge_instance['badge'], dict):
                self.badge_url = self.badge_instance['badge']
                self.badge = requests.get(
                    self.badge_url, headers=req_head).json()
                self.json['badge'] = self.badge.copy()

                self.issuer_url = self.badge['issuer']
                self.issuer = requests.get(
                    self.issuer_url, headers=req_head).json()
                self.json['badge']['issuer'] = self.issuer.copy()
            else:
                self.badge = self.badge_instance['badge'].copy()
                self.issuer = self.badge['issuer'].copy()
        except ConnectionError as e:
            raise ValidationError(e.message)

    def __getitem__(self, key):
        return self.badge_instance[key]

    def __repr__(self):
        return str(self.badge_instance)


class AnnotatedDict(UserDict, object):

    def __init__(self, dictionary):
        super(AnnotatedDict, self).__init__(dictionary)

        self.versions = []
        self.version_errors = {}
        self.version = None


class AnalyzedBadgeInstance(RemoteBadgeInstance):

    def __init__(self, badge_instance, recipient_id=None, recipient_ids=None):
        if not isinstance(badge_instance, RemoteBadgeInstance):
            raise TypeError('Expected RemoteBadgeInstance')

        self.non_component_errors = []
        self.json = badge_instance.json.copy()
        self.instance_url = badge_instance.instance_url

        # These properties are now dict-like adding metadata within properties
        self.badge_instance = \
            AnnotatedDict(badge_instance.badge_instance.copy())

        # 0.x badge instances embedded the badge and issuer information
        try:
            self.badge_url = badge_instance.badge_url
            self.issuer_url = badge_instance.issuer_url

            self.badge = AnnotatedDict(badge_instance.badge.copy())
            self.issuer = AnnotatedDict(badge_instance.issuer.copy())

            components = (
                ('badge_instance', self.badge_instance),
                ('badge_class', self.badge),
                ('issuer', self.issuer))
        except AttributeError:
            components = (('badge_instance', self.badge_instance),)

        self.version_signature = re.compile(r"[Vv][0-9](_[0-9])+$")

        for module_name, component in components:
            self.add_versions(component, module_name)
            self.evaluate_version(component)

        if self.version is None:
            pass
        elif self.version.startswith('v1'):
            self.check_origin()
        elif self.version.startswith('v0'):
            self.check_origin_0_5()

        self.recipient_id = (recipient_id
                             or getattr(badge_instance, 'recipient_id', None))
        self.check_recipient(recipient_ids)

        self.check_version_continuity()

    def add_versions(self, component, module_name):
        module = getattr(serializers, module_name)
        classes = zip(*inspect.getmembers(sys.modules[module.__name__],
                                          inspect.isclass))[0]

        component.versions = filter(
            lambda class_: self.version_signature.search(class_), classes)

    def evaluate_version(self, component):
        component.version = None
        for version in component.versions:

            SerializerClass = getattr(serializers, version)
            serializer = SerializerClass(
                data=component.data,
                context={'recipient_id': self.recipient_id}
            )

            if not serializer.is_valid():
                component.version_errors[version] = serializer.errors
            else:
                component.version = self.get_version(version)
                component.serializer = SerializerClass

    def get_version(self, version):
        try:
            return self.version_signature.search(version).group() \
                .replace('_', '.').replace('V', 'v')
        except AttributeError:
            return None

    def check_origin(self):
        same_domain = (urlparse(self.instance_url).netloc
                       == urlparse(self.badge_url).netloc
                       == urlparse(self.issuer_url).netloc)
        if not same_domain:
            self.non_component_errors.append(
                ['warning.domain', "Badge components don't share the same domain."])

        local_platform = (urlparse(self.issuer_url).netloc
                          == urlparse(self.issuer.get('url')).netloc)
        if not local_platform:
            self.non_component_errors.append([
                'warning.platform',
                "Badge was issued from a platform ("
                + urlparse(self.issuer_url).netloc
                + ") separate from the issuer's domain ("
                + urlparse(self.issuer.get('url')).netloc + ")."
            ])

    def check_origin_0_5(self):
        issuer_origin = self.json.get('badge', {}).get('issuer', {}).get('origin', '')
        local_platform = (urlparse(issuer_origin).netloc
                          == urlparse(self.instance_url).netloc)

        if not local_platform:
            self.non_component_errors.append([
                'warning.platform',
                "Badge was issued from a platform ("
                + urlparse(self.instance_url).netloc
                + ") separate from the issuer's domain ("
                + urlparse(issuer_origin).netloc + ")."
            ])

    def check_recipient(self, recipient_ids):
        """
        Check if a badge recipient is indeed the expected recipient (email address)
        """
        recipient_chunk = self.badge_instance.get('recipient', '')
        if isinstance(recipient_chunk, dict):
            hash_string = recipient_chunk.get('identity')
            salt = recipient_chunk.get('salt', '')
        else:
            hash_string = recipient_chunk
            salt = self.badge_instance.get('salt', '')

        if recipient_ids is None:
            recipient_ids = [self.recipient_id]

        for identifier in recipient_ids:
            if utils.verify_hash(identifier, hash_string, salt) is True:
                self.recipient_id = identifier
                break
        else:
            self.non_component_errors.append([
                'error.recipient',
                'Recipient id "%s" did not match badge contents: "%s"'
                % (str(recipient_ids), hash_string)
            ])

    def check_version_continuity(self):
        """
        Check if all components of a badge are the same version
        """
        try:
            if not (self.badge.version == self.issuer.version == self.version):
                self.non_component_errors.append([
                    'warning.version',
                    "Components assembled with different specification versions."
                    + " Assertion: " + self.version + ", BadgeClass: "
                    + self.badge.version + ", Issuer: " + self.issuer.version
                ])
        except (TypeError, AttributeError):
            pass

    def is_valid(self):
        """
        Check if all components of a badge have a version and that there are no
        non_component_errors.
        """
        return all(e[0].startswith('warning') for e in self.all_errors())

    def all_errors(self):
        errors = list(self.non_component_errors)
        for component_type in ('badge_instance', 'badge', 'issuer'):

            try:
                component = getattr(self, component_type)
            except AttributeError:
                pass
            else:
                if component is not None and component.version is None:
                    errors += [[
                        'error.version_detection',
                        'Could not determine Open Badges version of %s'
                        % component_type,
                        component.version_errors
                    ]]

        return errors

    @property
    def data(self):
        """
        Return a canonical serialization
        """
        if self.is_valid():
            serializer = self.serializer(self)
            return serializer.data

    def __getattr__(self, key):
        base_properties = ['instance_url', 'recipient_id',
                           'badge', 'issuer', 'json']
        if key not in base_properties:
            return getattr(self.badge_instance, key)

    def __getitem__(self, key):
        return self.badge_instance[key]

    def __repr__(self):
        return str(self.badge_instance)
