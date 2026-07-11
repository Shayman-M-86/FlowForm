# LocalStack TLS shim (rehearsal only)

Fronts LocalStack with **TLS on :443 under AWS-style SNI names** so the app box
reaches fake-AWS exactly the way it reaches real AWS — and so Squid's
`CONNECT :443` + SNI allow-list applies unchanged. Runs on the **ls-vm (230)**,
beside LocalStack (baked into template 9001; auto-starts via
`flowform-tls-shim.service`).

```
app-vm → Squid (CONNECT <svc>.localstack.test:443, SNI allow-list)
       → TLS tunnel → shim (Caddy, :443) → terminate TLS → LocalStack :4566
```

The **only** deltas from prod are the hostnames (`*.localstack.test`) and a
rehearsal-only CA. Everything else — CONNECT/443/SNI, TLS termination at the
"AWS endpoint" — is identical. Never read a green shim as real-AWS proof.

## Files

| File | What |
|---|---|
| `Caddyfile` | terminates TLS for `secretsmanager/ssm/kms.localstack.test`, reverse-proxies to LocalStack at `10.10.10.30:4566` |
| `docker-compose.tls-shim.yml` | runs `caddy:2-alpine` (host networking, binds :443) |
| `ca/rehearsal-ca.crt` / `.key` | **throwaway rehearsal CA** (see warning) |
| `ca/localstack.crt` / `.key` | server cert for the 3 SNI names, signed by the CA |
| `ca/san.cnf` | openssl SAN config used to (re)generate the server cert |

The authoritative copies of the Caddyfile + server cert are **baked into**
`../runtime LocalStack first-boot configuration or a future Proxmox-only Packer fixture variant` (base64). Keep them in
sync if you regenerate.

## ⚠️ The CA is a committed throwaway — rehearsal only

`ca/rehearsal-ca.key` is a **private key committed on purpose** for the local
rehearsal. This is safe ONLY because:

- It signs certs for `*.localstack.test`, names that resolve to a LocalStack VM
  on a private, un-routed net (`vmbr10`) — never a real domain.
- It is trusted ONLY on the rehearsal's own app box (added to its trust store at
  build time), never on any real machine.
- LocalStack accepts any credentials; there is nothing real behind it.

**Never** reuse this CA outside the rehearsal, and never add it to a trust store
that also talks to the real internet. Real EC2 uses real AWS TLS with the public
CA bundle — no shim, no custom CA.

## Regenerating the CA/cert

```sh
cd ca
openssl genrsa -out rehearsal-ca.key 2048
openssl req -x509 -new -nodes -key rehearsal-ca.key -sha256 -days 3650 \
  -subj "/CN=FlowForm Rehearsal CA (throwaway)/O=FlowForm Rehearsal" -out rehearsal-ca.crt
openssl genrsa -out localstack.key 2048
openssl req -new -key localstack.key -out localstack.csr -config san.cnf
openssl x509 -req -in localstack.csr -CA rehearsal-ca.crt -CAkey rehearsal-ca.key \
  -CAcreateserial -days 3650 -sha256 -extensions v3_req -extfile san.cnf -out localstack.crt
```

Then re-embed `Caddyfile` + `localstack.crt/.key` (base64) into the ls builder
user-data and rebuild template 9001.
