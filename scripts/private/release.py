#!/usr/bin/env python2.7
"""MoPub Unity SDK Release Script.

Creates, tests, and processes a tagged release branch on the private repo.
On success, commits on the public repo, ready to be pushed.


PREREQUISITES:
  > mopub-unity and mopub-unity-sdk repositories must both be checked out and
    be siblings in the same directory
  > iOS plugin should be ready for release:
    > MoPub iOS SDK should have been updated
    > iOS plugin should have been built via mopub-ios-sdk-unity-build
    > iOS plugin should have been tested and checked in
  > this script must be run from the mopub-unity/ directory.

For more information, see the Unity Release document:
  http://go/adf-unity-release
"""
import argparse
import os, re, subprocess
import git_helper, os_helper, strip_lines

GREEN = "\033[92m"
RED   = "\033[91m"
END   = "\033[0m"
WORKSPACE = os.path.abspath('../')
PRIVATE_REPO = os.path.join(WORKSPACE, 'mopub-unity')
PUBLIC_REPO = os.path.join(WORKSPACE, 'mopub-unity-sdk')
ANDROID_BUILD_SCRIPT = os.path.join(PRIVATE_REPO, 'scripts', 'mopub-android-sdk-unity-build.sh')
IOS_BUILD_SCRIPT = os.path.join(PRIVATE_REPO, 'scripts', 'mopub-ios-sdk-unity-build.sh')
SAMPLE_APP_PROJECT_SETTINGS = os.path.join(PRIVATE_REPO, 'unity-sample-app', 'ProjectSettings',
        'ProjectSettings.asset')
NATIVE_JAR = os.path.join(PRIVATE_REPO, 'unity-sample-app', 'Assets', 'MoPub', 'Plugins', 'Android', 'MoPub', 'libs', 'mopub-sdk-native-static.jar')

def on_branch(func):
    """This decorator tries to check out a branch named for the first arg.

    Raises a CalledProcessError if it can't.
    """
    def func_wrapper(*args, **kwargs):
        if not (args and args[0]):
            raise subprocess.CalledProcessError(1, cmd="on_branch",
                                                output="branch_name not supplied")
        git_helper.checkout(args[0])
        return func(*args, **kwargs)
    return func_wrapper

def release_step(func):
    """Decorator that prints a nice message after a step completes without raising an exception."""
    def func_wrapper(*args, **kwargs):
        returnval = func(*args, **kwargs)
        print GREEN + "**** RELEASE STEP COMPLETED: {} ****".format(func.__name__) + END
        return returnval
    return func_wrapper

@release_step
def create_release_branch(version_string, commit_hash=None, internal=False, test=False):
    """Creates a branch named 'release-$version_string' from the provided commit_hash

    Uses the tip of master if no commit_hash is present.
    """
    if commit_hash is None:
        if not test:
            git_helper.checkout("master")
            git_helper.pull()
        commit_hash = git_helper.current_hash()

    internal_prefix = "internal-" if internal else ""
    release_branch = "{}release-{}".format(internal_prefix, version_string)
    # Check for existence of branch on origin, fail if it exists.
    release_branch_found = os_helper.check_output("git ls-remote --heads origin | grep refs/heads/{}".format(release_branch))
    if test or not release_branch_found:
        os_helper.check_call("git checkout -b {} {}".format(release_branch, commit_hash))
        return release_branch
    else:
        raise subprocess.CalledProcessError(
            1,
            cmd="create_release_branch({})".format(release_branch),
            output="Release branch {} exists on the origin remote.".format(release_branch))

@on_branch
@release_step
def strip_private_lines(branch_name):
    """Removes lines from various files that can carry private information"""
    strip_lines.process_directory('.')

@on_branch
@release_step
def update_sample_app_version(branch_name, version_string):
    """Update the bundle version and Android/iOS version codes in the sample app"""
    # update platform-independent bundle version
    bundle_version_pattern = re.compile(r'  bundleVersion: .*')
    bundle_version_replacement = r'  bundleVersion: {}'.format(version_string)
    replace_file_lines(SAMPLE_APP_PROJECT_SETTINGS,
            (bundle_version_pattern, bundle_version_replacement))

    # convert version into bundle code
    major,minor,patch = version_string.split('.')
    if len(minor) == 1:
        # since minor versions have gone over 9, we need to pad it to keep it increasing
        minor = minor + '0'
    bundle_code = major + minor + patch

    # update per-platform bundle code
    ios_bundle_code_pattern = re.compile(r'    iOS: \d+')
    ios_bundle_code_replacement = r'    iOS: {}'.format(bundle_code)
    replace_file_lines(SAMPLE_APP_PROJECT_SETTINGS,
            (ios_bundle_code_pattern, ios_bundle_code_replacement))
    android_bundle_code_pattern = re.compile(r'  AndroidBundleVersionCode: \d+')
    android_bundle_code_replacement = r'  AndroidBundleVersionCode: {}'.format(bundle_code)
    replace_file_lines(SAMPLE_APP_PROJECT_SETTINGS,
            (android_bundle_code_pattern, android_bundle_code_replacement))

