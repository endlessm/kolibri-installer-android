#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
from argparse import ArgumentParser


def kolibri_version(pkgdir):
    """
    Returns the major.minor version of Kolibri if it exists
    """
    version_path = os.path.join(pkgdir, "kolibri/VERSION")
    with open(version_path, "r") as version_file:
        # p4a only likes digits and decimals
        version = version_file.read().strip()
        # For git dev builds, shorten the version by removing date details:
        if "+git" not in version:
            return version
        return version.split("+git")[0]


def explore_plugin_version_name(pkgdir):
    version_path = os.path.join(pkgdir, "kolibri_explore_plugin/VERSION")
    with open(version_path, "r") as version_name_file:
        return version_name_file.read().strip()


def explore_plugin_version(pkgdir):
    # kolibri-explore-plugin v6.27.0 and newer store the version in a separate
    # file.
    version_path = os.path.join(pkgdir, "kolibri_explore_plugin/_version.py")
    spec = importlib.util.spec_from_file_location("_version", version_path)
    if not spec:
        raise ImportError

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return getattr(module, "__version__")


def explore_plugin_simple_version(pkgdir):
    full_version = explore_plugin_version(pkgdir)
    [major, minor, patch, *_] = full_version.split(".")
    if patch == "0":
        return ".".join([major, minor])
    return full_version


def commit_hash():
    """
    Returns the number of commits of the Kolibri Android repo

    Returns 0 if something fails.
    TODO hash, unless there's a tag. Use alias to annotate
    """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.Popen(
        "git rev-parse --short HEAD",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
    )
    return p.communicate()[0].rstrip()


def git_tag():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.Popen(
        "git tag --points-at {}".format(commit_hash()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
    )
    return p.communicate()[0].rstrip()


def get_version_name(pkgdir):
    """
    Returns the user-visible version to be used for the Android app.
    """
    return "{} {}".format(
        explore_plugin_version_name(pkgdir),
        explore_plugin_simple_version(pkgdir),
    )


def get_ek_version(pkgdir):
    """
    Returns detailed version of major modules for debugging.
    """
    android_version_indicator = git_tag() or commit_hash()
    return "{}-{}-{}".format(
        explore_plugin_version(pkgdir),
        kolibri_version(pkgdir),
        android_version_indicator,
    )


def get_version_data(pkgdir):
    version_name = get_version_name(pkgdir)
    ek_version = get_ek_version(pkgdir)
    return {
        "versionName": version_name,
        "ekVersion": ek_version,
    }


if __name__ == "__main__":
    ap = ArgumentParser(description="Output version information")
    ap.add_argument(
        "-o",
        "--output",
        help="path to save JSON output",
    )
    ap.add_argument(
        "-d",
        "--pkgdir",
        default=".",
        help="path to package directory (default: %(default)s)",
    )
    ap.add_argument(
        "-c",
        "--version-code",
        type=int,
        help="versionCode value to include in output",
    )
    args = ap.parse_args()

    data = get_version_data(args.pkgdir)
    if args.version_code:
        data["versionCode"] = args.version_code
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    else:
        json.dump(data, sys.stdout, indent=2, sort_keys=True)
