#!/usr/bin/env python2

# Copyright (C) 2012-2014, Eduardo Silva <eduardo@monkey.io>
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

import os
import sys
import shutil
import getopt
import datetime
import ConfigParser

from git import GitProject
from utils import *

# Version
DUDAC_VERSION  = "0.31"

# Internal / Protocol
PROTOCOL_HTTPS = 0
PROTOCOL_GIT   = 1

class DudaConfig(ConfigParser.ConfigParser):
    def __init__(self):
        ConfigParser.ConfigParser.__init__(self)

    def open(self, path):
        self.read(path)

    def get_handlers(self):
        return self.sections()

    def get_key(self, handler, key):
        try:
            val = self.get(handler, key)
            return val
        except:
            return None


class Monkey:
    opts = ''
    recent_configure = False
    recent_build = False
    recent_clean = False

    def __init__(self, source_path):
        self.mk_path = source_path
        self.SSL = False

    def configure(self):
        if self.recent_configure is True:
            return

        cpath = os.getcwd()
        os.chdir(self.mk_path)

        # Specify the plugins
        plugins = "liana,duda,auth"

                # If we have SSL enable, we have to replace the transport layer, that means
        # disable Liana and enable the new PolarSSL, later we need to generate
        # certificates and configure everything to make it work properly
        if self.SSL is True:
            plugins += ',polarssl'

        configure = "./configure --debug --disable-plugins='*' --enable-plugins='%s' %s"  % (plugins, self.opts)

        # Run the configure script
        execute("Monkey      : prepare build", configure)

        # Revert to original path
        os.chdir(cpath)
        self.recent_configure = True

    def make_build(self):
        if self.recent_build is True:
            return

        cmd = "make -C %s" % (self.mk_path)
        execute("Monkey      : building", cmd)

        self.recent_build = True

    def make_clean(self):
        if self.recent_clean is True:
            return

        if os.path.exists(self.mk_path + '/Makefile') is False:
            return

        cmd = "make -C %s clean" % (self.mk_path)
        execute("Monkey      : cleaning", cmd)

        self.recent_clean = True

    def system(self, cmd):
        return commands.getstatusoutput(cmd)

    def update_transport_layer(self, t='plain'):
        if t == 'plain':
            pass
        elif t == 'SSL':
            pass

    def version(self):
        bin = self.mk_path + "/bin/monkey -v"
        output = execute(None, bin, False, False, False)
        lines = output[1].split('\n')
        header = lines[0]
        pos = header.find(' v')
        version = header[pos + 2:]
        return ".".join(version.split()[3].split(".")[0:2])

class MonkeyGIT (GitProject):
    def __init__(self, home_path):
        self._home = home_path
        https_repo = 'https://github.com/monkey/monkey.git'
        git_repo   = 'git@github.com:monkey/monkey.git'
        GitProject.__init__(self, 'Monkey', https_repo, git_repo)

    def home(self):
        return self._home

class DudaGIT(GitProject):
    def __init__(self, home_path):
        self._home = home_path
        https_repo = 'https://github.com/monkey/duda.git'
        git_repo   = 'git@github.com:monkey/duda.git'
        GitProject.__init__(self, 'Duda', https_repo, git_repo)

    def home(self):
        return self._home