def clear_mopub_defines(m):
    """Helper function to compute a replacement string from the regex match object.  This is
    specific to the Scripting Defines lines in Unity's ProjectSettings.asset file, each of
    which has a semicolon-separated list of symbols.  We need to filter out the 'mopub_developer',
    'mopub_native_beta' and 'mopub_menu_beta' symbols and then clean up semicolons correctly.  Use
    split() and join() to do so.
    """
    return m.group(1) + ';'.join(filter(
        lambda d: d != 'mopub_developer' and d != 'mopub_native_beta' and d != 'mopub_build_menu_beta',
        m.group(2).split(';')))

@on_branch
@release_step
def make_build_scripts_use_public_sdks(branch_name):
    """Changes the value of INTERNAL_SDK in the build scripts to false"""
    internal_sdk_line_pattern = re.compile(r':.*INTERNAL_SDK:=.*')
    replacement = r': "${INTERNAL_SDK:=false}"'
    replace_file_lines(ANDROID_BUILD_SCRIPT, (internal_sdk_line_pattern, replacement))
    replace_file_lines(IOS_BUILD_SCRIPT, (internal_sdk_line_pattern, replacement))
    # Reclaim execute permissions lost in replace_file_lines
    os_helper.call("chmod +x {}".format(ANDROID_BUILD_SCRIPT))
    os_helper.call("chmod +x {}".format(IOS_BUILD_SCRIPT))
    # Remove all 'mopub_*' symbols from sample app's defines, so that the corresponding
    # options are disabled by default.
    define_pattern = re.compile(r'(\s*\d+:\s*)(.*)')
    replace_file_lines(SAMPLE_APP_PROJECT_SETTINGS, (define_pattern, clear_mopub_defines))
    # TODO: remove Android platform from native-static.jar

def replace_file_lines(fname, *args):
    """Reads all the lines from the given file and applies the provided replacement patterns to it.

    Replacement patterns are formatted (compiled_regex, replacement).
    Every replacement pattern must be used, or this function will raise a CalledProcessError.
    Patterns can be used more than once.
    Earlier replacement patterns will short-circuit later ones:
      First pattern: (a, a)
      Second pattern: (a, c)
      The second pattern will never match, since the first pattern is identical to it.
    """
    replacement_succeeded = [False for arg in args]
    with open(fname, 'r') as infile, open(fname + '.tmp', 'w') as outfile:
        for line in infile:
            for i, pattern in enumerate(args):
                # This will raise an IndexError if the args are not structured properly
                regex, replacement = pattern[0], pattern[1]
                (outline, replaced) = regex.subn(replacement, line)
                if replaced > 0:
                    replacement_succeeded[i] = True
                    break
            outfile.write(outline)
        if all(replacement_succeeded):
            os_helper.check_call('mv {} {}'.format(fname + '.tmp', fname))
        else:
            error_output = "Didn't find all provided patterns in {}\n\tPatterns:".format(fname)
            for arg in args:
                error_output += \
                    "\n\tpattern: {} replacement: {}".format(arg[0], arg[1])
            print RED + error_output + END
            raise subprocess.CalledProcessError(
                1,
                cmd="replace_file_lines",
                output=error_output)

@release_step
def update_mopub_sdk_submodules(external_only=False):
    """Pulls the latest MoPub Android and iOS SDK releases, both internal and external"""
    os_helper.check_call('git --git-dir mopub-android-sdk/.git pull origin master')
    os_helper.check_call('git --git-dir mopub-ios-sdk/.git pull origin master')
    if not external_only:
        os_helper.check_call('git --git-dir mopub-android/.git pull origin master')
        os_helper.check_call('git --git-dir mopub-ios/.git pull origin master')

@release_step
def reset_mopub_sdk_submodules():
    """Resets the git state of the Android and iOS submodules"""
    os_helper.check_call('git --git-dir mopub-android-sdk/.git checkout .')
    os_helper.check_call('git --git-dir mopub-android-sdk/.git clean -df')
    os_helper.check_call('git --git-dir mopub-ios-sdk/.git checkout .')
    os_helper.check_call('git --git-dir mopub-ios-sdk/.git clean -df')

@on_branch
@release_step
def recover_mopub_sdk_submodules(branch):
    """Brings back the Android and iOS submodules"""
    os_helper.check_call('git submodule init')
    os_helper.check_call('git submodule update --recursive')

