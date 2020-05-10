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

hostname = lambda: re.match('[a-zA-Z_\-]+', gethostname()).group()

"""
Decorator that moves into the application directory while running the function.
"""
def app_local(f):
    def wrapper(*args, **kwargs):
        me = args[0]
        cwd = os.getcwd()
        os.chdir(me.path)
        try:
            ret = f(*args, **kwargs)
            os.chdir(cwd)
            return ret
        except Exception as e:
            os.chdir(cwd)
            raise e
    return wrapper

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
        try:
            basename = os.path.basename(self.dir())
            self.path = '{}{}{}-{}'.format(os.getcwd(), os.path.sep, basename, hostname())
            if not os.path.isdir(self.path):
                copytree(self.dir(), self.path)
                self.setup()
        except NotImplementedError:
            self.path = os.getcwd()
        time = str(datetime.now())
        time = re.sub('\s', '-', time)
        self.out_file = self.path + os.path.sep + 'run-{}.out'.format(time)
        
    """
    Return application name represented by this class.
    Must be implemented.
    """
    @classmethod
    def name(cls):
        raise NotImplementedError
    
    """
    Return application directory.
    Must be implemented.
    """
    @classmethod
    def dir(cls):
        raise NotImplementedError
    
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
        self.binding += ' '.join([ '{}:{}'.format(n.annotation['type'], n.annotation['logical_index']) for n in nodes ])
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
        raise NotImplementedError
    
    """
    Get the content of application standard output as an array of lines.
    """
    def output(self):
        with open(self.out_file) as f:
            return f.readlines()
        
    """
    Get application Figure Of Merit (FOM) or time after it is run.
    """
    def get_timing(self):
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
        try:
            f = open(self.out_file, 'a')
        except FileNotFoundError:
            f = open(self.out_file, 'x')
        f.write(out)
        f.flush()
        seconds = self.get_timing()
        os.remove(self.out_file)
        return seconds

"""
Class representing application that can be run straight out of a command line
"""
class Bash(Application):
    """
    Build application from its binary name.
    """
    def __init__(self, bin: str):
        super().__init__()
        self.bin = bin
        
    @classmethod
    def name(self):
        return os.path.basename(self.bin)
    
    def cmdline(self, *args, **kwargs):
        return self.make_cmdline(self.bin,
                                 *args,
                                 prepend='/usr/bin/time -o {} -f %E '.format(self.out_file),
                                 **kwargs)
    
    def get_timing(self):        
        regex = re.compile('(?P<minutes>\d+):(?P<seconds>\d+).(?P<milliseconds>\d+)')
        for l in self.output():
            match = regex.match(l)
            if match is not None:
                return 60*float(match['minutes']) + float(match['seconds']) + 1e-2*float(match['milliseconds'])


class OpenMP(Application):
    def bind(self, topology_nodes: list):
        pus = [ Topology.get_children(n.annotation['type'],
                                      n.annotation['logical_index'],
                                      'PU')[0] for n in topology_nodes ]
        os.environ['OMP_NUM_THREADS'] = str(len(pus))
        os.environ['OMP_PLACES'] = ','.join([ str(pu['os_index']) for pu in pus ])

"""
Class representing NAS parallel benchmarks applications
"""
class NAS(OpenMP):
    def __init__(self, _class = 'B'):
        self._class = _class
        super().__init__()
    
    def dir(self):
        return os.path.expanduser('~') + os.path.sep + 'Documents' + os.path.sep + 'NPB3.4-OMP'
    
    def name(self):
        return 'NAS.{}'.format(self._class)
    
    def compile(self):
        return 'make suite CLASS={}'.format(self._class)
    
    def clean(self):
        return 'make clean'
    
    def cmdline(self, *args, **kwargs):
        app = args[0]
        bin = os.curdir + os.path.sep + 'bin' + os.path.sep + app + '.' + self._class + '.x'
        return self.make_cmdline(bin)
    
    def get_timing(self):
        output = self.output()
        regex = re.compile('[\s]*Time[\s]+in[\s]+seconds[\s]+[=][\s]+(?P<seconds>[\d]+[.][\d]+)')
        for l in output:
            match = regex.match(l)
            if match is not None:
                return float(match.groupdict()['seconds'])    

applications = { 'NAS': NAS(), 'sleep': Bash('sleep'), 'echo': Bash('echo') }

__all__ = [ 'Application', 'applications' ]

if __name__ == '__main__':
    echo = Bash('echo')
    print('echo -n toto: {}'.format(echo.run('-n', 'toto')))
    sleep = Bash('sleep')
    print('sleep 1.2: {}'.format(sleep.run('1.2')))
    nas = NAS()
    print('NAS cg: {}'.format(nas.run('cg')))
