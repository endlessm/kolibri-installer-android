#!/bin/bash
# Copyright 2021-2023 Endless OS Foundation LLC
# SPDX-License-Identifier: GPL-2.0-or-later

set -e

SCRIPTDIR=$(dirname "$0")
PROPERTIES=$(realpath "$(dirname "$SCRIPTDIR")/gradle.properties")

ARGS=$(getopt -n "$0" -o h -l help -- "$@")
eval set -- "$ARGS"

usage() {
    cat <<EOF
Usage: $0 VERSION
Update the kolibri-explore-plugin version in $PROPERTIES

  -h, --help	display this message and exit
EOF
}

while true; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "error: Unrecognized option \"$1\"" >&2
            exit 1
            ;;
    esac
done

if [ $# -lt 1 ]; then
  echo "error: No version specified" >&2
  usage >&2
  exit 1
fi
VERSION=$1

sed -ri "s/^(exploreVersion)=.*/\1=${VERSION}/" "$PROPERTIES"
