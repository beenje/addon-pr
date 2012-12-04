# -*- coding: utf-8 -*-
"""
addonpr command module

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
import sys
import shlex
import shutil
import subprocess
import urllib
import zipfile


def run(cmd):
    """Run the shell command and return the result"""
    args = shlex.split(cmd)
    try:
        result = subprocess.check_output(args)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.output)
        sys.exit(e.returncode)
    else:
        return result.strip()


def git_pull(addon, url, revision):
    current_dir = os.getcwd()
    run('git clone "%s" %s' % (url, addon))
    os.chdir(addon)
    run('git checkout "%s"' % revision)
    shutil.rmtree('.git')
    if os.path.isfile('.gitignore'):
        os.remove('.gitignore')
    os.chdir(current_dir)


def svn_pull(addon, url, revision):
    run('svn export "%s" -r "%s" %s' % (url, revision, addon))


def hg_pull(addon, url, revision):
    run('hg clone -r "%s" "%s" %s' % (revision, url, addon))
    shutil.rmtree(os.path.join(addon, '.hg'))
    hgignore = os.path.join(addon, '.hgignore')
    if os.path.exists(hgignore):
        os.remove(hgignore)


def zip_pull(addon, url, revision):
    addon_zip = addon + '.zip'
    urllib.urlretrieve(url, addon_zip)
    zip_file = zipfile.ZipFile(addon_zip)
    zip_file.extractall()
    os.remove(addon_zip)
