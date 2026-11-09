# Hybrid network setup and acceptance checks

This is a manual operator guide for the Cloud Gateway Fiber, UniFi switch and
two-port Proxmox server. Confirm VLANs, subnets, physical interface names and
console recovery before changing the management connection. The addresses below
are proposed values.

| Zone | VLAN / bridge | Guests and addresses |
| --- | --- | --- |
| Trusted administration | VLAN 10 / `vmbr0` | Proxmox `10.10.10.10/24`, gateway `10.10.10.1` |
| Ingress | VLAN 30 / `vmbr1` | Proxy `10.30.0.10/24`, gateway `10.30.0.1` |
| Application | VLAN 40 / `vmbr1` | App `10.40.0.10/24`, gateway `10.40.0.1` |
| Database | Internal-only `vmbr2` | App `172.20.50.10/24`, PostgreSQL `172.20.50.20/24` |

On the switch, make NIC 1 an access port for management VLAN 10 and make NIC 2
a trunk restricted to tags 30 and 40 with an unused native network. Carry the
required tags on the gateway-to-switch uplink. Bind `vmbr0` to NIC 1 and put the
hypervisor's management address and default route there. Bind VLAN-aware
`vmbr1` to NIC 2 with no host address. Make `vmbr2` a bridge with no physical
port, host address or gateway. The DB guest has a single NIC on that bridge and
has no default route. Use a separate build network for Packer's temporary
guest so package and tool downloads can be approved without opening the
runtime VLANs.

## Allow only the required flows

Apply stateful return rules and default-deny between zones and for WAN egress.
Put specific allow rules before general denies. Apply the equivalent IPv6
policy or disable IPv6 and router advertisements where unused. On Proxmox,
enable the node/guest firewall and validate enforcement for the Docker-published
ports. Traffic on the DB bridge requires Proxmox or guest enforcement because
UniFi never sees it.

| Source | Destination | Allow |
| --- | --- | --- |
| Trusted deployment/admin workstation | Proxmox management and guest administration | TCP 8006 to Proxmox, TCP 22 to approved hosts. Scope to the designated management source. |
| Proxy VM | App VLAN IP | TCP 5000 to Gunicorn for Caddy upstream. |
| App VM | Proxy VM | TCP 3128 for Squid, TCP 3500 and 4317 for Alloy. |
| App database NIC | DB VM | TCP 5432 for PostgreSQL. PostgreSQL also limits access by source, database, role and TLS. |
| Approved DB admin path | DB VM | TCP 22 solely for deployment and maintenance. |
| Proxy and app | Site infrastructure | DNS and time to the designated internal endpoints, with DHCP only if used. |
| Proxy VM | Approved external HTTPS endpoints | TCP 443 for AWS, Grafana Cloud and registry access. Include the approved domains served by Squid below. |
| Proxy VM | Cloudflare Tunnel endpoints | TCP/UDP 7844 for HTTP/2 or QUIC. [Cloudflare firewall requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/) |

Keep the database bridge limited to the two guests. The app VM's firewall must
block forwarding **between its two physical interfaces** while permitting the
required Docker bridge traffic. Disable app-container access to Proxmox
management, other internal networks and direct WAN egress. The proxy and app
must be unable to reach Home, NAS, Admin and VPN subnets except for narrowly
scoped stateful return traffic or explicitly approved infrastructure services.
Leave WAN port forwards closed.

For DB staging over SSH, one possible admin path is `ProxyJump` via the app VM
with a dedicated forwarding key, SSH `PermitOpen` restricted to the DB
address and TCP 22, no shell for the forwarding key, and a separate DB login
key. Allow that source in the DB VM firewall and verify both SSH host keys
out of band. The forwarding session is an administrative exception over the
private bridge. It does not require guest IP forwarding.

## App egress through Squid

Install a root-owned `/etc/flowform/allowed-domains.txt` on the proxy with one
exact DNS name per line. Start with the service families below and substitute
the approved region, account and tenant. The regional STS host is useful for
checking workload identity if permitted.

- The configured Auth0 issuer and canonical Management API tenant.
- `rolesanywhere.<region>.amazonaws.com`, `ssm.<region>.amazonaws.com`,
  `secretsmanager.<region>.amazonaws.com`, `kms.<region>.amazonaws.com` and
  `email.<region>.amazonaws.com`.
- `api.ecr.<region>.amazonaws.com`, the exact
  `<account>.dkr.ecr.<region>.amazonaws.com` registry and the ECR layer bucket's
  HTTPS hostname for the region, typically
  `prod-<region>-starport-layer-bucket.s3.<region>.amazonaws.com`.
  [AWS ECR layer storage](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)
- `sts.<region>.amazonaws.com` for the regional STS probe when enabled.

The app uses Squid for host AWS CLI requests, backend HTTPS requests and Docker
ECR pulls, including their S3 layer redirects. Proxy-host AWS, ECR,
cloudflared and Grafana Cloud traffic uses the approved proxy VLAN egress
directly. Keep that allow-list separate from the app's Squid destinations.

## Ingress and acceptance

Cloudflared reaches Caddy over the proxy's internal Docker network. Caddy
listens on HTTP inside that network and forwards over HTTP on the private
proxy-to-app path. Public TLS terminates at Cloudflare. PostgreSQL traffic uses
verified TLS on the database bridge.

If Route 53 is authoritative for the public API hostname, arrange a supported
Cloudflare partial DNS setup before cutover. Cloudflare's partial DNS setup
requires Business or Enterprise. Confirm the actual hostname and certificate
before changing the authoritative record. [Cloudflare partial DNS](https://developers.cloudflare.com/dns/zone-setups/partial-setup/)

Before enabling the public route, check each allowed flow and deliberately test
these denials from the guest or container that would originate the connection.

- App and backend container cannot reach direct public HTTPS, arbitrary HTTPS
  through Squid, or private management and home destinations.
- Proxy reaches the app on TCP 5000 and fails to reach the database on TCP 5432.
  From the proxy, query the app readiness endpoint directly. Test Caddy with the
  configured Host header from inside its container.
- The DB has no IPv4 or IPv6 default route. From the app, verify both roles
  connect with TLS and each can access only its own database. Plaintext and
  unexpected source addresses must fail.
- Only the app reaches published Squid and Alloy ingestion ports. The public
  internet reaches the API through the tunnel alone.
