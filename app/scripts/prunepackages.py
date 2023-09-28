#!/usr/bin/env python3
import logging
import os
from argparse import ArgumentParser
from glob import iglob
from pathlib import Path
from shutil import rmtree

logger = logging.getLogger("prune")

INCLUDE_LOCALES_DIRS = ["common/kolibri/locale"]

REMOVE_LOCALES_DIRS = [
    "common/kolibri/dist/django/conf/locale",
    "common/kolibri/dist/django/contrib/admin/locale",
    "common/kolibri/dist/django/contrib/admindocs/locale",
    "common/kolibri/dist/django/contrib/auth/locale",
    "common/kolibri/dist/django/contrib/contenttypes/locale",
    "common/kolibri/dist/django/contrib/flatpages/locale",
    "common/kolibri/dist/django/contrib/gis/locale",
    "common/kolibri/dist/django/contrib/humanize/locale",
    "common/kolibri/dist/django/contrib/postgres/locale",
    "common/kolibri/dist/django/contrib/redirects/locale",
    "common/kolibri/dist/django/contrib/sessions/locale",
    "common/kolibri/dist/django/contrib/sites/locale",
    "common/kolibri/dist/django_filters/locale",
    "common/kolibri/dist/mptt/locale",
    "common/kolibri/dist/rest_framework/locale",
]

REMOVE_GLOBS = [
    "common/kolibri/dist/cext/cp27",
    "common/kolibri/dist/cext/cp36",
    "common/kolibri/dist/cext/cp37",
    "common/kolibri/dist/cext/cp38",
    "common/kolibri/dist/cext/*/Windows",
    "common/kolibri/dist/cheroot/test",
    "common/kolibri/dist/magicbus/test",
    "common/kolibri/dist/colorlog/tests",
    "common/kolibri/dist/django_js_reverse/tests",
    "common/kolibri/dist/future/tests",
    "common/kolibri/dist/ipware/tests",
    "common/kolibri/dist/more_itertools/tests",
    "common/kolibri/dist/past/tests",
    "common/kolibri/dist/sqlalchemy/testing",
    "**/*.js.map",
    # Chaquopy currently precompiles modules but also keeps the original module
    # for packages specified in extractPackages. We don't want to disable
    # precompiling since other packages depend on it, so we strip out the
    # unwanted precompiled modules here.
    #
    # https://github.com/chaquo/chaquopy/issues/978
    "common/kolibri/**/*.pyc",
    "common/kolibri_explore_plugin/**/*.pyc",
]


def get_locales(locales_dir):
    return (entry for entry in locales_dir.iterdir() if entry.is_dir())


def prune(pkgroot, dry_run=False):
    include_locale_names = set(["en"])
    for subdir in INCLUDE_LOCALES_DIRS:
        locales_dir = pkgroot / subdir
        locales = get_locales(locales_dir)
        include_locale_names.update(locale.name for locale in locales)

    logger.info("Included locales: {}".format(include_locale_names))

    for subdir in REMOVE_LOCALES_DIRS:
        cleanup_dir = pkgroot / subdir
        locales = get_locales(cleanup_dir)
        remove_locales = (
            locale for locale in locales if locale.name not in include_locale_names
        )
        for remove_locale in remove_locales:
            logger.info("Removing locale '{}'".format(remove_locale))
            if not dry_run:
                rmtree(remove_locale)

    for pattern in REMOVE_GLOBS:
        logger.info(f"Matching pattern '{pattern}'")
        for match in iglob(f"{pkgroot}/{pattern}", recursive=True):
            remove_path = Path(match)
            if remove_path.is_dir():
                logger.info(f"Removing matched directory '{remove_path}'")
                if not dry_run:
                    rmtree(remove_path)
            else:
                logger.info(f"Removing matched file '{remove_path}'")
                if not dry_run:
                    os.unlink(remove_path)


def main():
    parser = ArgumentParser(description="Prune python packages")
    parser.add_argument(
        "-p",
        "--pkgroot",
        default=Path("."),
        type=Path,
        help="package root directory",
    )
    parser.add_argument(
        "-r",
        "--report",
        type=Path,
        help="report file path",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="only show what would be removed",
    )
    args = parser.parse_args()

    logging_config = {"level": logging.INFO}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        logging_config.update(
            {
                "filename": os.fspath(args.report),
                "filemode": "w",
            }
        )
    logging.basicConfig(**logging_config)

    prune(args.pkgroot.resolve(), args.dry_run)


if __name__ == "__main__":
    main()
