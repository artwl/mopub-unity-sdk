#!/usr/bin/python
import os
import os_helper


def current_branch():
    return os_helper.check_output('git rev-parse --abbrev-ref HEAD').strip()

def current_hash():
    return os_helper.check_output('git rev-parse HEAD').strip()

def repo_name():
    return os_helper.check_output('git config --get remote.origin.url').strip()

def create(branch):
    return os_helper.check_output('git branch {}'.format(branch)).strip()

def checkout(branch):
    if branch != current_branch():
        print 'Checking out branch: ' + branch
        os_helper.call('git checkout ' + branch)

def pull():
    print 'Pulling branch: ' + current_branch()
    os_helper.call('git pull')


def merge(branch):
    print 'Merging branch: {} into {}'.format(branch, current_branch())
    os_helper.call('git merge {} --no-edit'.format(branch))


def chdir_root():
    # git_root is the .git directory, so change to one directory higher
    git_dir = os_helper.check_output('git rev-parse --git-dir')
    git_root = os.path.abspath(os.path.join(git_dir.strip(), '..'))
    print 'Changing working directory to git root: {}'.format(git_root)
    os.chdir(git_root)