class Duda:
    # Default configuration directives for Monkey configuration
    # file located under the [SERVER] section
    MCONF_KNOWN = ['Port',
                   'Listen',
                   'Workers',
                   'Timeout',
                   'PidFile',
                   'UserDir',
                   'Indexfile',
                   'HideVersion',
                   'Resume',
                   'User',
                   'KeepAlive',
                   'KeepAliveTimeout',
                   'MaxKeepAliveRequest',
                   'MaxRequestSize',
                   'SymLink',
                   'TransportLayer',
                   'DefaultMimeType']

    def __init__(self):
        self.print_version()
        self.web_service = None
        self.service = None
        self.port = 2001
        self.SSL = False
        self.SSL_default = False
        self.output_stdout = False
        self.api_level = DEFAULT_API_LEVEL
        self.linux_malloc = False
        self.linux_trace = False
        self.jemalloc_stats = False
        self.jemalloc_prof  = False
        self.rebuild_monkey = False
        self.reset_environment = False
        self.load_makefile()

        # Load Environment variables
        self.dudac_home_path  = os.getenv('DUDAC_HOME')
        self.dudac_stage_path = os.getenv('DUDAC_STAGE')

        # Sanitize paths: DUDAC_HOME
        if self.dudac_home_path is None:
            self.dudac_home_path  = '%s/.dudac/' % (os.getenv('USERPROFILE') or os.getenv('HOME'))
        if self.dudac_home_path[-1] != '/':
            self.dudac_home_path += '/'

        # Sanitize paths: DUDAC_STAGE
        if self.dudac_stage_path is None:
            self.dudac_stage_path = self.dudac_home_path + 'stage/'
        if self.dudac_stage_path[-1] != '/':
            self.dudac_stage_path += '/'

        # Set Source paths for Monkey and Duda
        self.mk_home   = self.dudac_home_path + 'monkey/'
        self.duda_home = self.dudac_home_path + 'duda/'

        # Initialize GIT handlers
        self.mk_git   = MonkeyGIT(self.mk_home)
        self.duda_git = DudaGIT(self.duda_home)

        # Instance Monkey handler
        self.monkey  = Monkey(self.dudac_stage_path + 'monkey/')
        self.get_arguments()

        exit(0)

    def load_makefile(self):
        dot = os.path.dirname(os.path.abspath(__file__))
        f = open(os.path.join(dot, "dudac.Make"), "r")
        self.dudac_makefile = f.read()
        f.close

    # This routine read the config.dudac configuration file which is
    # optional inside every web service source code. It specifies the
    # Monkey sources requirements and perform the right setup
    def config_requirements(self):
        ws = os.path.abspath(self.service)
        if not os.path.isdir(ws):
            print "Error: Invalid web service directory"
            exit(1)

        # Check if is an API level
        try:
            api_number = int(self.api_level)
        except:
            api_number = -1

        if api_number > 0:
            version = "dst-%i" % (api_number)
        else:
            version = self.api_level

        mk_version      = version
        mk_https_repo   = None
        mk_git_repo     = None
        duda_version    = version
        duda_https_repo = None
        duda_git_repo   = None

        # Check if the service have a configuration file
        config_file = os.path.abspath("%s/dudac.conf" % (ws))
        if os.path.isfile(config_file) is True:
            # Read the configuration
            config = DudaConfig()
            config.open(config_file)

            for h in config.get_handlers():
                if h == 'MONKEY':
                    # Get key/values
                    mk_version    = config.get_key(h, 'version')
                    mk_https_repo = config.get_key(h, 'https_repo')
                    mk_git_repo   = config.get_key(h, 'git_repo')
                elif h == 'DUDA':
                    duda_version    = config.get_key(h, 'version')
                    duda_https_repo = config.get_key(h, 'https_repo')
                    duda_git_repo   = config.get_key(h, 'git_repo')

        # Configure repos
        self.mk_git.setup(mk_version, mk_https_repo, mk_git_repo)
        self.duda_git.setup(duda_version, duda_https_repo, duda_git_repo)

    def update_framework(self, protocol):
        self.mk_git.set_protocol(protocol)
        self.duda_git.set_protocol(protocol)

        if os.path.exists(self.mk_home):
            self.mk_git.update(self.mk_home)
        else:
            self.mk_git.clone(self.mk_home)

        if os.path.exists(self.duda_home):
            self.duda_git.update(self.duda_home)
        else:
            self.duda_git.clone(self.duda_home)

        # Cleanup and rebuild Monkey
        cpath = os.getcwd()
        os.chdir(self.mk_home)

        self.mk_git.version = self.api_level
        self.mk_git.snapshot()

        self.duda_git.version = self.api_level
        self.duda_git.snapshot()

        self.merge_on_stage()
        self.monkey.configure()

        if os.path.exists("./Makefile"):
            self.monkey.make_clean()

        self.monkey.make_build()
        os.chdir(cpath)

    def merge_on_stage(self):
        # Create archives from repos
        self.mk_git.archive_to(self.dudac_stage_path + '/monkey')
        self.duda_git.archive_to(self.dudac_stage_path + '/monkey/plugins/duda')

        # Tag the content with branch used
        f = open(self.dudac_stage_path + '/monkey/api_level.dudac', 'w')
        f.write(self.mk_git.version + '\n')
        f.close()


    # Enable a plugin on plugins.load file, if the line is commented, it
    # change the status, if it do not exist, it create a new entry at the
    # end
    def enable_plugin(self, monkey_stage, name):
        matched = False
        plugins = monkey_stage + "/conf/plugins.load"
        f = open(plugins, "r")
        lines = f.readlines()
        f.close()

        plugin = 'monkey-%s.so' % (name)

        raw = ""
        for line in lines:
            if line.startswith('    # Load') and line.strip().endswith(plugin):
                line = "    " + line[6:]
                matched = True
            elif line.startswith('    Load') and line.strip().endswith(plugin):
                matched = True

            raw += line

        if matched is False:
            raw += '\n'
            raw += '    # Enabled by DudaC\n'
            raw += '    # ================\n'
            raw += '    Load %s/plugins/%s/%s\n' % (monkey_stage, name, plugin)

        f = open(plugins, "w")
        f.write(raw)
        f.close()

    def run_webservice(self, schema=None):
        ws = os.path.abspath(self.service)
        monkey_stage = self.monkey.mk_path

        # Check if the web service was staged and built previously, we
        # this check to make sure the service is updated as the user needs/want
        stage_level = self.dudac_stage_path + '/monkey/api_level.dudac'
        if os.path.isfile(stage_level):
            f = open(stage_level, 'r')
            level = f.read().replace('\n', '')
            f.close()

            if level != self.mk_git.version:
                self.rebuild_monkey = True
        else:
            self.rebuild_monkey = True

        # Check if SSL is required and the Stack was built with SSL on it
        if self.monkey.SSL is True:
            polarssl = self.dudac_stage_path + '/monkey/plugins/polarssl/monkey-polarssl.so'
            if not os.path.isfile(polarssl):
                self.rebuild_monkey = True

        if self.rebuild_monkey is True:
            # Backup our original path
            cpath = os.getcwd()

            # On rebuild, check that stack sources are in place
            if os.path.exists(self.mk_home) is False or \
               os.path.exists(self.duda_home) is False:
                fail_msg("Error: the stack components are missing, try: \n\n" \
                         "    $ dudac -s\n")
                sys.exit(1)

            # Make sure Monkey sources match the snapshot
            if not os.getenv('DUDAC_STAGE'):
                self.mk_git.snapshot()
                self.duda_git.snapshot()
                self.merge_on_stage()

            # Cleanup and rebuild Monkey
            os.chdir(monkey_stage)

            if os.path.exists("./Makefile"):
                self.monkey.make_clean()

            self.monkey.configure()
            self.monkey.make_build()

            f = open(self.dudac_stage_path + '/monkey/api_level.dudac', 'w')
            f.write(self.mk_git.version + '\n')
            f.close()

            # Restore path
            os.chdir(cpath)

        makefile = "%s/Makefile" % (ws)
        makefile_in = "%s/Makefile.in" % (ws)
        if os.path.isdir(ws) is False or os.path.exists(makefile_in) is False:
            print "Error: Invalid web service directory " + ws
            exit(1)

        # Monkey headers
        mk_inc      = monkey_stage + "/include/ -I" + monkey_stage + "/src/include"
        mk_duda     = monkey_stage + "/plugins/duda/src"
        mk_packages = monkey_stage + "/plugins/duda/"

        # Read the Makefile.in file
        mk_ins = []
        for root, dirs, files in os.walk(ws):
            for file in files:
                if file == 'Makefile.in':
                    path = "%s/%s" % (root, file)
                    mk_ins.append(root)

        for mk in mk_ins:
            mk_in = "%s/Makefile.in" % (mk)

            CC_SET = None

            f = open(mk_in, "r")
            lines = f.readlines()
            f.close()

            raw = ""
            for line in lines:
                if line.startswith("INCDIR"):
                    prev = line.replace("INCDIR", "")
                    prev = prev.replace("=", "").strip()

                    raw += "INCDIR  = " + prev
                    raw += " -I" + mk_inc
                    raw += " -I" + mk_duda
                    raw += " -I" + mk_packages + "\n"
                else:
                    raw += line
            raw += "\n"

            makefile = "%s/Makefile" % (mk)
            f_mk = open(makefile, "w")
            f_mk.write("# Autogenerated by Duda Client Manager\n")
            f_mk.write("# ====================================\n")

            today = datetime.datetime.now()
            f_mk.write("# Date      : " + today.strftime('%a %d, %b %Y at %H:%M') + "\n")
            f_mk.write("# Stage Path: " + monkey_stage + "\n\n")

            f_mk.write(raw)
            f_mk.write(self.dudac_makefile)
            f_mk.close()

        # Cleanup web service and rebuild
        execute("WebService  : clean", "make -C " + ws + " clean")
        execute("WebService  : build", "make -C " + ws)

        # Get services
        services = []
        list = os.listdir(ws)
        for entry in list:
            p = ws + "/" + entry
            if os.path.isfile(p) and entry.endswith(".duda"):
                e = {'name': entry[:-5], 'filename': entry}
                services.append(e)

        # check that services exists
        if len(services) == 0:
            print "Error: i could not find Duda services under", ws
            exit(1)

        # Setting up virtual host
        vhost = monkey_stage + "/conf/sites/default"
        f = open(vhost, "r")
        lines = f.readlines()
        f.close()

        # Setting up web services
        print "%s %-70s" % (MSG_NEW, "Monkey      : configure HTTP Server"),
        raw = ""
        for line in lines:
            if line.startswith('[WEB_'):
                break
            else:
                raw += line

        for s in services:
            raw += "[WEB_SERVICE]\n"
            raw += "    Name " + s['name'] + "\n"
            raw += "    Enabled on\n"

            html = os.path.abspath(self.service) + '/html/'
            if os.path.exists(html):
                raw += "    DocumentRoot %s\n" % (html)

            confdir = os.path.abspath(self.service) + '/conf/'
            if os.path.exists(confdir):
                raw += "    ConfDir %s\n" % (confdir)

            datadir = os.path.abspath(self.service) + '/data/'
            if os.path.exists(datadir):
                raw += "    DataDir %s\n" % (datadir)

            logdir = os.path.abspath(self.service) + '/logs/'
            if os.path.exists(logdir):
                raw += "    LogDir  %s\n" % (logdir)

            raw += "\n"

        f = open(vhost, "w")
        f.write(raw)
        f.close()

        # Make sure Duda plugin is enabled on plugins.load
        self.enable_plugin(monkey_stage, 'duda')
        self.enable_plugin(monkey_stage, 'auth')

        if self.monkey.SSL is True:
            self.enable_plugin(monkey_stage, 'polarssl')

        # Setting up Duda plugin configuration
        duda = monkey_stage + "/conf/plugins/duda/duda.conf"
        f = open(duda, "r")
        lines = f.readlines()
        f.close()

        raw = ""
        for line in lines:
            if line.startswith("    ServicesRoot"):
                raw += "    ServicesRoot " + ws + "\n"
            else:
                raw += line

        f = open(duda, "w")
        f.write(raw)
        f.close()

        # Setting up Monkey
        monkey = monkey_stage + "/conf/monkey.conf"
        f = open(monkey, "r")
        lines = f.readlines()
        f.close()

        # Get Monkey version
        mk_version = self.monkey.version()
        raw = ""
        for line in lines:
            if mk_version == '1.6':
                if line.startswith("    Listen"):
                    raw += "    Listen " + str(self.port) + "\n"
                    continue
            elif mk_version == '1.5' or mk_version == '1.4':
                if line.startswith("    Port"):
                    raw += "    Port " + str(self.port) + "\n"
                    continue

            if line.startswith("    User"):
                raw += "    # User  Inactivated by DudaC\n"
            elif line.startswith("    TransportLayer"):
                if self.SSL is True:
                    raw += "    TransportLayer polarssl\n"
                    self.SSL_default = True
                else:
                    raw += "    TransportLayer liana\n"
                    self.SSL_default = False
            elif line.startswith("    TransportLayer") and line.find('polarssl') > 0:
                self.SSL_default = True
                raw += line
            else:
                raw += line

        f = open(monkey, "w")
        f.write(raw)
        f.close()

        print MSG_OK

        # Schema
        # ======
        # Once the new monkey.conf Port and TransportLayer are set, we can start
        # overriding the config if we have a schema. We do this at the end to do not
        # mess with specific settings handled by the previous lines.
        if schema is not None:
            # Change direct Port global
            if 'Port' in schema:
                self.port = schema['Port']

            # open the file and read it content
            f = open(monkey, "r")
            lines = f.readlines()
            f.close()

            # compose a new buffer
            raw = ""
            for line in lines:
                row = line
                key = None
                val = None
                kv  = []
                if line.startswith("    "):
                    # strip the indentation
                    row = line[4:]

                    # Lets see if this line can belong to a commented key/value
                    if row[:2] == '# ':
                        arr = row[2:].split()
                        if len(arr) == 2 and arr[0][-1] != ':':
                            if arr[0] in self.MCONF_KNOWN:
                                # ok, its a known key and is commented, now lets check
                                # if this key is bein overriden through the schema
                                if not arr[0] in schema:
                                    raw += line
                                else:
                                    raw += "    %s %s\n" % (arr[0], schema[arr[0]])

                                continue

                    kv = row.split()
                    if len(kv) != 2:
                        raw += line
                        continue
                    else:
                        # Start replacing
                        key = kv[0]
                        val = kv[1]
                        if key in schema:
                            raw += "    %s %s\n" % (key, schema[key])
                            continue


                raw += line

            # Flush our new content
            f = open(monkey, "w")
            f.write(raw)
            f.close()

        # Configure Transport Layer for SSL
        if self.SSL_default is True:
            self.SSL_configure(monkey_stage)


        http = monkey_stage + "bin/monkey"

        if self.SSL is True:
            http += " --transport polarssl"
        else:
            http += " --transport liana"

        try:
            if self.SSL_default is True:
                prot = "https"
            else:
                prot = "http"

            d = 0
            domain = prot + "://localhost:%s/" % str(self.port)
            schema = ""
            for s in services:
                if d > 0:
                    schema += "                                   "
                schema += domain + services[d]['name'] + '/' + "\n"
                d += 1

            # Do not trap the output of the server, just print everything
            # to STDOUT
            sc = ANSI_RESET + ANSI_CYAN + schema + ANSI_RESET
            if self.output_stdout is True:
                execute_stdout("%s Service Up  : %s" \
                                   % (MSG_NEW, sc), http, False)
            else:
                execute("%s Service Up  : %s" \
                            % (MSG_NEW, sc), \
                            http, False, True, False)

        except (RuntimeError, TypeError, NameError):
            print "\nDone!"
            raise

    def SSL_configure(self, monkey_stage):
        plgs = monkey_stage + "/conf/plugins.load"
        f = open(plgs, "r")
        lines = f.readlines()
        f.close()

        raw = ""
        for line in lines:
            if line.find('monkey-polarssl') > 0 and self.SSL is True:
                raw += line.replace("# Load", "Load")
            else:
                raw += line

        f = open(plgs, "w")
        f.write(raw)
        f.close()

        # Check if SSL certificates exists
        sslconf = monkey_stage + "/conf/plugins/polarssl/polarssl.conf"
        f = open(sslconf, "r")
        lines = f.readlines()
        f.close()

        certificate_file = None
        rsa_key_file = None
        dh_param_file = None
        for line in lines:
            row = line.strip()
            if row.startswith('CertificateFile'):
                key, val = row.split()
                if os.path.exists(val):
                    certificate_file = val
            elif row.startswith('RSAKeyFile'):
                key, val = row.split()
                if os.path.exists(val):
                    rsa_key_file = val
            elif row.startswith('DHParameterFile'):
                key, val = row.split()
                if os.path.exists(val):
                    dh_param_file = val

        # Generate Certificates if they dont exists
        p = monkey_stage + "/conf/plugins/polarssl/"
        if rsa_key_file is None:
            cmd = "openssl genrsa -out " + p + "rsa_key.pem 1024"
            execute("SSL: Generate RSA", cmd)
            rsa_key_file = p + "rsa_key.pem"
        else:
            print_msg("SSL         : RSA (cached)", True)

        if certificate_file is None:
            cmd = "openssl req -new -x509 -key " + rsa_key_file + \
                " -out " + p + "srv_cert.pem" + " -days 1095 -subj '/C=US'"
            execute("SSL: Generate Certificate", cmd)
            certificate_file = p + "srv_cert.pem"
        else:
            print_msg("SSL         : Cert (cached)", True)

        if dh_param_file is None:
            cmd = "openssl dhparam -out " + p + "dhparam.pem 1024"
            execute("SSL: Generate DH Params", cmd)
            dh_param_file = p + "dhparam.pem"
        else:
            print_msg("SSL         : DH Params (cached)", True)

        # Create new config and override polarssl.conf file
        raw  = "[SSL]\n"
        raw += "    CertificateFile " + certificate_file + "\n"
        raw += "    RSAKeyFile      " + rsa_key_file + "\n"
        raw += "    DHParameterFile " + dh_param_file + "\n\n"

        f = open(sslconf, "w")
        f.write(raw)
        f.close()

    def reset(self):
        if os.getenv('DUDAC_HOME') is None or self.reset_force is True:
            self.mk_git.remove(self.mk_home)
            self.duda_git.remove(self.duda_home)
            try:
                shutil.rmtree(self.dudac_stage_path)
            except:
                pass
        else:
            print_msg("Cannot reset when DUDAC_HOME is set, use -R instead", 0)

    def print_version(self):
        print_bold("Duda Client Manager - v%s" % DUDAC_VERSION)
        print_color("http://duda.io", ANSI_YELLOW, True)
        print_color("http://monkey-project.com\n", ANSI_YELLOW, True)

    def print_help(self):
        print "Usage: dudac [-g|-s] [-V] [-S] [-h] [-v] [-A] [-J] [-T] -w WEB_SERVICE_PATH\n"
        print ANSI_BOLD + ANSI_WHITE + "Stack Build Options" + ANSI_RESET
        print "  -V\t\t\tAPI level (default: %i)" % DEFAULT_API_LEVEL
        print "  -s\t\t\tGet stack sources using HTTPS"
        print "  -g\t\t\tGet stack sources using GIT protocol (SSH)"
        print "  -F\t\t\tForce mode, rebuild the Stage area"
        print "  -r\t\t\tRemove stack sources"
        print "  -R\t\t\tRemove stack sources even if $DUDAC_HOME is set"
        print

        print ANSI_BOLD + ANSI_WHITE + "Profiling and Trace" + ANSI_RESET
        print "  -A\t\t\tUse libc memory allocator instead of Jemalloc (disabled)"
        print "  -X\t\t\tEnable Jemalloc statistics (disabled)"
        print "  -J\t\t\tEnable Jemalloc profiling and leaks detection (disabled)"
        print "  -T\t\t\tEnable Linux Trace Toolkit (disabled)"

        print
        print ANSI_BOLD + ANSI_WHITE + "HTTP Server Options" + ANSI_RESET
        print "  -p TCP_PORT\t\tSet TCP port (default 2001)"
        print "  -w WEB_SERVICE\tSpecify web service source path"
        print "  -S\t\t\tWeb Service will run with SSL mode enabled"
        print "  -M 'k1=v1,kn=vn'\tOverride some web server config key/value"

        print
        print ANSI_BOLD + ANSI_WHITE + "Others" + ANSI_RESET
        print "  -h\t\t\tPrint this help"
        print "  -u\t\t\tRedirect server output to STDOUT"
        print "  -v\t\t\tPrint version"
        print

        print ANSI_BOLD + ANSI_WHITE + "Environment Variables" + ANSI_RESET
        print "  DUDAC_HOME\t\tSet where to store the stack sources (default: ~/.dudac)"
        print "  DUDAC_STAGE\t\tSet the stage build area (default: ~/.dudac/stage)"
        print

    # it creates a configuration schema to override the values of the main
    # Monkey configuration file
    def conf_schema(self, value):
        if value.find(',') > 0:
            entries = value.split(',')
            if len(entries) == 0:
                return None
        else:
            key, val = value.split('=')
            if len(key) == 0 or len(val) == 0:
                print "Error: Invalid configuration schema '%s'" % value
                exit(1)

            return {key: val}

        # Lookup all entries in the value
        c = {}
        for e in entries:
            key, val = e.split('=')
            if len(key) == 0 or len(val) == 0:
                print "Error: Invalid configuration schema '%s'" % value
                exit(1)
            c[key] = val

        return c

    def get_arguments(self):
        update = None
        monkey_conf = None
        self.api_level = "dst-%i" % int(DEFAULT_API_LEVEL)

        if 'DEFS' not in os.environ:
            os.environ['DEFS'] = ''

        # Reading command line arguments
        try:
            optlist, args = getopt.getopt(sys.argv[1:], 'DV:sgFrRhvSuw:p:AXJTM:')
        except getopt.GetoptError:
            self.print_help()
            sys.exit(2)

        if len(optlist) == 0:
            self.print_help()
            sys.exit(2)

        # Check options
        for op, arg in optlist:
            if op == '-s':
                update = PROTOCOL_HTTPS
            elif op == '-g':
                update = PROTOCOL_GIT
            elif op == '-F':
                self.rebuild_monkey = True
            elif op == '-r':
                self.reset_environment = True
                self.reset_force = False
            elif op == '-R':
                self.reset_environment = True
                self.reset_force = True
            elif op == '-V':
                self.api_level = arg
            elif op == '-S':
                self.SSL = True
            elif op == '-p':
                if not str(arg).isdigit():
                    self.print_help()
                    exit(1)
                self.port = arg
            elif op == '-A':
                self.linux_malloc = True
            elif op == '-X':
                self.jemalloc_stats = True
            elif op == '-J':
                self.jemalloc_prof = True
            elif op == '-M':
                monkey_conf = arg
            elif op == '-D':
                self.service_macros = arg
            elif op == '-T':
                self.linux_trace = True
            elif op == '-u':
                self.output_stdout = True
            elif op == '-v':
                sys.exit(0)
                break
            elif op == '-w':
                self.service = arg
                self.config_requirements()
            elif op == '-h':
                self.print_help()
                sys.exit(0)
            else:
                self.print_help()
                sys.exit(0)

        print_info("HOME        : " + self.dudac_home_path)
        print_info("STAGE       : " + self.dudac_stage_path)

        # Reset environment
        if self.reset_environment is True:
            self.reset()
            sys.exit(0)

        # SSL
        if self.SSL is True:
            self.monkey.SSL = True

        # Enable Jemalloc profiling
        if 'JEMALLOC_OPTS' not in os.environ:
            os.environ['JEMALLOC_OPTS'] = ''

        if self.jemalloc_prof is True:
            os.environ['JEMALLOC_OPTS']  += '--enable-prof'
            os.environ['JE_MALLOC_CONF']  = 'prof_leak:true,prof:true,prof_prefix:duda.jeprof'

        # More environment vars: make will use 8 jobs
        os.environ['MAKEFLAGS'] = '-j 8'

        # Linux Trace Toolkit
        if self.linux_trace is True:
            self.monkey.opts += "--linux-trace "

        # Use system malloc instead Jemalloc
        if self.linux_malloc is True:
            self.monkey.opts += "--malloc-libc "

        # Jemalloc Stats
        if self.linux_malloc is False and self.jemalloc_stats is True:
            os.environ['JEMALLOC_OPTS'] += ' --enable-stats'
            os.environ['DEFS'] += ' -DJEMALLOC_STATS'

        # Rebuild the stack ?
        if update is not None:
            if self.rebuild_monkey is True:
                print "Error: you cannot mix the flag -g or -s"
                exit(1)

            self.update_framework(update)

        # Override Monkey configuration. It will create the configuration
        # schema which is used later by the run_webservice() method.
        if monkey_conf:
            mconf_schema = self.conf_schema(monkey_conf)
        else:
            mconf_schema = None

        # Run web service
        if self.service:
            self.run_webservice(mconf_schema)

    def _temp_path(self):
        pass

def main():
    d = Duda()

if __name__ == '__main__':
    main()
