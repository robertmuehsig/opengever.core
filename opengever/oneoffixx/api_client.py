from hashlib import sha256
from opengever.oneoffixx.exceptions import OneoffixxBackendException
from opengever.oneoffixx.exceptions import OneoffixxConfigurationException
from opengever.oneoffixx.interfaces import IOneoffixxSettings
from plone import api
from plone.memoize import ram
from time import time
from urlparse import urlunsplit
import json
import os.path
import requests
import urllib


def oneoffixx_access_token_cachekey(*args):
    """We will always have to explicitly invalidate this cache key!"""
    return '-'.join(('oneoffixx-access-token', api.user.get_current().id))


def oneoffixx_templatelibrary_id_cachekey(*args):
    """Cache the template library, per user.

    The left-behind-by-instability cache keys this produces will get reaped by
    the global cache LRU cleanups.

    The timeout is configurable in the registry and used a part of the cache
    key so changing the timeout immediately invalidates all caches.
    """
    timeout = api.portal.get_registry_record('cache_timeout', interface=IOneoffixxSettings)
    return '-'.join(('oneoffixx_templatelibrary_id', api.user.get_current().id, str(timeout), str(time() // timeout), ))


def oneoffixx_template_groups_cachekey(*args):
    """Cache the template groups, per user.

    The left-behind-by-instability cache keys this produces will get reaped by
    the global cache LRU cleanups.

    The timeout is configurable in the registry and used a part of the cache
    key so changing the timeout immediately invalidates all caches.
    """
    timeout = api.portal.get_registry_record('cache_timeout', interface=IOneoffixxSettings)
    return '-'.join(('oneoffixx_template_groups', api.user.get_current().id, str(timeout), str(time() // timeout), ))


def oneoffixx_favorites_cachekey(*args):
    """Cache the favorite templates, per user.

    The left-behind-by-instability cache keys this produces will get reaped by
    the global cache LRU cleanups.

    The timeout is configurable in the registry and used as a part of the cache
    key so changing the timeout immediately invalidates all caches.
    """
    timeout = api.portal.get_registry_record('cache_timeout', interface=IOneoffixxSettings)
    return '-'.join(('oneoffixx_favorites', api.user.get_current().id, str(timeout), str(time() // timeout), ))


class OneoffixxAPIClientSingleton(type):
    """Ensure we have a shared configurable singleton of the client."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Use the class variable as a cache to ensure we'll only have one of these."""
        if cls not in cls._instances:
            cls._instances[cls] = super(OneoffixxAPIClientSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class OneoffixxAPIClient(object):
    """A caching API client for fetching templates from Oneoffixx backends."""

    __metaclass__ = OneoffixxAPIClientSingleton

    def __init__(self, session=None, credentials=None):
        """We initialise a shared session.

        The access token for the session is also fetched and cached.
        """
        super(OneoffixxAPIClient, self).__init__()
        self.session = session or requests.Session()
        self.credentials = credentials
        self.refresh_access_token()

    def get_credentials_file_path(self):
        dotdir = os.path.expanduser(os.path.join('~', '.opengever', 'oneoffixx'))
        creds_path = os.path.join(dotdir, 'oneoffixx.json')
        if not os.path.isfile(creds_path):
            raise OneoffixxConfigurationException('Oneoffixx configuration file missing!')
        return creds_path

    def get_credentials(self):
        """Read the per deployment Oneoffixx backend credentials.

        We've deemed hitting this one every time we need to fetch a new token
        is OK.
        """
        if not self.credentials:
            try:
                with open(self.get_credentials_file_path()) as f:
                    credentials = json.loads(f.read())
            except ValueError:
                raise OneoffixxConfigurationException('Oneoffixx configuration file malformed!')
            return credentials

        return self.credentials

    def get_oneoffixx_api_protocol(self):
        """Return the protocol used by the Oneoffixx API.

        This is normally HTTP or HTTPS, but as tests can also use mock, we do
        not want to add any evaluation logic here. It is not expected people
        ever have to configure this to a non-default setting.
        """
        return api.portal.get_registry_record(
            'protocol', interface=IOneoffixxSettings)

    def get_oneoffixx_api_hostname(self):
        hostname = api.portal.get_registry_record(
            'hostname', interface=IOneoffixxSettings)
        if not hostname:
            raise OneoffixxConfigurationException(
                'No Oneoffixx backend hostname configured!')
        return hostname

    def get_oneoffixx_api_path_prefix(self):
        path_prefix = api.portal.get_registry_record(
            'path_prefix', interface=IOneoffixxSettings)
        if path_prefix:
            if path_prefix[0] != '/':
                raise OneoffixxConfigurationException(
                    'Oneoffixx API path prefix erroneously configured without'
                    ' a leading slash.'
                )
            elif path_prefix[-1] == '/':
                raise OneoffixxConfigurationException(
                    'Oneoffixx API path prefix erroneously configured with a'
                    ' trailing slash.'
                )
        return path_prefix

    def get_oneoffixx_api_auth_path(self):
        auth_path = api.portal.get_registry_record(
            'auth_path', interface=IOneoffixxSettings)
        if not auth_path:
            raise OneoffixxConfigurationException(
                'No Oneoffixx API auth path configured!')
        if auth_path[0] != '/':
            raise OneoffixxConfigurationException(
                'Oneoffixx API auth path erroneously configured without a'
                ' leading slash.'
            )
        elif auth_path[-1] == '/':
            raise OneoffixxConfigurationException(
                'Oneoffixx API auth path erroneously configured with a'
                ' trailing slash.'
            )
        return auth_path

    def get_oneoffixx_api_webservice_path(self):
        webservice_path = api.portal.get_registry_record(
            'webservice_path', interface=IOneoffixxSettings)
        if not webservice_path:
            raise OneoffixxConfigurationException(
                'No Oneoffixx API webservice path configured!')
        if webservice_path[0] != '/':
            raise OneoffixxConfigurationException(
                'Oneoffixx API auth path erroneously configured without a'
                ' leading slash.'
            )
        elif webservice_path[-1] == '/':
            raise OneoffixxConfigurationException(
                'Oneoffixx API auth path erroneously configured with a'
                ' trailing slash.'
            )
        return webservice_path

    def get_oneoffixx_auth_url(self):
        protocol = self.get_oneoffixx_api_protocol()
        hostname = self.get_oneoffixx_api_hostname()
        prefix = self.get_oneoffixx_api_path_prefix()
        auth_path = self.get_oneoffixx_api_auth_path()
        path = u''.join((prefix, auth_path))
        return urlunsplit((protocol, hostname, path, u'', u''))

    def get_oneoffixx_webservice_url(self):
        protocol = self.get_oneoffixx_api_protocol()
        hostname = self.get_oneoffixx_api_hostname()
        prefix = self.get_oneoffixx_api_path_prefix()
        auth_path = self.get_oneoffixx_api_webservice_path()
        path = u''.join((prefix, auth_path))
        return urlunsplit((protocol, hostname, path, u'', u''))

    @ram.cache(oneoffixx_access_token_cachekey)
    def get_oneoffixx_access_token(self):
        """Get and blindly persist per user id the access token.

        We will invalidate and refetch elsewhere if we have an invalid token.

        The user id provides us a stable cache key to invalidate with.
        """
        url = self.get_oneoffixx_auth_url()
        credentials = self.get_credentials()
        try:
            client_id = credentials['client_id']
            client_secret = credentials['client_secret']
            preshared_key = credentials['preshared_key']
        except KeyError:
            raise OneoffixxConfigurationException('Oneoffixx configuration file missing data!')

        fake_sid = api.portal.get_registry_record('fake_sid', interface=IOneoffixxSettings)
        real_sid = api.user.get_current().getProperty('objectSid', None)

        if real_sid and not isinstance(real_sid, str):
            raise OneoffixxConfigurationException(
                "SID returned from LDAP as 'objectSid' is not a string, "
                'probably a missing / misconfigured LDAP property mapping or'
                'using the wrong version of Products.LDAPUserFolder.'
            )

        impersonate_as = fake_sid or real_sid

        if not impersonate_as:
            raise OneoffixxConfigurationException('No fake_sid configured and LDAP did not provide one!')

        timestamp = str(int(time()))

        checksum = sha256()
        checksum.update(impersonate_as)
        checksum.update('+')
        checksum.update(timestamp)
        checksum.update('+')
        checksum.update(preshared_key)

        grant_type = 'urn:oneoffixx:oauth2:impersonate'
        # There was a bug in the initial implementation of the Oneoffixx
        # backend where they ended up requiring the grant type to be doubly URL
        # encoded - we decided to leave this in as a registry configuration in
        # case they ever fix it
        if api.portal.get_registry_record('double_encode_bug', interface=IOneoffixxSettings):
            grant_type = urllib.quote_plus(grant_type)
        data = {
            'grant_type': grant_type,
            'scope': api.portal.get_registry_record(
                'scope', interface=IOneoffixxSettings),
            'client_id': client_id,
            'client_secret': client_secret,
            'impersonateAs': impersonate_as,
            'timestamp': timestamp,
            'hash': checksum.hexdigest().upper(),
            }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            response = self.session.post(url, headers=headers, data=data)
            response.raise_for_status()
            access_token = response.json().get('access_token')
            if access_token:
                return access_token
            else:
                raise OneoffixxBackendException('Unable to fetch an OAUTH2 grant from Oneoffixx.', response.text)
        except requests.HTTPError as error:
            raise OneoffixxBackendException('Unable to fetch an OAUTH2 grant from Oneoffixx.', response.text, error)

    def refresh_access_token(self, invalidate=False):
        if invalidate:
            ram.global_cache.invalidate(oneoffixx_access_token_cachekey())
        self.session.headers.update({'Authorization': ' '.join(('Bearer', self.get_oneoffixx_access_token()))})

    @ram.cache(oneoffixx_templatelibrary_id_cachekey)
    def get_oneoffixx_templatelibrary_id(self):
        try:
            url = u'/'.join((self.get_oneoffixx_webservice_url(), 'TenantInfo'))
            response = self.session.get(url)
            response.raise_for_status()
            templatelibrary_id = response.json()[0].get('datasources')[0].get('id')
        except requests.HTTPError as error:
            if response.status_code == 401:
                self.refresh_access_token(invalidate=True)
                response = self.session.get(url)
                response.raise_for_status()
                templatelibrary_id = response.json()[0].get('datasources')[0].get('id')
            else:
                raise OneoffixxBackendException(
                    'Unable to fetch the template library id from Oneoffixx.',
                    response.text,
                    error,
                )
        return templatelibrary_id

    @ram.cache(oneoffixx_template_groups_cachekey)
    def get_oneoffixx_template_groups(self):
        templatelibrary_id = self.get_oneoffixx_templatelibrary_id()
        url = u'/'.join((
            self.get_oneoffixx_webservice_url(),
            u'{}'.format(templatelibrary_id),
            u'TemplateLibrary',
            u'TemplateGroups',
        ))
        try:
            response = self.session.get(url)
            response.raise_for_status()
            template_groups = response.json()
        except requests.HTTPError as error:
            if response.status_code == 401:
                self.refresh_access_token(invalidate=True)
                response = self.session.get(url)
                response.raise_for_status()
                template_groups = response.json()
            else:
                raise OneoffixxBackendException('Unable to fetch the template groups from Oneoffixx.', response.text, error)
        return template_groups

    @ram.cache(oneoffixx_favorites_cachekey)
    def get_oneoffixx_favorites(self):
        templatelibrary_id = self.get_oneoffixx_templatelibrary_id()
        url = u'/'.join((
            self.get_oneoffixx_webservice_url(),
            u'{}'.format(templatelibrary_id),
            u'TemplateLibrary',
            u'TemplateFavorites',
        ))
        try:
            response = self.session.get(url)
            response.raise_for_status()
            favorites = response.json()
        except requests.HTTPError as error:
            if response.status_code == 401:
                self.refresh_access_token(invalidate=True)
                response = self.session.get(url)
                response.raise_for_status()
                favorites = response.json()
            else:
                raise OneoffixxBackendException('Unable to fetch the favorites from Oneoffixx.', response.text, error)
        return favorites
