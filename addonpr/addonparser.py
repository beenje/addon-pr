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
from PIL import Image


logger = logging.getLogger(__name__)


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


class AddonVersion(object):
    """Class to represent and compare addon versions"""

    version_re = re.compile(r'^(\d+)\.(\d+)(?:\.(\d+))?$',
                            re.VERBOSE)

    def __init__(self, vstring):
        self._parse(vstring)

    def _parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError("invalid version number '%s'" % vstring)
        (major, minor, patch) = match.groups()
        if patch is None:
            logger.warning('Invalid frodo version number "%s"', vstring)
            self.version = (major, minor)
        else:
            self.version = (major, minor, patch)

    def __str__(self):
        return '.'.join(self.version)

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = AddonVersion(other)
        return cmp(self.version, other.version)


class AddonCheck(object):
    """Class to run addon tests"""

    def __init__(self, addon_path, addon_version, branch):
        self.addon_path = addon_path
        self.addon_version = addon_version
        self.branch = branch
        self.files = self._get_files()
        self.addon = Addon(addon_path)
        self.warnings = 0
        self.errors = 0

    def _warning(self, message):
        self.warnings += 1
        logger.warning(message)

    def _error(self, message):
        self.errors += 1
        logger.error(message)

    def _get_files(self):
        filenames = [os.path.join(root, name)
            for root, dirs, files in os.walk(self.addon_path)
            for name in files]
        return filenames

    def check_addon_xml(self):
        if self.addon_path != self.addon.addon_id:
            self._error("Given addon id doesn't match.")
        if self.addon_version != self.addon.version:
            self._error("Given addon version doesn't match.")
        if 'language' not in self.addon.metadata:
            self._warning('Missing language tag.')

    def check_dependencies(self):
        for dependency in self.addon.dependencies:
            if dependency['addon'] == 'xbmc.python':
                if self.branch == 'frodo':
                    if dependency['version'] != '2.1.0':
                        self._warning('Invalid version: %s' % dependency['version'])
                elif self.branch == 'eden':
                    if dependency['version'] != '2.0':
                        self._warning('Invalid version: %s' % dependency['version'])

    def check_eol(self):
        for filename in self.files:
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                continue
            logger.debug('Checking %s' % filename)
            with open(filename, 'rb') as f:
                for line in f:
                    if line.endswith('\r\n'):
                        self._error('Invalid end-of-line (CRLF) in %s' % filename)
                        break

    def check_addon_structure(self):
        for mandatory in ('addon.xml', 'LICENSE.txt'):
            if not os.path.isfile(os.path.join(self.addon_path, mandatory)):
                self._error('Missing %s file' % mandatory)
        for recommended in ('changelog.txt',):
            if not os.path.isfile(os.path.join(self.addon_path, recommended)):
                self._warning('Missing recommended %s file' % recommended)

    def check_forbidden_files(self):
        for filename in self.files:
            if filename.endswith(('.so', '.dll', '.pyo',
                '.exe', '.xbt', '.xpr', 'Thumbs.db')):
                self._error('%s is not allowed' % filename)

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
                self._error('Incorrect icon.png size: %dx%d' % (width, height))
            width, height = self._get_image_size('fanart.jpg')
            #if (width, height) != (0, 0) and width / height != 16 / 9:
            if (width, height) != (0, 0) and not (width, height) in ((1280, 720),
                                                                    (1920, 1080)):
                self._error('Incorrect fanart.jpg aspect ratio: %dx%d' % (width, height))

    def check_forbidden_patterns(self):
        for filename in self.files:
            if filename.endswith('.py'):
                logger.debug('Checking %s' % filename)
                with open(filename, 'rb') as f:
                    for line in f:
                        if 'os.getcwd' in line:
                            self._warning('%s: os.getcwd() is deprecated' % filename)

    def run(self):
        """Run all the check methods and return the numbers of warnings and errors"""
        for attribute in dir(self):
            if attribute.startswith('check_'):
                logger.debug('Running %s' % attribute)
                getattr(self, attribute)()
        return (self.warnings, self.errors)
