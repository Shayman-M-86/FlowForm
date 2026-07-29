#!/usr/bin/env bash
set -Eeuo pipefail

# (Re)generate the proxy Caddy's TLS leaf for the rehearsal API domain, signed
# by the committed rehearsal CA (tls-shim/ca/rehearsal-ca.{crt,key}).
#
# Why a pre-generated leaf instead of Caddy's `tls internal`: the internal CA
# is minted inside the proxy VM's /data volume, so every VM rebuild produced a
# NEW root and silently invalidated the CA installed in operators' OS trust
# stores (browser ERR_CERT_AUTHORITY_INVALID after each teardown). Anchoring on
# the repo-committed rehearsal CA means operators trust ONE file, once, and it
# survives any rebuild — the same pattern the tls-shim already uses for the
# fake-AWS endpoints.
#
# The outputs are COMMITTED (like localstack.crt/key): the CA is a rehearsal
# throwaway and the private net is local-only. Re-run only if the CA or the
# API domain changes, then re-render cloud-init and re-apply terraform.

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CA_DIR="$(cd -- "${HERE}/../../tls-shim/ca" && pwd)"
API_DOMAIN="${API_DOMAIN:-api.localstack.test}"
DAYS="${DAYS:-3650}"

openssl req -new -newkey rsa:2048 -nodes \
  -keyout "${HERE}/api.key" \
  -subj "/CN=${API_DOMAIN}" \
  -addext "subjectAltName=DNS:${API_DOMAIN}" \
  -out "${HERE}/api.csr"

openssl x509 -req -in "${HERE}/api.csr" \
  -CA "${CA_DIR}/rehearsal-ca.crt" -CAkey "${CA_DIR}/rehearsal-ca.key" \
  -CAcreateserial -days "${DAYS}" \
  -copy_extensions copyall \
  -out "${HERE}/api.crt"

rm -f "${HERE}/api.csr"
openssl verify -CAfile "${CA_DIR}/rehearsal-ca.crt" "${HERE}/api.crt"
openssl x509 -in "${HERE}/api.crt" -noout -subject -ext subjectAltName -enddate
