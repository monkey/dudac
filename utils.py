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

ANSI_BOLD    = "\033[1m"
ANSI_CYAN    = "\033[36m"
ANSI_MAGENTA = "\033[35m"
ANSI_RED     = "\033[31m"
ANSI_YELLOW  = "\033[33m"
ANSI_BLUE    = "\033[34m"
ANSI_GREEN   = "\033[32m"
ANSI_WHITE   = "\033[37m"
ANSI_RESET   = "\033[0m"

def execute(header, command, status=True):
    print "[+] %-30s" % (header),
    sys.stdout.flush()

    ret = commands.getstatusoutput(command)
    if ret[0] == 0:
        if status is True:
            print "[OK]"
        if ret[1].find('warning') > 0:
            print ANSI_BOLD + ANSI_RED + "--- Compilation Warnings ---" + ANSI_RESET

            lines = ret[1].split('\n')
            for l in lines:
                if l.find('warning') > 0:
                    print ANSI_GREEN + l + ANSI_RESET

            print ANSI_BOLD + ANSI_RED + "--- * --- * --- * --- * ---"
            print ANSI_RESET
    else:
        if status is True:
            print "[FAILED]\n"
        print "Error Command: '%s'\n--" % command
        print ret[1]
        exit(1)

    return ret

def print_msg(msg, status = 0):
    print "[+] %-30s" % (msg),

    if status == 0:
        print "[FAILED]\n"
    else:
        print "[OK]"

def print_bold(msg):
    print ANSI_BOLD + msg + ANSI_RESET

def print_color(msg, color, is_bold=False):
    text = color + msg + ANSI_RESET
    if is_bold is True:
        text = ANSI_BOLD + text

    print text
