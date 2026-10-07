#!/bin/sh
exec distrobox enter --name codex-tools -- /usr/bin/python3 "$(dirname "$(readlink -f "$0")")/dropmux.py" "$@"
