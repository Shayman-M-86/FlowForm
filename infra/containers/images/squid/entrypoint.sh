#!/bin/sh
set -eu

template=/etc/squid/squid.conf.template
rendered=/run/flowform/squid.conf

: "${SQUID_APP_SOURCE_CIDR:?set SQUID_APP_SOURCE_CIDR}"
: "${SQUID_DB_BOOTSTRAP_SOURCE_CIDR:=127.0.0.1/32}"

case "${SQUID_APP_SOURCE_CIDR}" in
  *[!0-9./:a-fA-F]*)
    printf 'invalid SQUID_APP_SOURCE_CIDR: %s\n' "${SQUID_APP_SOURCE_CIDR}" >&2
    exit 64
    ;;
esac

case "${SQUID_DB_BOOTSTRAP_SOURCE_CIDR}" in
  *[!0-9./:a-fA-F]*)
    printf 'invalid SQUID_DB_BOOTSTRAP_SOURCE_CIDR: %s\n' \
      "${SQUID_DB_BOOTSTRAP_SOURCE_CIDR}" >&2
    exit 64
    ;;
esac

install -d -m 0755 /run/flowform
sed \
  -e "s|__APP_SOURCE_CIDR__|${SQUID_APP_SOURCE_CIDR}|g" \
  -e "s|__DB_BOOTSTRAP_SOURCE_CIDR__|${SQUID_DB_BOOTSTRAP_SOURCE_CIDR}|g" \
  "${template}" > "${rendered}"

squid -k parse -f "${rendered}"

install -d -o proxy -g proxy -m 0755 /var/log/squid
su -s /bin/sh -c \
  'touch /var/log/squid/access.log' proxy
su -s /bin/sh -c \
  'exec tail -n 0 -F /var/log/squid/access.log' proxy &

exec squid -N -f "${rendered}"
