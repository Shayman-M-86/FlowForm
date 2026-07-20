#!/usr/bin/env bash
set -Eeuo pipefail

# (Re)generate the TLS-shim leaf (localstack.{crt,key}) signed by the committed
# rehearsal CA (rehearsal-ca.{crt,key}). This one cert terminates TLS for every
# fake-AWS SNI name the shim fronts — the fake-AWS service endpoints AND the
# fake-ECR registry — so its SANs come from san.cnf (see [alt] there).
#
# Why committed, like the CA and the proxy api.crt: the CA is a rehearsal
# throwaway and the private net is local-only. Operators trust rehearsal-ca.crt
# once; leaves signed by it survive VM rebuilds. Re-run this ONLY when san.cnf
# changes (a new fronted host) or the CA is rotated, then re-render cloud-init
# and re-apply terraform (regenerating the leaf forces a LocalStack VM replace).

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DAYS="${DAYS:-3650}"

openssl req -new -newkey rsa:2048 -nodes \
  -config "${HERE}/san.cnf" \
  -keyout "${HERE}/localstack.key" \
  -out "${HERE}/localstack.csr"

openssl x509 -req -in "${HERE}/localstack.csr" \
  -CA "${HERE}/rehearsal-ca.crt" -CAkey "${HERE}/rehearsal-ca.key" \
  -CAcreateserial -days "${DAYS}" \
  -copy_extensions copyall \
  -out "${HERE}/localstack.crt"

rm -f "${HERE}/localstack.csr"
openssl verify -CAfile "${HERE}/rehearsal-ca.crt" "${HERE}/localstack.crt"
openssl x509 -in "${HERE}/localstack.crt" -noout -subject -ext subjectAltName -enddate
