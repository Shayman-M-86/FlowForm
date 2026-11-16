# UniFi policy register (hybrid)

This is the record of what is **actually configured** on the Cloud Gateway
Fiber for the FlowForm hybrid runtime. [`NETWORK.md`](NETWORK.md) explains the
design and the reasons for it. This file lists the live objects and policies
so changes can be reviewed and drift can be spotted.

- **Snapshot:** 2026-11-16, read from the gateway through the read-only UniFi
  MCP server (`unifi-mcp-server`, local API, site `default`).
- **Scope:** FlowForm and Proxmox networks only. Home-network policies on the
  same gateway are out of scope.
- **Not covered here:** the database bridge (`vmbr2`) never reaches UniFi.
  Proxmox enforces it through
  [`terraform/firewall.tf`](terraform/firewall.tf) and the host firewall
  through [`scripts/setup-firewall.sh`](scripts/setup-firewall.sh).

UniFi is configured by hand. When you change it, update this file in the same
change, then run the [drift check](#drift-check).

## Networks

| Network | VLAN | Subnet / gateway | DHCP | IPv6 | Zone |
| --- | --- | --- | --- | --- | --- |
| Proxmox Management | 10 | `10.10.20.0/24`, gateway `10.10.20.1` | Off | None | Proxmox Management |
| FlowForm Ingress | 30 | `10.30.0.0/24`, gateway `10.30.0.1` | Off | None | FlowForm Ingress |
| FlowForm App | 40 | `10.40.0.0/24`, gateway `10.40.0.1` | Off | None | FlowForm App |
| Unused Native | 999 | VLAN only, no subnet | — | — | — |

Guests use static addresses: proxy `10.30.0.10`, app `10.40.0.10`. The admin
workstation is `192.168.68.106` on the home `Default` network (Internal zone).

## Objects

| Object | Type | Members | Used by |
| --- | --- | --- | --- |
| `FlowForm Proxy and Telemetry.` | Port group | 3128 Squid, 3500 Alloy logs, 4317 Alloy OTLP | App → Squid and Alloy |
| `region1-2.v2.argotunnel.com` | Address group | 20 Cloudflare Tunnel edge IPs (`198.41.192.x`, `198.41.200.x`) | Ingress → Cloudflare Tunnel |
| `region1.v2.argotunnel.com`, `region2.v2.argotunnel.com` | Address groups | The two halves of the list above | Nothing (unused) |
| `HTTPS destination list` | Domain group | An older 10-domain copy of the egress list | Nothing. The HTTPS policy uses its own inline list; see [findings](#findings) |
| `Proxmox Admin` | Port group | 8006, 22 | Nothing; see [findings](#findings) |

## Policies

Custom policies only, in evaluation order (lower index first). The zone
defaults behind them block everything between FlowForm zones and other
internal zones, VPN, Hotspot and DMZ. Every zone also gets the predefined
"Block Invalid Traffic" and "Allow mDNS" policies and the matching return rules
for each allow.

### From FlowForm Ingress (proxy `10.30.0.10`)

| Index | Name | Action | Destination | Protocol / ports |
| --- | --- | --- | --- | --- |
| 10000 | FlowForm-Ingress to FlowForm API | Allow | App `10.40.0.10` | TCP 5000 |
| 10000 | FlowForm-Ingress to Cloudflare Tunnel | Allow | External, `region1-2.v2.argotunnel.com` | TCP/UDP 7844, IPv4 |
| 10000 | FlowForm-Ingress DNS | Allow | Gateway `10.30.0.1` | TCP/UDP 53 |
| 10001 | FlowForm-Ingress NTP | Allow | External `162.159.200.1`, `162.159.200.123` | UDP 123, IPv4 |
| 10001 | FlowForm-Block Ingress to Gateway | Block | Gateway, any | All |
| 10002 | FlowForm-Ingress to Approved HTTPS | Allow | External, [domain list](#proxy-https-egress-domains) | TCP 443 |
| 10003 | FlowForm-Block Ingress to Internet | Block | External, any | All |

### From FlowForm App (app `10.40.0.10`)

| Index | Name | Action | Destination | Protocol / ports |
| --- | --- | --- | --- | --- |
| 10000 | FlowForm-App to Squid and Alloy | Allow | Proxy `10.30.0.10` | TCP, `FlowForm Proxy and Telemetry.` |
| 10000 | FlowForm-App DNS | Allow | Gateway `10.40.0.1` | TCP/UDP 53 |
| 10000 | FlowForm-Block App to Internet | Block | External, any | All |
| 10001 | FlowForm-App to Ingress NTP | Allow | Proxy `10.30.0.10` | UDP 123, IPv4 |
| 10001 | FlowForm-Block App to Gateway | Block | Gateway, any | All |

### From Internal (admin workstation `192.168.68.106`)

| Index | Name | Action | Destination | Protocol / ports |
| --- | --- | --- | --- | --- |
| 10000 | FlowForm-Admin SSH to FlowForm Ingress | Allow | Proxy `10.30.0.10` | TCP 22, IPv4 |
| 10000 | FlowForm-Admin SSH to FlowForm App | Allow | App `10.40.0.10` | TCP 22, IPv4 |
| 10000 | Proxmox-Allow Admin Workstation to Proxmox | Allow | Proxmox Management, any | **All protocols**; see [findings](#findings) |

### From Proxmox Management

No custom policies. The zone defaults allow it out to the gateway and the
internet, and block it from reaching Internal, FlowForm and the other zones.

## Proxy HTTPS egress domains

The single list in **FlowForm-Ingress to Approved HTTPS** (TCP 443, custom web
domains). It must contain every domain in Squid's
[`allowed-domains.txt`](../../containers/images/squid/allowed-domains.txt),
because Squid's outbound connections leave from the proxy VM. The remaining
entries are for the proxy host's own traffic.

**Mirrors Squid** (the app's traffic through Squid):

- `auth.flow-form.com.au`, `dev-3wccg4jx4o5wvedn.au.auth0.com`
- `rolesanywhere.ap-southeast-2.amazonaws.com`, `ssm.ap-southeast-2.amazonaws.com`,
  `secretsmanager.ap-southeast-2.amazonaws.com`, `kms.ap-southeast-2.amazonaws.com`,
  `email.ap-southeast-2.amazonaws.com`
- `api.ecr.ap-southeast-2.amazonaws.com`, `908123139858.dkr.ecr.ap-southeast-2.amazonaws.com`,
  `prod-ap-southeast-2-starport-layer-bucket.s3.ap-southeast-2.amazonaws.com`
- `api.openai.com` (AI survey import, added 2026-11-16)

**Proxy host only** (not in Squid):

- Grafana Cloud: `logs-prod-026.grafana.net`, `tempo-prod-16-prod-au-southeast-1.grafana.net`
- cloudflared: `api.cloudflare.com`, `update.argotunnel.com`, `github.com`
- Docker Hub: `auth.docker.io`, `registry-1.docker.io`, `production.cloudfront.docker.com`
  (still an open decision in the cutover notes)

## Findings

Found in the 2026-11-16 snapshot. These are differences between the live
configuration, the Squid list and `NETWORK.md`. None was changed.

1. **Squid allows two domains that UniFi blocks:**
   `ssmmessages.ap-southeast-2.amazonaws.com` and
   `ec2messages.ap-southeast-2.amazonaws.com`. SSM Session Manager and Run
   Command through Squid therefore fail on hybrid. Add them to the HTTPS
   policy if you use those features on hybrid; otherwise this is harmless.
2. **Admin access to Proxmox allows all protocols.** `NETWORK.md` specifies TCP
   8006 and 22 only. The `Proxmox Admin` port group already holds those ports
   but no policy uses it. Narrow the policy to that group.
3. **Proxmox Management has unrestricted internet egress** through the zone
   default. `NETWORK.md` doesn't constrain the hypervisor's own egress, so this
   is a decision to make rather than a violation.
4. **Stale `HTTPS destination list` domain group.** It doesn't match the live
   list and nothing uses it. Delete it, or point the HTTPS policy at it and keep
   the full list there, so the list exists in only one place.
5. **`NETWORK.md` had the wrong management subnet** (`10.10.10.0/24`). The live
   network is `10.10.20.0/24`, and `NETWORK.md` has been corrected. Confirm the
   Proxmox host's own address on it.

## Drift check

Run this whenever `allowed-domains.txt` or this file changes, and before a
hybrid release. Ask an agent with the UniFi MCP server to compare the live
configuration with this file, or compare by hand in the console:

1. `list_firewall_policies` for site `default`, filtered by each FlowForm zone
   as the source, compared with the [policy tables](#policies).
2. The `web_domains` of **FlowForm-Ingress to Approved HTTPS**, compared with
   Squid's `allowed-domains.txt`. Every Squid domain must be present.
3. `list_vlans` and `list_firewall_groups`, compared with
   [Networks](#networks) and [Objects](#objects).

The MCP server is read-only (`read_only: true`, viewer role), so it can't
change the gateway. Make changes in the UniFi console, then update this file.
