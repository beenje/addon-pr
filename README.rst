========
addon-pr
========

addon-pr helps to process XBMC addons pull requests.

Configuration
-------------

Create the following ~/.addon-pr config file::

    [mail]
    server = imap.gmail.com
    port = 993
    username = <username>
    password = <password>
    label = pull_request

    [git]
    # Parent directory of the local clones
    # (plugins, scripts, scrapers, skins...)
    parent_dir = <full path of your local clone(s) parent dir>

To process several e-mails at the same time, you can create a filter
in gmail to apply the label "pull_request" (label shall match the
label defined in your config file) on messages that arrives.
Filter can be something like::

    to:(xbmc-addons@lists.sourceforge.net) subject:pull

Or just manually add the label to the messages you want to process.
Don't forget to remove the label when messages have been processed.


Usage
-----

To process all e-mails with the "pull_request" label::

    $ addon-pr

To ask confirmation before to process each pull request
(interactive mode)::

    $ addon-pr -i

To process one e-mail using the gmail url::

    $ addon-pr --mail https://mail.google.com/mail/#inbox/13b3e93a812f3de0

Note that the id in that url is the thread id. Only last message of the thread
is processed. you don't have to pass the full url, only the thread id is
enough. The mail should still be in your inbox.

To process information from a file::

    $ addon-pr --filename /tmp/foo

The file shall contain the same information as a standard pull request e-mail
(including the subject on the first line)::

    [Git Pull] my cool plugin

    *addon - my.cool.plugin
    *version - 1.1.0
    *url - git://some.where.git
    *revision - a241345a
    *branch - master
    *xbmc version - frodo

All arguments can be passed on the command line (mainly to be used in a
script)::

    $ addon-pr --addon_id plugin.video.m6groupe --addon_version 1.0.2
    --url git://github.com/beenje/plugin.video.m6groupe.git --revision v1.0.2
    --xbmc_branch eden --pull_type git

The addon-pr script can also be used to check your pull request.
If you don't create a config file ~/.addon-pr (or don't define a git parent
dir), you can still pass a file or all arguments to the script (like previously described).
Checks will be run on the addon, but obviously no commit will be done.

The script can as well be used to run checks on a local directory.
Just give the addon path and xbmc branch in arguments::

    $ addon-pr --check --xbmc_branch=frodo /Users/foo/plugin.video.m6groupe


Installing
----------

addon-pr has been tested on OS X with Python 2.7.
It should work without problem on Linux as well.

It requires docopt and pillow. Dependencies will be installed automatically
if you use pip.
virtualenv is recommended.

To install from github, run::

    $ pip install git+git://github.com/beenje/addon-pr.git#egg=addon_pr


Copyright
---------

Copyright (c) 2012-2013 Team XBMC.
See LICENSE for details.
