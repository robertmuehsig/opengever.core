from ftw.testbrowser import browser
from ftw.testbrowser.pages import factoriesmenu
from plone.app.testing.interfaces import SITE_OWNER_NAME
from plone.app.testing.interfaces import SITE_OWNER_PASSWORD
from threading import Thread
from time import sleep
import json
import os
import re
import signal
import socket
import subprocess
import sys
import unittest
import xmlrpclib


class TestserverSelftest(object):
    """The selftest tests that the testserver works properly.
    The selftest is not a regular unittest so that it does not run together
    with the regular tests. It is too time consuming.
    """

    def __init__(self):
        # The TestserverSelftest should not be executed by the regular testserver
        # and therefore should not subclass TestserverSelftest.
        # Lets do a hack so that we have assert methods anyway.
        case = unittest.TestCase('__init__')
        case.maxDiff = None
        self.assertIn = case.assertIn
        self.assertNotIn = case.assertNotIn
        self.assertDictContainsSubset = case.assertDictContainsSubset
        self.assertMultiLineEqual = case.assertMultiLineEqual

    def __call__(self):
        os.environ['ZSERVER_PORT'] = os.environ.get('ZSERVER_PORT', '60601')
        self.plone_url = 'http://localhost:{}/plone/'.format(os.environ['ZSERVER_PORT'])
        os.environ['TESTSERVER_CTL_PORT'] = os.environ.get('PORT1', '60602')

        self.controller_proxy = xmlrpclib.ServerProxy('http://localhost:{}'.format(
            os.environ['TESTSERVER_CTL_PORT']))
        print ansi_green('> STARTING TESTSERVER')
        self.start_testserver()
        try:
            self.wait_for_testserver()
            print ansi_green('> TESTSERVER IS READY')
            print ansi_green('> PERFORMING SELFTEST')
            self.selftest()
        finally:
            print ansi_green('> STOPPING TESTSERVER')
            self.stop_testserver()

    def selftest(self):
        with browser:
            self.testserverctl('zodb_setup')
            with browser.expect_unauthorized():
                browser.open(self.plone_url)

            browser.fill({'Benutzername': SITE_OWNER_NAME,
                          'Passwort': SITE_OWNER_PASSWORD}).submit()

            browser.replace_request_header('Accept', 'application/json')
            browser.replace_request_header('Content-Type', 'application/json')

            data = {'@type': 'opengever.dossier.businesscasedossier',
                    'title': u'Gesch\xe4ftsdossier',
                    'responsible': 'kathi.barfuss'}
            browser.open(self.plone_url + 'ordnungssystem/rechnungspruefungskommission',
                         method='POST',
                         data=json.dumps(data))
            dossier_url = browser.json['@id']

            browser.open(dossier_url)
            self.assertDictContainsSubset(
                {u'title': u'Gesch\xe4ftsdossier',
                 u'modified': u'2018-11-22T14:29:33+00:00',
                 u'UID': u'testserversession000000000000001',
                 u'email': u'99001@example.org'},
                browser.json)

            document_url = (
                self.plone_url
                + 'ordnungssystem/fuehrung/vertraege-und-vereinbarungen/dossier-1/document-12')
            browser.open(document_url)

            expected_preview_url = '''
http://bumblebee/YnVtYmxlYmVl/api/v3/resource/local/51d6317494eccc4a73154625a6820cb6b50dc1455eb4cf26399299d4f9ce77b2/preview?access_token=L1I-UGCXCjMaevatBSv-ZLZwypkO9yWkj5cCATieaDI%3D
'''.strip()
            got_preview_url = browser.json['preview_url'].split('&bid')[0]
            self.assertMultiLineEqual(expected_preview_url, got_preview_url)

            self.testserverctl('zodb_teardown')
            self.testserverctl('zodb_setup')

            with browser.expect_http_error(404):
                browser.open(dossier_url)

            self.testserverctl('zodb_teardown')

    def testserverctl(self, *args):
        args = ['bin/testserverctl'] + list(args)
        print ansi_blue('>', *args)
        subprocess.check_call(args)

    def start_testserver(self):
        """Start the testserver in a subprocess controlled by a separate thread.
        """
        args = ['bin/testserver']
        print ansi_blue('>', *args)
        self.testserver_process = subprocess.Popen(args)
        self.testserver_thread = Thread(target=self.testserver_process.communicate)
        self.testserver_thread.start()

    def wait_for_testserver(self):
        """Block until the testserver is ready.
        """
        timeout_seconds = 60 * 5
        interval = 0.1
        steps = timeout_seconds / interval
        for num in range(int(steps)):
            if self.is_controller_server_ready():
                return
            if num > 300 and num % 300 == 0:
                print ansi_gray('... waiting for testserver to be ready ')
            sleep(interval)

        self.stop_testserver()
        raise Exception('Timeout: testserver did not start in {} seconds'.format(timeout_seconds))

    def stop_testserver(self):
        """Kill the testserver process group.
        It should be killed as group since bin/testserver is a wrapper script,
        creating a subprocess.
        """
        try:
            os.kill(self.testserver_process.pid, signal.SIGINT)
        except KeyboardInterrupt:
            pass
        self.testserver_thread.join()

    def is_controller_server_ready(self):
        """Test whether the controller server is available.
        This indicates that the testserver is ready.
        """
        try:
            self.controller_proxy.listMethods()
        except socket.error:
            return False
        except Exception:
            pass
        return True


def ansi_green(*text):
    text = ' '.join(text)
    if sys.stdout.isatty():
        return '\033[0;32m{}\033[0m'.format(text)
    else:
        return text


def ansi_blue(*text):
    text = ' '.join(text)
    if sys.stdout.isatty():
        return '\033[0;34m{}\033[0m'.format(text)
    else:
        return text


def ansi_gray(*text):
    text = ' '.join(text)
    if sys.stdout.isatty():
        return '\033[0;36m{}\033[0m'.format(text)
    else:
        return text


def selftest():
    TestserverSelftest()()
