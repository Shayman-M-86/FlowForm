#!/usr/bin/env bash
# dns-sync check: matching zones pass; missing, extra, changed and unexpectedly
# proxied records fail; Cloudflare-owned names are ignored on both sides.
set -Eeuo pipefail
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
TOOL="${REPO_ROOT}/infra/deployment/dns/dns-sync"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT
export FLOWFORM_DNS_ROUTE53_FILE="${TEST_DIR}/r53.json" FLOWFORM_DNS_CLOUDFLARE_FILE="${TEST_DIR}/cf.json"

cat > "${FLOWFORM_DNS_ROUTE53_FILE}" <<'JSON'
{"ResourceRecordSets": [
  {"Name": "flow-form.com.au.", "Type": "NS", "TTL": 172800, "ResourceRecords": [{"Value": "ns-1.awsdns-00.com."}]},
  {"Name": "flow-form.com.au.", "Type": "A", "AliasTarget": {"DNSName": "d1.cloudfront.net.", "HostedZoneId": "Z2", "EvaluateTargetHealth": false}},
  {"Name": "flow-form.com.au.", "Type": "TXT", "TTL": 300, "ResourceRecords": [{"Value": "\"google-site-verification=abc\""}]},
  {"Name": "mail.flow-form.com.au.", "Type": "MX", "TTL": 300, "ResourceRecords": [{"Value": "10 feedback-smtp.example.com"}]},
  {"Name": "auth.flow-form.com.au.", "Type": "CNAME", "TTL": 300, "ResourceRecords": [{"Value": "tenant.edge.auth0.com"}]},
  {"Name": "api-staging.flow-form.com.au.", "Type": "A", "TTL": 60, "ResourceRecords": [{"Value": "203.0.113.10"}]}
]}
JSON
write_cf() { # $@ = extra jq filters applied to the matching Cloudflare zone
  jq -n "{result: [
    {type: \"NS\", name: \"flow-form.com.au\", content: \"x.ns.cloudflare.com\", proxied: false},
    {type: \"CNAME\", name: \"flow-form.com.au\", content: \"d1.cloudfront.net\", proxied: false},
    {type: \"TXT\", name: \"flow-form.com.au\", content: \"\\\"google-site-verification=abc\\\"\", proxied: false},
    {type: \"MX\", name: \"mail.flow-form.com.au\", content: \"feedback-smtp.example.com\", priority: 10, proxied: false},
    {type: \"CNAME\", name: \"auth.flow-form.com.au\", content: \"tenant.edge.auth0.com\", proxied: false},
    {type: \"CNAME\", name: \"api-staging.flow-form.com.au\", content: \"abc.cfargotunnel.com\", proxied: true}
  ]} | ${1:-.}" > "${FLOWFORM_DNS_CLOUDFLARE_FILE}"
}
expect_fail() { # $1 = label, $2 = expected report fragment
  local out
  if out="$("${TOOL}" check 2>&1)"; then printf 'expected drift (%s) but check passed\n' "$1" >&2; exit 1; fi
  grep -Fq "$2" <<<"${out}" || { printf 'missing "%s" for %s:\n%s\n' "$2" "$1" "${out}" >&2; exit 1; }
}

write_cf
"${TOOL}" check | grep -Fq 'Cloudflare matches Route 53' # owned api-staging ignored both sides

write_cf 'del(.result[] | select(.name == "auth.flow-form.com.au"))'
expect_fail missing 'missing in Cloudflare:  CNAME auth.flow-form.com.au'

write_cf '.result += [{type: "A", name: "old.flow-form.com.au", content: "198.51.100.1", proxied: false}]'
expect_fail extra 'only in Cloudflare:     A old.flow-form.com.au'

write_cf '(.result[] | select(.type == "MX")).priority = 20'
expect_fail changed 'MX mail.flow-form.com.au 20'

write_cf '(.result[] | select(.name == "auth.flow-form.com.au")).proxied = true'
expect_fail proxied 'proxied but not owned:  CNAME auth.flow-form.com.au'

printf '[test-dns-sync] PASS\n'
