# -*- coding: utf-8 -*-
"""
addonpr addonparser module

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
"""
from __future__ import division
import os
import re
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from datetime import datetime, timedelta
from PIL import Image
from config import BRANCHES, DEPENDENCIES, STRINGS_ID
from addonpr import command


logger = logging.getLogger(__name__)


def filter_comments(infile):
    """Generator to filter commented line in a python file"""
    for line in infile:
        # Remove leading and trailing characters
        line = line.strip()
        # Skip blank line
        if line == '':
            continue
        if not line.startswith('#'):
            yield line


class Addon(object):
    """Class used to parse the addon.xml"""

    def __init__(self, addon_path):
        tree = ET.parse(os.path.join(addon_path, 'addon.xml'))
        self._root = tree.getroot()
        self.addon_id = self._root.get('id')
        self.name = self._root.get('name')
        self.version = AddonVersion(self._root.get('version'))
        self.provider = self._root.get('provider-name')
        self.addon_type = None
        self.dependencies = []
        self.extensions = []
        self.metadata = {}
        self._parse()

    def _parse(self):
        """Parse the addon.xml"""
        requires = self._root.find('requires')
        self.dependencies = [elt.attrib for elt in list(requires)]
        for ext in self._root.iter('extension'):
            if ext.get('point') == 'xbmc.addon.metadata':
                self.metadata = self._get_metadata(ext)
            else:
                self.extensions.append(self._get_extension(ext))
        self.addon_type = self._get_addon_type()

    def _get_extension(self, ext):
        extension = ext.attrib
        try:
            extension['provides'] = ext.find('provides').text
        except AttributeError:
            extension['provides'] = ''
        return extension

    def _get_metadata(self, ext):
        metadata = {}
        for elt in list(ext):
            tag = elt.tag
            if tag in ('summary', 'description', 'disclaimer'):
                if tag not in metadata:
                    metadata[tag] = {}
                try:
                    metadata[tag][elt.attrib['lang']] = elt.text
                except KeyError:
                    metadata[tag]['en'] = elt.text
            else:
                metadata[tag] = elt.text
        return metadata

    def _get_addon_type(self):
        """Return the addon type"""
        for extension in self.extensions:
            extension_type = extension['point']
            if extension_type == 'xbmc.gui.skin':
                return 'skin'
            elif extension_type == 'xbmc.gui.webinterface':
                return 'webinterface'
            elif extension_type.startswith('xbmc.metadata.scraper'):
                return 'scraper'
            elif (extension_type == 'xbmc.python.pluginsource' and not
                    self.addon_id.startswith('script')):
                return 'plugin'
        else:
            return 'script'

    def is_broken(self):
        """Return True if the addon is broken"""
        return 'broken' in self.metadata

    def get_extension_points(self):
        """Return a list of extension points (excluding metadata)"""
        return [extension['point'] for extension in self.extensions]

    def last_commit_date(self):
        """Return the last commit date"""
        timestamp = command.run(
            'git log -n1 --format="%ct" {}'.format(
            os.path.join(self.addon_id, 'addon.xml')))
        return datetime.fromtimestamp(float(timestamp))

    def is_last_commit_older_than(self, days):
        age = datetime.now() - self.last_commit_date()
        return age > timedelta(days=days)


class AddonVersion(object):
    """Class to represent and compare addon versions"""

    version_re = re.compile(r'^(\d+)\.(\d+)(?:\.(\d+))?$',
                            re.VERBOSE)

    def __init__(self, vstring):
        self._parse(vstring)
        self.length = len(self.version)

    def _parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError("invalid version number '%s'" % vstring)
        (major, minor, patch) = match.groups()
        if patch is None:
            self.version = tuple(map(int, [major, minor]))
        else:
            self.version = tuple(map(int, [major, minor, patch]))

    def __str__(self):
        return '.'.join(map(str, self.version))

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = AddonVersion(other)
        return cmp(self.version, other.version)


