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
    "common/kolibri/dist/django/contrib/redirects/locale",
    "common/kolibri/dist/django/contrib/sessions/locale",
    "common/kolibri/dist/django/contrib/sites/locale",
    "common/kolibri/dist/django_filters/locale",
    "common/kolibri/dist/mptt/locale",
    "common/kolibri/dist/rest_framework/locale",
]

REMOVE_GLOBS = [
    # Only the Kolibri bundled C extensions for this build are needed. Keep the list of
    # pruned ABIs and Python versions in sync with build.gradle.kts.
    "common/kolibri/dist/cext/*/*/armv6l",
    "common/kolibri/dist/cext/*/*/i686",
    "common/kolibri/dist/cext/*/*/aarch64",
    "common/kolibri/dist/cext/cp27",
    "common/kolibri/dist/cext/cp36",
    "common/kolibri/dist/cext/cp37",
    "common/kolibri/dist/cext/cp38",
    # Keep "common/kolibri/dist/cext/cp39" to match Chaquopy Python version 3.9 in
    # app/build.gradle.kts.
    "common/kolibri/dist/cext/cp311",
    "common/kolibri/dist/cext/*/Windows",
    # Remove unneeded explore plugin components. JS source files aren't needed since
    # only the webpacked apps in static are used at runtime. The bundled loadingScreen
    # isn't needed as loading-screen.zip is added as an asset.
    "common/kolibri_explore_plugin/assets",
    "common/kolibri_explore_plugin/loadingScreen",
    # Kolibri doesn't use several large django contrib apps.
    "common/kolibri/dist/django/contrib/gis",
    "common/kolibri/dist/django/contrib/humanize",
    "common/kolibri/dist/django/contrib/postgres",
    # Tests aren't needed.
    "common/kolibri/core/*/test",
    "common/kolibri/utils/tests",
    "common/kolibri/dist/cheroot/test",
    "common/kolibri/dist/colorlog/tests",
    "common/kolibri/dist/django_js_reverse/tests",
    "common/kolibri/dist/future/backports/test",
    "common/kolibri/dist/future/moves/test",
    "common/kolibri/dist/future/tests",
    "common/kolibri/dist/ipware/tests",
    "common/kolibri/dist/importlib_resources/tests",
    "common/kolibri/dist/json_schema_validator/tests",
    "common/kolibri/dist/magicbus/test",
    "common/kolibri/dist/more_itertools/tests",
    "common/kolibri/dist/past/tests",
    "common/kolibri/dist/sqlalchemy/testing",
    "common/kolibri/plugins/*/test",
    "common/kolibri_explore_plugin/test",
    # JS map files are only for debugging.
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
