###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import os
import re
import subprocess
from datetime import datetime
from shutil import copytree, rmtree
from socket import gethostname
from permutation import Permutation
from topology import Topology
from tree import TreeIterator

hostname_regex = re.compile('[a-zA-Z_\-]+')

"""
Decorator that moves into the application directory while running the function.
"""
def app_local(f):
    def wrapper(*args, **kwargs):
        me = args[0]
        cwd = os.getcwd()
        os.chdir(me.local_dir())
        try:
            ret = f(*args, **kwargs)
            os.chdir(cwd)
            return ret
        except Exception as e:
            os.chdir(cwd)
            raise e
    return wrapper

"""
Stringify application argument list in a single output field.
"""
def args_str(*args, **kwargs):
    fmt = re.compile('-?\w+')

    args_list=[]
    for arg in args:
        if fmt.match(str(arg)) is None:
            raise ValueError('arg: "{!s}" error. Expected arg format: -?[0-9a-zA-Z_]'.format(str(arg)))
        args_list.append('{!s}'.format(arg))
        
    for k,v in kwargs.items():
        k = str(k)

        if v is not None:
            v = str(v)
            if fmt.match(v) is None:
                raise ValueError('kwarg: {} error. Expected arg format: [0-9a-zA-Z_]'.format(v))
            if len(k) == 1:
                args_list.append('-{!s}={!s}'.format(k,v))
            else:
                args_list.append('--{!s}={!s}'.format(k,v))
        else:
            if len(k) == 1:
                args_list.append('-{}'.format(k))
            else:
                args_list.append('--{}'.format(k))
    return ':'.join(args_list)

def str_args(s: str):
    args = s.split()
    kwargs = zip(args[:-1], args[1:])
    kwargs = { x.strip('-'):y.strip('"') for (x,y) in kwargs if x[0] == '-' and y[0] != '-' }
    args = [ a for a in args if a.strip('-') not in list(kwargs.keys()) + list(kwargs.values())]
    return args, kwargs
    
"""
Generic class that describes an application.
An application needs to provide way to:
* a name(),
* application dir() directory
* compile() (optional if compilation not needed),
* a cmdline() to run the application,
* a get_timing() function to collect application run time after execution.
With these methods provided, Application constructor will:
* copy application in a directory for the current machine.
* compile application
* bind application threads with default binding.
* Collect application runtime when its run() method is invoked.
"""
class Application:
    """
    Generic application constructor.
    Must be call after other initializations in subclass if the subclass 
    compilation requires other initializations.
    This constructor will look for a machine local copy of the application.
    If the directory does not exists, application files are copied and 
    application is compiled.
    """
    def __init__(self):
        try:
            if not os.path.isdir(self.dir()):
                raise ValueError('Application {} dir() {} is not a valid directory.'.format(self.name(), self.dir()))
        except NotImplementedError:
            pass
        self.binding = None
        local_dir = self.local_dir()
        try:
            if not os.path.isdir(local_dir):
                copytree(self.dir(), local_dir)
                self.setup()
        except NotImplementedError:
            pass        
    
    """
    Return application name represented by this class.
    Must be implemented.
    """
    def name(self):
        raise NotImplementedError
    
    """
    Return application directory.
    Must be implemented.
    """
    @classmethod
    def dir(cls):
        raise NotImplementedError

    """
    Directory where files are copied, compiled run.
    """
    def local_dir(self, hostname = gethostname()):
        try:
            basename = os.path.basename(self.dir())
        except NotImplementedError:
            return os.getcwd()
        hostname = hostname_regex.match(hostname).group()
        return '{}{}{}-{}'.format(os.getcwd(), os.path.sep,
                                  basename, hostname)
    
    """
    Compile application from its directory.
    Must be implemented if application requires compilation.
    """
    def compile(self) -> str:
        raise NotImplementedError
    
    """
    Compile application if compile method is implemented.
    """
    @app_local
    def setup(self):
        try:
            cmd = self.compile().split()
            if subprocess.check_call(cmd) != 0:
                raise Exception('Compilation error.')
        except NotImplementedError:
            pass
    
    """
    Bind application threads with a list of Topology objects.
    bind will export OMP_NUM_THREADS env to the number of @topology_nodes
    bind will then prepend hwloc-thread-bind command to application command line.
    """
    def bind(self, topology_nodes: list):
        nodes = [ n for n in topology_nodes ]
        self.binding = 'hwloc-thread-bind -l '
        self.binding += ' '.join([ '{}:{}'.format(n.type, n.logical_index) for n in nodes ])
        self.binding += ' -- '
    
    """
    Utility function for definining a command line.
    * The command line starts with @bin
    * @args are expended to their string value.
    * @kwargs keys are expended to -<key> if len(<key>) == 1 else --<key>. 
      @kwargs values are expended with their string value.
    * @prepend a prepended to the command line.
    * @append is appended to the command line.
    The command line is not wrapped into bash so pipes and redirection won't work.
    
    """
    def make_cmdline(self, bin: str, *args, prepend='', append='', **kwargs) -> str:
        cmd = bin
        if self.binding is not None:
            cmd = self.binding + cmd
        for k, v in kwargs.items():
            if len(k) == 1:
                cmd += ' -{!s} {!s}'.format(k, v)
            else:
                cmd += ' --{!s} {!s}'.format(k, v)
        for arg in args:
            cmd += ' {!s}'.format(arg)
        if isinstance(prepend, list) and len(prepend) > 0:            
            prepend[-1] += cmd + append
            cmd = prepend
        elif isinstance(prepend,str):
            cmd = (prepend + cmd + append).split()
        return cmd
    
    """
    Build a command line provided application arguments @args, @kwargs
    where @kwargs keys do not start with '-' or '--'.
    """
    def cmdline(self, *args, **kwargs) -> str:
        bin = os.curdir + os.path.sep + self.name()
        return self.make_cmdline(bin, *args, **kwargs)
            
    """
    Get application Figure Of Merit (FOM) or time after it is run.
    @param out: The content of stdout.
    """
    @classmethod
    def get_timing(cls, output: str):
        raise NotImplementedError
    
    """
    Run an application with its arguments and return the 
    Figure Of Merit (FOM) or runtime
    """
    @app_local
    def run(self, *args , **kwargs):
        cmd = self.cmdline(*args, **kwargs)
        try:
            out = subprocess.getoutput(' '.join(cmd))
        except Exception as e:
            print('Command line failed: {}'.format(cmd))
            raise e
        seconds = self.get_timing(out)
        return seconds

