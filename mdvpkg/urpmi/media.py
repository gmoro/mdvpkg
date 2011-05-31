##
## Copyright (C) 2010-2011 Mandriva S.A <http://www.mandriva.com>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##
## Author(s): Eugeni Dodonov <eugeni@mandriva.com>
##            J. Victor Martins <jvdm@mandriva.com>
##
"""Class for accessing urpmi media data."""


import os.path
import re
import gzip
import gobject


class UrpmiMedia(gobject.GObject):
    """Provide access to a urpmi media data."""

    def __init__(self, name, update, ignore,
                 data_dir='/var/lib/urpmi',
                 key='',
                 compressed=True):
        self.name = name
        self.ignore = ignore
        self.update = update
        self.key = key
        if compressed:
            self._open = gzip.open
        else:
            self._open = open
        self._hdlist_path = os.path.join(
            data_dir,
            '%s/synthesis.hdlist.cz' % name
        )

        # name-version-release[disttagdistepoch].arch regexp:

        # FIXME This is a ugly hack.  Some packages comes with
        #       disttag/distepoch in their file names, separated by
        #       '-'.  And synthesis provides NVRA information in the
        #       rpm file name.  So we check if <release> starts with
        #       'm' for 'mdv' (our current disttag).

        self._nvra_re = re.compile('^(?P<name>.+)-'
                                       '(?P<version>[^-]+)-'
                                       '(?P<release>[^m].*)\.'
                                       '(?P<arch>.+)$')
        self._cap_re = re.compile('^(?P<name>[^[]+)'
                                      '(?:\[\*])*(?:\[(?P<cond>[<>=]*)'
                                      ' *(?P<ver>.*)])?')

    def list(self):
        """Open the hdlist file and yields package data in it."""
        with self._open(self._hdlist_path, 'r') as hdlist:
            pkg = {}
            for line in hdlist:
                fields = line.rstrip('\n').split('@')[1:]
                tag = fields[0]
                if tag == 'info':
                    (pkg['name'],
                     pkg['version'],
                     pkg['release'],
                     pkg['arch']) = self.parse_rpm_name(fields[1])
                    for (i, field) in enumerate(('epoch', 'size', 'group')):
                        pkg[field] = fields[2 + i]
                    yield pkg
                    pkg = {}
                elif tag == 'summary':
                    pkg['summary'] = fields[1]
                elif tag in ('requires', 'provides', 'conflict',
                                   'obsoletes'):
                    pkg[tag] = self._parse_capability_list(fields[1:])

    def parse_rpm_name(self, name):
        """Return (name, version, release, arch) tuple from a rpm
        package name.

        Handle both names with and without
        {release}-{disttag}{distepoch}.
        """
        match = self._nvra_re.match(name)
        if not match:
            raise ValueError, 'Malformed RPM name: %s' % name

        release = match.group('release')
        if release.find('-') != -1:
            release = release.split('-')[0]

        return (match.group('name'),
                match.group('version'),
                release,
                match.group('arch'))

    def _parse_capability_list(self, cap_str_list):
        """Parse a list of capabilities specification string."""
        cap_list = []
        for cap_str in cap_str_list:
            m = self._cap_re.match(cap_str)
            if m is None:
                continue    # ignore malformed names
            cap_list.append({ 'name': m.group('name'),
                              'condition': m.group('cond'),
                              'version': m.group('ver') })
        return tuple(cap_list)