class AddonCheck(object):
    """Class to run addon tests"""

    def __init__(self, addon_path, xbmc_branch, addon_id=None,
            addon_version=None, parent_dir=None):
        self.addon_id = addon_id
        self.addon_path = self._get_addon_path(addon_path)
        self.xbmc_branch = xbmc_branch
        self.addon_version = addon_version
        self.parent_dir = parent_dir
        self.files = self._get_files()
        self.addon = Addon(addon_path)
        self.warnings = 0
        self.errors = 0

    def _warning(self, message, *args, **kwargs):
        self.warnings += 1
        logger.warning(message, *args, **kwargs)

    def _error(self, message, *args, **kwargs):
        self.errors += 1
        logger.error(message, *args, **kwargs)

    def _get_files(self):
        filenames = [os.path.join(root, name)
            for root, dirs, files in os.walk(self.addon_path)
            for name in files]
        return filenames

    def _get_addon_path(self, addon_path):
        if self.addon_id and os.path.isdir(os.path.join(addon_path, self.addon_id)):
            addon_path = os.path.join(addon_path, self.addon_id)
            logger.debug('Switched to addon subdir: %s', addon_path)
        return addon_path

    def _checkout_branch(self, repo):
        """Checkout the proper branch in repo"""
        current_dir = os.getcwd()
        try:
            os.chdir(repo)
        except OSError as e:
            logger.error('OSError: %s', e.strerror)
            return
        command.run('git checkout -qf %s' % self.xbmc_branch)
        os.chdir(current_dir)

    def check_xbmc_version(self):
        if self.xbmc_branch not in BRANCHES:
            self._error('Invalid xbmc version: %s',
                    self.xbmc_branch)

    def check_addon_version(self):
        if self.xbmc_branch == 'frodo':
            if self.addon.version.length != 3:
                self._error('Invalid version %s for frodo. Should be x.y.z.',
                        self.addon.version)

    def check_addon_xml(self):
        if self.addon_id is not None and self.addon_id != self.addon.addon_id:
            self._error("Given addon id doesn't match %s",
                    self.addon.addon_id)
        if self.addon_version is not None and self.addon_version != self.addon.version:
            self._error("Given addon version doesn't match %s",
                    self.addon.version)
        if 'language' not in self.addon.metadata:
            self._error('Missing language tag')

    def check_optional_info(self):
        for tag in ['license', 'forum', 'website', 'source', 'email']:
            if tag not in self.addon.metadata:
                self._warning('Missing optional %s tag' % tag)

    def check_dependencies(self):
        xbmc_dependencies = DEPENDENCIES[self.xbmc_branch]
        if self.parent_dir is not None:
            # Prepare the repositories for dependencies check
            for repo in ['plugins', 'scripts']:
                self._checkout_branch(os.path.join(self.parent_dir, repo))
        for dependency in self.addon.dependencies:
            dependency_id = dependency['addon']
            try:
                dependency_version = dependency['version']
            except KeyError:
                logger.debug('Skipping %s dependency (no version specified)',
                        dependency_id)
                continue
            if dependency_id in xbmc_dependencies:
                if dependency_version != xbmc_dependencies[dependency_id]:
                        self._error('Invalid version for %s (%s != %s)',
                            dependency_id,
                            dependency_version,
                            xbmc_dependencies[dependency_id])
                else:
                    logger.debug('%s dependency OK (%s)',
                                dependency_id,
                                dependency_version)
            elif self.parent_dir is not None:
                # Try to check plugins and scripts dependencies
                for repo in ['plugins', 'scripts']:
                    dependency_dir = os.path.join(self.parent_dir, repo, dependency_id)
                    if os.path.isdir(dependency_dir):
                        dependency_addon = Addon(dependency_dir)
                        if dependency_version > dependency_addon.version:
                            self._error('Invalid version for %s (%s > %s)',
                                dependency_id,
                                dependency_version,
                                dependency_addon.version)
                        else:
                            logger.debug('%s dependency OK (%s <= %s)',
                                dependency_id,
                                dependency_version,
                                dependency_addon.version)
                        break
                else:
                    logger.debug('Skipping dependency %s (not found in plugins or scripts)',
                            dependency_id)
            else:
                logger.debug('Skipping dependency %s (no parent_dir given)',
                        dependency_id)

    def check_addon_structure(self):
        for mandatory in ('addon.xml', 'LICENSE.txt'):
            if not os.path.isfile(os.path.join(self.addon_path, mandatory)):
                self._error('Missing %s file', mandatory)
        for recommended in ('changelog.txt',):
            if not os.path.isfile(os.path.join(self.addon_path, recommended)):
                self._warning('Missing recommended %s file', recommended)

    def check_forbidden_files(self):
        for filename in self.files:
            if filename.endswith(('.so', '.dll', '.pyo', '.pyc',
                '.exe', '.xbt', '.xpr', 'Thumbs.db', '.DS_Store')):
                self._error('%s is not allowed', filename)

    def _get_image_size(self, picture):
        try:
            img = Image.open(os.path.join(self.addon_path, picture))
        except IOError:
            logger.debug("Picture %s doesn't exist" % picture)
            return (0, 0)
        return img.size

    def check_images(self):
        # module are not visible and don't require any images
        if 'xbmc.python.module' in self.addon.get_extension_points():
            logger.debug('No check done on images for %s' % self.addon.addon_id)
        else:
            width, height = self._get_image_size('icon.png')
            if (width, height) != (256, 256):
                self._error('Incorrect icon.png size: %dx%d', width, height)
            width, height = self._get_image_size('fanart.jpg')
            #if (width, height) != (0, 0) and width / height != 16 / 9:
            if (width, height) != (0, 0) and not (width, height) in ((1280, 720),
                                                                    (1920, 1080)):
                self._error('Incorrect fanart.jpg aspect ratio: %dx%d', width, height)

    def check_forbidden_patterns(self):
        for filename in self.files:
            if filename.endswith('.py'):
                logger.debug('Checking %s' % filename)
                with open(filename, 'rb') as f:
                    for line in filter_comments(f):
                        if 'os.getcwd' in line:
                            self._warning('%s: os.getcwd() is deprecated', filename)
                        if 'PLAYER_CORE' in line:
                            self._warning('{}: setting PLAYER_CORE_* is deprecated'.format(filename))
                        if 'executehttpapi' in line:
                            self._warning('{}: executehttpapi is deprecated'.format(filename))

    def get_po_strings_id(self, filename):
        """Generator that returns all strings id from a po file"""
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("msgctxt"):
                    # msgctxt "#30301"
                    try:
                        yield int(line.split()[1][2:-1])
                    except ValueError:
                        self._warning('{}: has not integer string ID: {}'.format(filename, line))

    def get_xml_strings_id(self, filename):
        """Generator that returns all strings id from a xml file"""
        try:
            tree = ET.parse(filename)
        except ET.ParseError as e:
            self._error('Parse error in {}: {}'.format(filename, e))
            raise StopIteration
        for elt in tree.getroot():
            yield int(elt.get('id'))

    def get_strings_id(self, filename):
        """Generator that returns all strings id from file"""
        file_type = filename.split('.')[-1]
        try:
            return getattr(self, 'get_{}_strings_id'.format(file_type))(filename)
        except AttributeError:
            logger.warning('Unknown strings file type: {}'.format(file_type))
            return []

    @staticmethod
    def is_valid_string_id(string_id, addon_type='all'):
        try:
            min_id, max_id = STRINGS_ID[addon_type]
        except KeyError:
            min_id, max_id = STRINGS_ID['all']
        return min_id <= string_id <= max_id

    def check_strings_id(self):
        for filename in self.files:
            if filename.endswith(('strings.xml', 'strings.po')):
                logger.debug('Checking %s' % filename)
                for string_id in self.get_strings_id(filename):
                    if not self.is_valid_string_id(string_id, 'all'):
                        self._error('Invalid string id {}'.format(string_id))
                    elif not self.is_valid_string_id(string_id, self.addon.addon_type):
                        self._warning('Invalid string id {} for {}'.format(
                            string_id, self.addon.addon_type))

    def check_xml_encoding(self):
        for filename in self.files:
            if filename.endswith('.xml'):
                try:
                    dom = minidom.parse(filename)
                except ExpatError as e:
                    self._error('{}: {}'.format(filename, e))
                else:
                    if not dom.encoding:
                        self._error('No xml encoding specified in {}'.format(filename))
                    else:
                        logger.debug('{} encoding: {}'.format(filename, dom.encoding))

    def check_print_statements(self):
        for filename in self.files:
            if filename.endswith('.py'):
                logger.debug('Checking %s' % filename)
                with open(filename, 'rb') as f:
                    for line in filter_comments(f):
                        if 'print' in line:
                            self._warning('%s: print statement should be replaced with xbmc.log()', filename)
                            logger.debug(line)
                            # We need only one warning per file, so exit the
                            # loop
                            break

    def check_language_dirs(self):
        language_dir = os.path.join(self.addon_path, 'resources', 'language')
        if not os.path.exists(language_dir):
            return
        for dirname in os.listdir(language_dir):
            logger.debug('Checking language dir {}'.format(dirname))
            # The language dir can be made of several words:
            # Chinese (Traditional)
            # Checking only the first word should be good enough
            first_word = dirname.split()[0]
            if first_word != first_word.capitalize():
                self._warning('Language dir {} should be capitalized'.format(
                    dirname))

    def check_extension_point(self):
        if 'xbmc.addon.repository' in self.addon.get_extension_points():
            self._error('xbmc.addon.repository extension point is not allowed')

    def run(self):
        """Run all the check methods and return the numbers of warnings and errors"""
        logger.info('Checking %s', self.addon_path)
        for attribute in dir(self):
            if attribute.startswith('check_'):
                logger.debug('Running %s' % attribute)
                getattr(self, attribute)()
        logger.info('%d warning(s) and %d error(s) found', self.warnings,
                self.errors)
        return (self.warnings, self.errors)
