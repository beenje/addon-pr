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
import logging
from addonpr import command, addonparser
from config import BRANCHES

PULL_RE = re.compile(r"""
    \[(\w+)[\s\-]*pull\]
    """, re.VERBOSE | re.IGNORECASE)

ADDON_RE = re.compile(r"""
    ^[\s\*]*addon[\s:=\-–]*([\w\.\-]+)\s*
    ^[\s\*]*version[\s:=\-–]*([\d\.]+)\s*
    ^[\s\*]*url[\s:=\-–]*([\w\.@:\/\-]+)\s*
    (?:^[\s\*]*(?:revision|tag)[\s:=\-–]*([\w\.\-]+)\s*)?
    (?:[\s\*]*branch[\s:=\-–]*.*?\s*)?
    ^[\s\*]*xbmc\s+version[\s:=\-–]*([\w\,\/\ ]+)
    """, re.VERBOSE | re.MULTILINE)


logger = logging.getLogger(__name__)


def get_pull_type(text):
    """Return the pull type from the subject"""
    m = PULL_RE.search(text)
    if m:
        return m.group(1).lower()
    return None


def parse_message(subject, request):
    """Return a list of pull requests

    Each pull request is a dictionary
    """
    pull_requests = []
    pull_type = get_pull_type(subject)
    if pull_type is None:
        logger.warning('Unknown pull type for "%s". Skipping.', subject)
        return []
    for match in ADDON_RE.findall(request):
        addon_id, addon_version, url, revision, xbmc_version = match
        xbmc_branches = [branch.lower() for branch in re.split('\W+', xbmc_version)
                            if branch and branch != 'and']
        for xbmc_branch in xbmc_branches:
            if xbmc_branch not in BRANCHES:
                logger.warning('Invalid xbmc version: "%s". Skipping.', xbmc_branch)
                continue
            pull_requests.append({'addon_id': addon_id,
                                  'addon_version': addon_version,
                                  'url': url,
                                  'revision': revision,
                                  'xbmc_branch': xbmc_branch,
                                  'pull_type': pull_type})
    if not pull_requests:
        logger.warning('No match found when parsing "%s". Skipping.', subject)
    else:
        logger.info('Parsing "%s"... OK!', subject)
    return pull_requests


def do_pr(addon_id, addon_version, url, revision, xbmc_branch, pull_type,
          git_parent_dir, tmp_dir, force=False):
    logger.info('Processing %s (%s) pull request for %s...', addon_id,
        addon_version, xbmc_branch)
    # Pull the addon in a temporary directory
    os.chdir(tmp_dir)
    try:
        getattr(command, pull_type + '_pull')(addon_id, url, revision)
    except AttributeError:
        logger.error('Unknown pull request type: %s. Aborting.', pull_type)
        return
    # Check the addon
    try:
        addon_check = addonparser.AddonCheck(addon_id,
                xbmc_branch,
                addon_id,
                addon_version,
                git_parent_dir)
    except Exception as e:
        logger.error(e)
        logger.error("Aborting.")
        return
    else:
        (warnings, errors) = addon_check.run()
    if errors > 0:
        if force:
            logger.warning("Error(s) detected. Processing anyway (force=True).")
        else:
            shutil.rmtree(addon_id, ignore_errors=True)
            logger.error("Error(s) detected. Aborting.")
            return
    addon = addon_check.addon
    addon_path = addon_check.addon_path
    if git_parent_dir is None:
        logger.error('Git parent dir not set. Aborting.')
        return
    git_dir = os.path.join(git_parent_dir, addon.addon_type + 's')
    try:
        os.chdir(git_dir)
    except OSError as e:
        logger.error('OSError: %s', e.strerror)
        return
    command.run('git checkout -qf %s' % xbmc_branch)
    if os.path.isdir(addon_id):
        command.run('git rm -rfq %s' % addon_id)
        # Directory might still exist due to files in .gitignore
        shutil.rmtree(addon_id, ignore_errors=True)
        if addon.is_broken():
            msg = '[%s] marked as broken' % addon_id
        else:
            msg = '[%s] updated to version %s' % (addon_id, addon_version)
    else:
        msg = '[%s] initial version (%s) thanks to %s' % (addon_id,
                    addon_version, addon.provider)
    shutil.move(os.path.join(tmp_dir, addon_path), addon_id)
    command.run('git add %s' % addon_id)
    command.run('git commit -m "%s"' % msg)


class Parser(object):

    def __init__(self, conf, mail=None, filename=None, interactive=False, force=False, **kwargs):
        self.mail_url = mail
        self.filename = filename
        self.interactive = interactive
        self.force = force
        self.kwargs = kwargs
        config = ConfigParser.ConfigParser()
        config.read(os.path.expanduser(conf))
        try:
            self.mail = dict(config.items('mail'))
        except ConfigParser.NoSectionError:
            self.mail = None
        try:
            self.git_parent_dir = config.get('git', 'parent_dir')
        except ConfigParser.NoSectionError:
            self.git_parent_dir = None

    def get_pr_from_kwargs(self):
        return [self.kwargs]

    def get_pr_from_file(self):
        with open(self.filename, 'rt') as f:
            msg = f.read()
            pull_requests = parse_message(
                    msg.splitlines()[0], msg)
        return pull_requests

    def get_pr_from_mail(self):
        if self.mail is None:
            logger.error('Missing mail section in config. Aborting.')
            return []
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
            if status.lower() == 'no':
                logger.error('Label does not exist. Aborting.')
                return []
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
                answer = raw_input('Process %s (%s) pull request for %s (y/N)? ' % (pr['addon_id'],
                             pr['addon_version'], pr['xbmc_branch']))
            else:
                answer = 'y'
            if answer.lower() in ('y', 'yes'):
                do_pr(git_parent_dir=self.git_parent_dir, force=self.force, tmp_dir=tmp_dir, **pr)
        shutil.rmtree(tmp_dir)
