# -*- coding: utf-8 -*-
"""
addonpr pullrequest module

       Copyright (C) 2012-2013 Team XBMC
       http://www.xbmc.org

   This Program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2, or (at your option)
   any later version.

   This Program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; see the file LICENSE.  If not, see
   <http://www.gnu.org/licenses/>.

This module defines the main functions to parse and
process pull requests.
"""
import os
import imaplib
import email
import re
import ConfigParser
import tempfile
import shutil
import xml.etree.ElementTree as ET
from addonpr import command

PULL_RE = re.compile(r"""
    \[(\w+)[\s\-]*pull\]
    """, re.VERBOSE | re.IGNORECASE)

ADDON_RE = re.compile(r"""
    ^[\s\*]*addon[\s:\-]*([\w\.\-]+)\s*
    ^[\s\*]*version[\s:\-]*([\d\.]+)\s*
    ^[\s\*]*url[\s:\-]*([\w\.@:\/\-]+)\s*
    ^[\s\*]*(?:revision|tag)[\s:\-]*([\w\.]+)\s*
    (?:[\s\*]*branch[\s:\-]*.*?\s*)?
    ^[\s\*]*xbmc\s+version[\s:\-]*([\w\,\/\ ]+)
    """, re.VERBOSE | re.MULTILINE)


def get_pull_type(text):
    """Return the pull type"""
    m = PULL_RE.search(text)
    if m:
        pull_type = m.group(1)
    else:
        pull_type = 'unknown'
    return pull_type.lower()


def parse_message(subject, request):
    """Return a list of pull requests

    Each pull request is a dictionary
    """
    pull_requests = []
    pull_type = get_pull_type(subject)
    for match in ADDON_RE.findall(request):
        addon, addon_version, url, revision, xbmc_version = match
        xbmc_branches = [branch for branch in re.split('\W+', xbmc_version) if branch
                            and branch != 'and']
        for xbmc_branch in xbmc_branches:
            pull_requests.append({'addon': addon,
                                  'addon_version': addon_version,
                                  'url': url,
                                  'revision': revision,
                                  'xbmc_branch': xbmc_branch,
                                  'pull_type': pull_type})
    if not pull_requests:
        print "No match found..."
    else:
        print "OK!"
    return pull_requests


def do_pr(addon, addon_version, url, revision, xbmc_branch, pull_type,
          git_parent_dir, tmp_dir):
    print 'Processing %s (%s) pull request for %s...' % (addon,
        addon_version, xbmc_branch)
    # Pull the addon in a temporary directory
    os.chdir(tmp_dir)
    try:
        getattr(command, pull_type + '_pull')(addon, url, revision)
    except AttributeError:
        print 'Unknown pull request type: %s. Aborting.' % pull_type
        return
    # Check the addon type
    addon_parser = AddonParser(addon)
    addon_type = addon_parser.get_type()
    git_dir = os.path.join(git_parent_dir, addon_type + 's')
    try:
        os.chdir(git_dir)
    except OSError as e:
        print e
        return
    command.run('git checkout -f %s' % xbmc_branch)
    if os.path.isdir(addon):
        command.run('git rm -rfq %s' % addon)
        msg = '[%s] updated to version %s' % (addon, addon_version)
    else:
        msg = '[%s] initial version (%s) thanks to %s' % (addon,
                    addon_version, addon_parser.get_author())
    shutil.move(os.path.join(tmp_dir, addon), addon)
    command.run('git add %s' % addon)
    command.run('git commit -m "%s"' % msg)


class AddonParser(object):
    """Class used to parse the addon.xml"""

    def __init__(self, addon_path):
        tree = ET.parse(os.path.join(addon_path, 'addon.xml'))
        self.root = tree.getroot()

    def get_id(self):
        """Return the addon id"""
        return self.root.get('id')

    def get_author(self):
        """Return the addon author"""
        return self.root.get('provider-name')

    def get_extension_type(self):
        """Return the addon type of extension"""
        return [ext.get('point') for ext in self.root.iter('extension')
                         if ext.get('point') != 'xbmc.addon.metadata'][0]

    def get_type(self):
        """Return the addon type"""
        ext_type = self.get_extension_type()
        if ext_type == 'xbmc.gui.skin':
            return 'skin'
        elif ext_type == 'xbmc.gui.webinterface':
            return 'webinterface'
        elif ext_type.startswith('xbmc.metadata.scraper'):
            return 'scrapers'
        elif ext_type == 'xbmc.python.pluginsource' and not self.get_id().startswith('script'):
            return 'plugin'
        else:
            return 'script'


class Parser(object):

    def __init__(self, conf, mail=None, filename=None, interactive=False, **kwargs):
        self.mail_url = mail
        self.filename = filename
        self.interactive = interactive
        self.kwargs = kwargs
        config = ConfigParser.ConfigParser()
        config.read(os.path.expanduser(conf))
        self.mail = dict(config.items('mail'))
        self.git = dict(config.items('git'))

    def get_pr_from_kwargs(self):
        return [self.kwargs]

    def get_pr_from_file(self):
        with open(self.filename, 'rt') as f:
            msg = f.read()
            pull_requests = parse_message(msg, msg)
        return pull_requests

    def get_pr_from_mail(self):
        pull_requests = []
        M = imaplib.IMAP4_SSL(self.mail['server'],
                              self.mail['port'])
        M.login(self.mail['username'],
                self.mail['password'])
        if self.mail_url:
            # Get the thread id from url
            hexid = self.mail_url.split('/')[-1]
            thrid = int(hexid, 16)
            # Search by thread id
            status, count = M.select('inbox', readonly=True)
            typ, data = M.search(None, '(X-GM-THRID "%d")' % thrid)
            # There might be several messages in the thread
            # Take only the last one
            msg_ids = data[0].split()[-1:]
        else:
            # Search by label
            status, count = M.select(self.mail['label'], readonly=True)
            typ, data = M.search(None, 'ALL')
            msg_ids = data[0].split()
        for num in msg_ids:
            typ, msg_data = M.fetch(num, '(RFC822)')
            msg = email.message_from_string(msg_data[0][1])
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    payload = part.get_payload(decode=True)
                    # Only first part should contain interesting information
                    break
            print 'Parsing %s...' % msg['subject'],
            pull_requests.extend(parse_message(msg['subject'], payload))
        M.close()
        M.logout()
        return pull_requests

    def get_pr(self):
        if self.filename:
            pull_requests = self.get_pr_from_file()
        elif self.kwargs:
            pull_requests = self.get_pr_from_kwargs()
        else:
            pull_requests = self.get_pr_from_mail()
        return pull_requests

    def process(self):
        # Create a temporary directory
        tmp_dir = tempfile.mkdtemp()
        for pr in self.get_pr():
            if self.interactive:
                answer = raw_input('Process %s (%s) pull request for %s (y/N)? ' % (pr['addon'],
                             pr['addon_version'], pr['xbmc_branch']))
            else:
                answer = 'y'
            if answer.lower() in ('y', 'yes'):
                do_pr(git_parent_dir=self.git['parent_dir'], tmp_dir=tmp_dir, **pr)
        shutil.rmtree(tmp_dir)
