"""A set of utilities for manipulating directories & making system calls."""
import os, shlex, subprocess, sys, tempfile
import os_helper



def check_output(command):
    return subprocess.check_output(shlex.split(command), env=os.environ)

def call(command):
    return_code = subprocess.call(shlex.split(command), env=os.environ)
    if return_code:
        sys.exit(1)

def check_call(command):
    return subprocess.check_call(shlex.split(command), env=os.environ)

class mktempdir:
    """Returns a tempdir class that can be deleted in a with block."""
    def __enter__(self):
        self.direc = tempfile.mkdtemp()
        return self.direc

    def __exit__(self, type, value, traceback):
        os_helper.call("rm -rf {}".format(self.direc))
