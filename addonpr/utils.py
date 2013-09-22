# -*- coding: utf-8 -*-
"""
addonpr utils module

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

This module defines some utility functions.
"""
import os
import ConfigParser
import logging
from addonpr import command, addonparser


logger = logging.getLogger(__name__)


def clean_repo(conf, xbmc_branch, addon_type):
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser(conf))
    try:
        git_parent_dir = config.get('git', 'parent_dir')
    except ConfigParser.NoSectionError:
        logger.warning('No git parent_dir defined. Using "."')
        repo = "."
    else:
        repo = os.path.join(git_parent_dir, addon_type)
    os.chdir(repo)
    command.run('git checkout -qf %s' % xbmc_branch)
    for addon_path in os.listdir("."):
        if addon_path.startswith("."):
            continue
        addon = addonparser.Addon(addon_path)
        if addon.is_broken():
            logging.debug("{} is broken".format(addon.addon_id))
            if addon.is_last_commit_older_than(days=182):
                logging.info("Removing {} (broken for more than 6 months)".format(addon.addon_id))
                command.run('git rm -rf {}'.format(addon.addon_id))
                msg = '[%s] removed (broken for more than 6 months)' % addon.addon_id
                command.run('git commit -m "%s"' % msg)