@on_branch
@release_step
def commit_all_changes(branch_name, commit_message=None, extra_args=""):
    """Commits all file changes with an optional commit message."""
    message = commit_message or "Commit generated by release.py"
    os_helper.check_call('git commit {} -am "{}"'.format(extra_args, message))
    return git_helper.current_hash()

@on_branch
@release_step
def build_wrappers_and_export_unity_package(branch_name):
    """Runs the build.sh script."""
    os_helper.check_call("./scripts/build.sh")

@on_branch
@release_step
def commit_release_branch(branch_name, version_string, internal=False):
    """Creates an optionally tagged release commit on the given branch."""
    # Commit to the private repo with the version number
    commit_all_changes(branch_name, "Release: version {}".format(version_string))

    if not internal:
        # Tag private repo with version number
        os_helper.call('git tag -f -a "v{}" -m "Version: {}"'.format(version_string, version_string))


@on_branch
@release_step
def push_private_release_branch(branch_name, version_string, internal=False):
    """Push the release branch to the private mopub_unity repo."""
    os_helper.call('git push origin {}'.format(branch_name))
    if not internal:
        # Push the release tag.
        os_helper.call('git push --force origin v{}'.format(version_string))

@release_step
def prepare_public_repo(public_repo, staging_dir):
    """Sets up the public repo to stage the next release.

    Copies the git history to a safe space, then cleans out the directory.
    """
    cwd = os.getcwd()
    os.chdir(public_repo)

    # remember what things used to be like
    os_helper.call('git checkout master')
    os_helper.call('git pull')
    os_helper.call('cp -r .git {}'.format(staging_dir))
    os.chdir(cwd)

@on_branch
@release_step
def copy_release_branch_to(branch_name, public_repo):
    """Copies the tagged release branch to the given directory."""
    os_helper.call('rsync -aWL --delete . {}'.format(public_repo))

@release_step
def fix_git_history(public_repo, staging_dir):
    """Restores the git history that was copied into the given staging directory."""
    os_helper.call('rm -rf {}/.git'.format(public_repo))
    os_helper.call('cp -r {}/.git {}'.format(staging_dir, public_repo))

@on_branch
@release_step
def remove_internal_submodules(branch_name):
    """Removes and deletes submodules for internal Android and iOS SDKs"""
    os_helper.call('git rm -f mopub-android')
    os_helper.call('git rm -f mopub-ios')

@release_step
def remove_unreleased_code():
    """Remove all the code directories that we shouldn't package in the release."""
    os_helper.call('rm -rf scripts/private')
    os_helper.call('find . -name *.aar* -not -path "/mopub-android-sdk/*" -delete')
    os_helper.call('find . -name unity*.jar -delete')
    os_helper.call('find . -name chartboost*.jar -delete')
    os_helper.call('find . -name dagger*.jar -delete')
    os_helper.call('find . -name javax.inject*.jar -delete')
    os_helper.call('find . -name vungle*.jar -delete')

@release_step
def commit_public_release(version_string):
    """Commits the release on the local public repo, ready for push to origin."""
    os_helper.call('git add -A .')
    commit_all_changes("master", "Release: version {}".format(version_string))
    os_helper.call('git tag -f -a "v{}" -m "Version: {}"'.format(version_string, version_string))

@on_branch
@release_step
def cherry_pick_to_master(branch_name):
    """Cherry picks the last commit from the given branch onto master."""
    os_helper.call('git checkout master')
    os_helper.call('git cherry-pick -x --allow-empty {}'.format(branch_name))
    os_helper.call('git checkout -')

def VersionString(version):
    matched_version = re.match(r"\d+\.\d+\.\d+([+-]\w+)?$", version)
    if matched_version is None:
        raise argparse.ArgumentTypeError(
            ("String {0} does not match the version string pattern!"+ \
            "\nValid Examples:\n\t3.1.1\n\t3.1.1-kit\n\t3.1.1+kit").format(version))
    return matched_version.group(0)

def create_internal_candidate(args):
    """Creates a release candidate built from the latest internal SDKs with the desired versioning.

    This enables release testing to begin prior to the Android and iOS SDKs releasing and once they
    do, create_candidate should be used and release testing continued on that one -- or just a
    sanity test, if release testing was completed.

    In contrast with create_candidate, this method does NOT:
        > cherry pick changes back to master
        > update build scripts for external SDKs
        > remove any internal code"""
    # Verify before performing potentially destructive behavior
    if not args.test:
        print 'This script will push an internal release candidate branch -- built from the latest internal SDKs -- to the private repo.\n '
    else:
        print 'This script is running in TEST mode.  It will not push the release candidate branch.\n '
    raw_input('Press Enter to continue...(Ctrl+C to Cancel)\n')

    try:
        release_branch = create_release_branch(args.version_string, args.release_hash,
                                               internal=True, test=args.test)

        # changes that also apply to private master
        update_mopub_sdk_submodules()
        commit_all_changes(release_branch, "Update to latest Android and iOS MoPub SDKs",
                           "--allow-empty")
        update_sample_app_version(release_branch, args.version_string)
        commit_all_changes(release_branch,
                           "Update bundle version and codes to {}".format(args.version_string))

        # changes only for public repo
        build_wrappers_and_export_unity_package(release_branch)
        commit_release_branch(release_branch, args.version_string, internal=True)
        if not args.test:
            push_private_release_branch(release_branch, args.version_string, internal=True)

        print GREEN + "HOORAY! Internal candidate branch created {}!! Run through release testing then create release candidate once SDKs have been released.".format(release_branch) + END
        exit(0)
    except subprocess.CalledProcessError as e:
        print RED + "RELEASE SCRIPT FAILED" + END
        print e.output
        raise

