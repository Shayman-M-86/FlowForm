#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
REHEARSAL="${REPO_ROOT}/infra/deployment/proxmox/scripts/rehearsal"
TLS_LIBRARY="${REPO_ROOT}/infra/deployment/proxmox/scripts/lib/rehearsal-tls.sh"
TERRAFORM_LIBRARY="${REPO_ROOT}/infra/deployment/proxmox/scripts/lib/rehearsal-terraform.sh"
SAN_SOURCE="${REPO_ROOT}/infra/containers/runtime/proxmox/rehearsal/services/tls-shim/ca/san.cnf"
API_GENERATOR="${REPO_ROOT}/infra/containers/runtime/proxmox/rehearsal/services/caddy/certs/generate-api-cert.sh"
LOCALSTACK_GENERATOR="${REPO_ROOT}/infra/containers/runtime/proxmox/rehearsal/services/tls-shim/ca/generate-localstack-cert.sh"
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/flowform-rehearsal-tls-test.XXXXXX")"
trap 'rm -rf -- "${TEST_DIR}"' EXIT

CA_DIR="${TEST_DIR}/ca"
API_DIR="${TEST_DIR}/api"
SAN_CONFIG="${TEST_DIR}/san.cnf"
mkdir -p -- "${CA_DIR}" "${API_DIR}"
cp -- "${SAN_SOURCE}" "${SAN_CONFIG}"

run_tls() {
  env \
    REHEARSAL_COLOR=never \
    REHEARSAL_TLS_CA_DIR="${CA_DIR}" \
    REHEARSAL_TLS_API_DIR="${API_DIR}" \
    REHEARSAL_TLS_SAN_CONFIG="${SAN_CONFIG}" \
    "${REHEARSAL}" tls
}

output="$(run_tls 2>&1)"
grep -F 'created machine-local rehearsal CA and leaf certificates' <<<"${output}" >/dev/null

for file in \
  "${CA_DIR}/rehearsal-ca.key" \
  "${CA_DIR}/rehearsal-ca.crt" \
  "${CA_DIR}/localstack.key" \
  "${CA_DIR}/localstack.crt" \
  "${API_DIR}/api.key" \
  "${API_DIR}/api.crt"; do
  [[ -s "${file}" ]] || { printf 'missing generated TLS file: %s\n' "${file}" >&2; exit 1; }
done

[[ "$(stat -c '%a' "${CA_DIR}/rehearsal-ca.key")" == 600 ]]
[[ "$(stat -c '%a' "${CA_DIR}/localstack.key")" == 600 ]]
[[ "$(stat -c '%a' "${API_DIR}/api.key")" == 600 ]]
[[ "$(stat -c '%a' "${CA_DIR}/rehearsal-ca.crt")" == 644 ]]
grep -F 'CA:TRUE' < <(openssl x509 -in "${CA_DIR}/rehearsal-ca.crt" -noout -text) >/dev/null
openssl verify -CAfile "${CA_DIR}/rehearsal-ca.crt" \
  "${CA_DIR}/localstack.crt" "${API_DIR}/api.crt" >/dev/null
openssl x509 -in "${API_DIR}/api.crt" -checkhost api.localstack.test -noout >/dev/null
for hostname in \
  secretsmanager.localstack.test \
  ssm.localstack.test \
  kms.localstack.test \
  registry.localstack.test; do
  openssl x509 -in "${CA_DIR}/localstack.crt" -checkhost "${hostname}" -noout >/dev/null
done

ca_checksum="$(sha256sum "${CA_DIR}/rehearsal-ca.crt" | awk '{print $1}')"
leaf_checksum="$(sha256sum "${CA_DIR}/localstack.crt" | awk '{print $1}')"
output="$(run_tls 2>&1)"
grep -F 'machine-local rehearsal TLS material is valid' <<<"${output}" >/dev/null
[[ "$(sha256sum "${CA_DIR}/rehearsal-ca.crt" | awk '{print $1}')" == "${ca_checksum}" ]]
[[ "$(sha256sum "${CA_DIR}/localstack.crt" | awk '{print $1}')" == "${leaf_checksum}" ]]

# Keep the former leaf-generator entrypoints working without retaining a
# second implementation or changing a valid trust anchor.
for compatibility_entrypoint in "${API_GENERATOR}" "${LOCALSTACK_GENERATOR}"; do
  output="$(
    env \
      REHEARSAL_COLOR=never \
      REHEARSAL_TLS_CA_DIR="${CA_DIR}" \
      REHEARSAL_TLS_API_DIR="${API_DIR}" \
      REHEARSAL_TLS_SAN_CONFIG="${SAN_CONFIG}" \
      "${compatibility_entrypoint}" 2>&1
  )"
  grep -F 'machine-local rehearsal TLS material is valid' <<<"${output}" >/dev/null
done
[[ "$(sha256sum "${CA_DIR}/rehearsal-ca.crt" | awk '{print $1}')" == "${ca_checksum}" ]]

rm -f -- "${CA_DIR}/localstack.key" "${CA_DIR}/localstack.crt"
output="$(run_tls 2>&1)"
grep -F 'repaired rehearsal leaf certificates without changing the CA trust anchor' <<<"${output}" >/dev/null
[[ "$(sha256sum "${CA_DIR}/rehearsal-ca.crt" | awk '{print $1}')" == "${ca_checksum}" ]]
openssl verify -CAfile "${CA_DIR}/rehearsal-ca.crt" "${CA_DIR}/localstack.crt" >/dev/null

# Terraform preparation must create TLS inputs before it evaluates any of its
# other fresh-checkout prerequisites. Stop it at a deliberately missing env
# file so this remains hermetic and cannot contact a Proxmox host.
AUTO_CA_DIR="${TEST_DIR}/auto-ca"
AUTO_API_DIR="${TEST_DIR}/auto-api"
mkdir -p -- "${AUTO_CA_DIR}" "${AUTO_API_DIR}"
set +e
output="$(
  env \
    REHEARSAL_COLOR=never \
    REHEARSAL_TLS_CA_DIR="${AUTO_CA_DIR}" \
    REHEARSAL_TLS_API_DIR="${AUTO_API_DIR}" \
    REHEARSAL_TLS_SAN_CONFIG="${SAN_CONFIG}" \
    DEV_BACKEND_ENV="${TEST_DIR}/does-not-exist.env" \
    "${REHEARSAL}" terraform validate 2>&1
)"
status=$?
set -e
[[ ${status} -ne 0 ]]
grep -F 'created machine-local rehearsal CA and leaf certificates' <<<"${output}" >/dev/null
grep -F 'dev backend env not found' <<<"${output}" >/dev/null
[[ -s "${AUTO_CA_DIR}/rehearsal-ca.crt" ]]

printf 'invalid certificate\n' >"${CA_DIR}/rehearsal-ca.crt"
set +e
output="$(run_tls 2>&1)"
status=$?
set -e
[[ ${status} -ne 0 ]]
grep -F 'it will not be overwritten automatically' <<<"${output}" >/dev/null

bash -n "${TLS_LIBRARY}" "${TERRAFORM_LIBRARY}" "${REHEARSAL}"

printf 'rehearsal TLS bootstrap tests passed\n'
