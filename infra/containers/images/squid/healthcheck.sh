#!/bin/sh
set -eu

test -s /run/flowform/squid.conf
grep -Eq '^Name:[[:space:]]+squid$' /proc/1/status
squid -k parse -f /run/flowform/squid.conf >/dev/null 2>&1
