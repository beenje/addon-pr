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
import os
import xml.etree.ElementTree as ET


class Addon(object):
    """Class used to parse the addon.xml"""

    def __init__(self, addon_path):
        tree = ET.parse(os.path.join(addon_path, 'addon.xml'))
        self._root = tree.getroot()
        self.addon_id = self._root.get('id')
        self.name = self._root.get('name')
        self.version = self._root.get('version')
        self.provider = self._root.get('provider-name')
        self.addon_type = None
        self.dependencies = []
        self.extension = {}
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
                self.extension = self._get_extension(ext)
        self.addon_type = self._get_addon_type(self.extension['point'])

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

    def _get_addon_type(self, extension_type):
        """Return the addon type"""
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