"""
Class representing application that can be run straight out of a command line
"""
class Bash(Application):
    time_regex = re.compile('.*(?P<minutes>\d+):(?P<seconds>\d+).(?P<milliseconds>\d+).*')
    
    """
    Build application from its binary name.
    """
    def __init__(self, bin: str):
        self.bin = bin
        super().__init__()
        
    def name(self):
        return os.path.basename(self.bin)
    
    def cmdline(self, *args, **kwargs):
        return self.make_cmdline(self.bin,
                                 *args,
                                 prepend='/usr/bin/time -o /dev/stdout -f %E ',
                                 **kwargs)

    @classmethod
    def get_timing(cls, output):        
        for l in output.split('\n'):
            match = cls.time_regex.match(l)
            if match is not None:
                match = match.groupdict()
                return 60*float(match['minutes']) + float(match['seconds']) + 1e-2*float(match['milliseconds'])

class StdoutTiming(Application):
    regex = None

    @classmethod
    def get_timing(cls, output):
        for l in output.split('\n'):
            match = cls.regex.match(l)
            if match is not None:
                return float(match.groupdict()['seconds'])

class OpenMP(Application):
    def bind(self, topology_nodes: list):
        pus = [ n.PUs[0] for n in topology_nodes ]
        os.environ['OMP_NUM_THREADS'] = str(len(topology_nodes))
        os.environ['OMP_PLACES'] = ','.join([ str(pu.os_index) for pu in pus ])

"""
Class representing NAS parallel benchmarks applications
"""
class NAS(OpenMP, StdoutTiming):
    regex = re.compile('[\s]*Time[\s]+in[\s]+seconds[\s]+[=][\s]+(?P<seconds>[\d]+[.][\d]+)')
    
    def __init__(self, _class = 'B'):
        self._class = _class
        super().__init__()
    
    @classmethod
    def dir(cls):
        return os.path.expanduser('~') + os.path.sep + 'Documents' + os.path.sep + 'NPB3.4-OMP'
    
    def name(self):
        return 'NAS.{}'.format(self._class)
    
    def compile(self):
        return 'make suite CLASS={}'.format(self._class)
    
    def cmdline(self, *args, **kwargs):
        app = args[0]
        bin = os.curdir + os.path.sep + 'bin' + os.path.sep + app + '.' + self._class + '.x'
        return self.make_cmdline(bin)

"""
Class representing LULESH OpenMP application
"""
class Lulesh(OpenMP, StdoutTiming):
    regex = re.compile('[\s]*Elapsed[\s]+time[\s]+[=][\s]+(?P<seconds>[\d]+[.][\d]+)[\s]+\(s\)')
    
    def __init__(self):
        super().__init__()
    
    @classmethod
    def dir(cls):
        return os.path.expanduser('~') + os.path.sep + 'Documents' + os.path.sep + 'LULESH'
    
    def name(self):
        return 'lulesh2.0'
    
    def compile(self):
        return 'make'
    
            
applications = { 'NAS': NAS(), 'sleep': Bash('sleep'), 'echo': Bash('echo'), 'lulesh': Lulesh() }

__all__ = [ 'Application', 'applications' ]

if __name__ == '__main__':
    echo = Bash('echo')
    print('echo toto: {}'.format(echo.run('-n', 'toto')))
    sleep = Bash('sleep')
    print('sleep 1.2: {}'.format(sleep.run('1.2')))
    nas = NAS()
    print('NAS cg: {}'.format(nas.run('cg')))
    lulesh = Lulesh()
    print('lulesh -i 10: {}'.format(lulesh.run(i=10)))
