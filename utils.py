# Copyright (C) 2012, Eduardo Silva <edsiper@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import commands

def execute(header, command, status=True):
    print "[+] %-30s" % (header),
    sys.stdout.flush()

    ret = commands.getstatusoutput(command)
    if ret[0] == 0:
        if status is True:
            print "[OK]"
    else:
        if status is True:
            print "[FAILED]\n"
        print ret[1]
        exit(1)

    return ret
