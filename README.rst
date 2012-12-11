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
is processed.

To process information from a file::

    $ addon-pr --filename /tmp/foo

The file shall contain the same information as a standard pull request e-mail
(including the subject)::

    [Git Pull] my cool plugin

    *addon -   my.cool.plugin
    *version - 1.1.0
    *url - git://some.where.git
    *revision - a241345a
    *branch - master
    *xbmc version - frodo

All arguments can be passed on the command line (mainly to be used in a
script)::

    $ addon-pr --addon plugin.video.m6groupe --addon_version 1.0.2
    --url git://github.com/beenje/plugin.video.m6groupe.git --revision v1.0.2
    --xbmc_branch eden --pull_type git


Installing
----------

addon-pr requires Python 2.5, 2.6 or 2.7.

To install, run::

    $ pip install addon-pr-x.x.x.tar.gz


Copyright
---------

Copyright (c) 2012-2013 Team XBMC.
See LICENSE for details.