def create_candidate(args):
    # Verify before performing potentially destructive behavior
    if not args.test:
        print 'This script will push a tagged release candidate branch to the private repo.\n '
    else:
        print 'This script is running in TEST mode.  It will not push the release candidate branch.\n '
    raw_input('Press Enter to continue...(Ctrl+C to Cancel)\n')

    try:
        release_branch = create_release_branch(args.version_string, args.release_hash, test=args.test)

        # changes that also apply to private master
        update_mopub_sdk_submodules()
        commit_all_changes(release_branch, "Update to latest Android and iOS MoPub SDKs",
                           "--allow-empty")
        if not args.test:
            cherry_pick_to_master(release_branch)
        update_sample_app_version(release_branch, args.version_string)
        commit_all_changes(release_branch,
                           "Update bundle version and codes to {}".format(args.version_string))
        if not args.test:
            cherry_pick_to_master(release_branch)

        # changes only for public repo
        make_build_scripts_use_public_sdks(release_branch)
        commit_all_changes(release_branch, "Make build scripts use public SDKs")
        remove_internal_submodules(release_branch)
        strip_private_lines(release_branch)
        build_wrappers_and_export_unity_package(release_branch)
        commit_release_branch(release_branch, args.version_string)
        if not args.test:
            push_private_release_branch(release_branch, args.version_string)

        print GREEN + "HOORAY! Candidate branch created {}!! Run through release testing then promote it.".format(release_branch) + END
        exit(0)
    except subprocess.CalledProcessError as e:
        print RED + "RELEASE SCRIPT FAILED" + END
        print e.output
        raise

def promote_to_release(args):
    # Verify before performing potentially destructive behavior
    print 'This script will take a tagged release candidate and publish it on the public repo.'
    raw_input('Press Enter to continue...(Ctrl+C to Cancel)\n')

    try:
        with os_helper.mktempdir() as git_history_dir:
            prepare_public_repo(PUBLIC_REPO, git_history_dir)
            copy_release_branch_to("release-{}".format(args.version_string), PUBLIC_REPO)
            fix_git_history(PUBLIC_REPO, git_history_dir)

        cwd = os.getcwd()
        os.chdir(PUBLIC_REPO)
        remove_unreleased_code()
        reset_mopub_sdk_submodules()
        update_mopub_sdk_submodules(external_only=True)
        commit_public_release(args.version_string)
        os.chdir(cwd)
        recover_mopub_sdk_submodules('master')

        print GREEN + '\nRelease preparation completed. On private master you have 1 commit to review and push.'
        print '\nOn public master you have 1 commit to review and push. Make sure to push tags:'
        print '\t\'git push --tags origin master\''
        exit(0)
    except subprocess.CalledProcessError as e:
        print RED + "RELEASE SCRIPT FAILED" + END
        print e.output
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="commands",
                                       help="Which release function to perform")

    version_parser = argparse.ArgumentParser(add_help=False)
    version_parser.add_argument("version_string",
                                type=VersionString,
                                help="The release version. Format is like '3.5.2'")
 
    release_hash_parser = argparse.ArgumentParser(add_help=False, parents=[version_parser])
    release_hash_parser.add_argument("--release_hash",
                                     type=str,
                                     help="The git hash of the commit to base the release off of.",
                                     default=None)
    release_hash_parser.add_argument("--test", 
                                     action='store_true',
                                     help="Suppresses cherry picks and push to origin.",
                                     default=False)

    internal_candidate_parser = subparsers.add_parser('internal-candidate', parents=[release_hash_parser])
    internal_candidate_parser.set_defaults(func=create_internal_candidate)

    candidate_parser = subparsers.add_parser('candidate', parents=[release_hash_parser])
    candidate_parser.set_defaults(func=create_candidate)

    promote_parser = subparsers.add_parser('promote', parents=[version_parser])
    promote_parser.set_defaults(func=promote_to_release)

    prog_args = parser.parse_args()
    prog_args.func(prog_args)

    print RED + "SOMETHING UNKNOWN WENT WRONG!" + END
    exit(1)
