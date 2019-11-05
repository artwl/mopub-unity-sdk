#! /usr/bin/python2.7
"""Removes lines containing private information from all text files in a subdirectory tree.

This includes lines that start with // TODO, //TODO, * TODO or *TODO from all files ending in .cs
It also removes the Team Id from the .asset file under Unity's ProjectSettings directory.
"""

import argparse, os, re, sys

TODO_RE = r'^\s*(//|\*)\s?TODO'

def process_directory(path):
    """Walk the path and run remove_todos on every file."""
    for (dirpath, _unused, filenames) in os.walk(path):
        for filename in filenames:
            if filename.endswith('.cs'):
                process_file(dirpath, filename, TODO_RE)

def process_file(dirname, filename, regex):
    """Remove every line that matches regex"""
    readfile = dirname + "/" + filename
    writefile = readfile + ".tmp"
    with open(readfile, "r") as infile, open(writefile, "w") as outfile:
        for line in infile:
            if not re.match(regex, line, flags=re.UNICODE | re.IGNORECASE):
                outfile.write(line)

    os.rename(writefile, readfile)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Remove private lines from text files in all subdirectories.')
    parser.add_argument('path',
                        help='The root of the file tree to remove all private lines from. Defaults to the current directory.',
                        default='.', nargs='?')
    args = parser.parse_args()
    # Verify before performing potentially destructive behavior
    print 'This script will remove all private lines found in: {}\n'.format(args.path)
    raw_input('Press Enter to continue...\n')
    process_directory(args.path)

