# -*- coding: utf-8 -*-
"""
addonpr config module

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

BRANCHES = ['eden', 'frodo', 'gotham']
DEPENDENCIES = {
    'eden': {'xbmc.python': '2.0'
            },
    'frodo': {'xbmc.addon': '12.0.0',
              'xbmc.core': '0.1.0',
              'xbmc.gui': '4.0.0',
              'xbmc.json': '6.0.0',
              'xbmc.metadata': '2.1.0',
              'xbmc.python': '2.1.0'
             },
    'gotham': {'xbmc.addon': '12.0.0',
               'xbmc.core': '0.1.0',
               'xbmc.gui': '5.0.1',
               'xbmc.json': '6.6.0',
               'xbmc.metadata': '2.1.0',
               'xbmc.python': '2.14.0'
              }

    }
STRINGS_ID = {
    'plugin': (30000, 30999),
    'skin': (31000, 31999),
    'script': (32000, 32999),
    'all': (30000, 33999),
    }
