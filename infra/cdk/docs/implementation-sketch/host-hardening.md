# Linux Host Hardening (proxy + app EC2 instances)

Companion to [caddy-ec2-implementation-notes.md](caddy-ec2-implementation-notes.md)
(network shape) and [docker-hardening.md](docker-hardening.md) (what runs
inside Docker). This doc covers the configuration of the Linux machines
themselves.

## Both instances

### Access — no internet-reachable SSH anywhere

The two boxes get **different** access paths, because Session Manager
cannot traverse an HTTPS proxy:

- **Proxy EC2**: SSM Session Manager only. No sshd needed at all —
  disable/remove it (`systemctl disable --now ssh`). The instance role
  includes `AmazonSSMManagedInstanceCore`.
- **App EC2**: reached via a **free EC2 Instance Connect Endpoint**
  (EICE). Nuance: EICE works *over sshd*, so this box keeps sshd —
  locked down as follows:
  - security group inbound 22 **only from the EICE's security group**;
  - `PasswordAuthentication no`, `PermitRootLogin no`;
  - no static authorized_keys — EC2 Instance Connect pushes ephemeral
    public keys per session (60s validity);
  - IAM (`ec2-instance-connect:SendSSHPublicKey`) controls who may
    connect, so access is governed by your `aws login` identity, not
    key files.

Never: SSH open to the internet, shared key files on disk, password
logins.

### Instance metadata

- **IMDSv2 required** (`http_tokens=required`), IMDSv1 disabled.
- **Hop limit 2** on both instances — containers (Caddy's Route 53
  provider, the backend's boto3) need role credentials via IMDS.
- `169.254.169.254` in every `NO_PROXY` (see docker-hardening.md) —
  metadata requests must never route to the proxy.

### IAM

- Two separate slim roles (see the IAM Boundary section of the notes
  doc): proxy = Route 53 zone-scoped + ECR pull + SSM core; app =
  `security_stack.task_role` (secrets/KMS/SES/ECR) + EIC connect.
- No long-lived AWS keys on disk, ever. Instance roles only.

### Patching and package hygiene

- OS security patches on a schedule (SSM Patch Manager once the boxes
  exist; unattended-upgrades as the baseline), reboot after kernel
  updates.
- Docker Engine, Caddy, and Squid images updated deliberately — they ARE
  the attack surface.
- No compilers, git, pip/npm, or build tooling on either box. Images
  build in CI; instances pull from ECR.
- Long-term goal: instances rebuildable from user-data alone (cattle,
  not pets) — makes "patch" = "replace".

### Host firewall (nftables)

Default-deny both directions, mirroring the security groups — the host
firewall catches what a fat-fingered SG change would otherwise expose:

- **Proxy**: inbound 80/443 from anywhere + 3128 from the app instance's
  IP; outbound 443 (ACME, Route 53, allow-listed destinations Squid
  dials), 5000 to the app instance, DNS/NTP.
- **App**: inbound 5000 from the proxy IP + 22 from the EICE ENI;
  outbound 3128 to the proxy, 5432 to RDS, 443 to the S3 gateway
  endpoint prefix list, DNS to the VPC resolver (`10.0.0.2`), NTP to
  `169.254.169.123` (Amazon Time Sync — works without internet).
- Log drops at a sampled rate; alert on repeated denied outbound from
  the app box (that's either a missing allow-list entry or a compromise).

### Filesystem

- Runtime secrets only under tmpfs (`/run/flowform/secrets`, root-owned
  `0600`/`0700`) — never in project folders, never on EBS.
- EBS volumes encrypted (account default on).
- No world-readable config; `/opt/flowform*` owned by root, deploy user
  via group.

### Logging and monitoring

- Ship to CloudWatch (via the awslogs driver or CW agent — remember the
  agent's endpoint must be allow-listed in Squid or the proxy box does
  the shipping): sshd/auth events, Squid allow+deny, Caddy access/error,
  docker events (restart loops), nftables drops.
- Alerts worth having on day one: repeated Squid denials, container
  restart loops, failed EICE/SSM auth, disk >80%.

## Proxy EC2 specifics

- Only public entry AND only controlled exit — harden hardest here; if
  this box falls, the attacker owns both gateways (accepted residual
  risk at this price point, per [cost-model.md](../cost-model.md)).
- Runs exactly two containers (Caddy, Squid) and the SSM agent. Nothing
  else listens.
- Caddy: cert data on a persistent volume, structured logs, security
  headers, proxies ONLY to the app instance's port 5000.
- Squid: bound to the private IP, deny-by-default, CONNECT to 443 only,
  no SSL-Bump, deny log watched (details in docker-hardening.md).

## App EC2 specifics

- No public IP; subnet route table has NO `0.0.0.0/0` (no IGW/NAT) —
  the box *cannot* reach the internet except via Squid. Keep it that
  way: never "temporarily" attach a public IP or NAT route to debug.
- All egress knobs point at the proxy (daemon + containers), with
  `NO_PROXY` correct per docker-hardening.md — including the Python
  no-CIDR caveat.
- Deploys: pull-and-restart only, driven over EICE/SSM-relay from CI;
  no git checkouts, no build artifacts, no leftover credentials.

## Later, if the threat model grows

- SSM Patch Manager + compliance reporting once both boxes are CDK-built.
- CloudTrail is account-level and should be on regardless.
- fail2ban only if SSH ever becomes internet-exposed (it shouldn't).
- IDS/file-integrity tooling, AWS Config drift detection — revisit
  post-launch; they're operational load before then.

## The five invariants

1. The proxy instance is the only internet-facing machine.
2. The app instance fails closed — no backup path to the internet.
3. The outbound proxy denies by default.
4. Security groups, host firewalls, Docker port bindings, and route
   tables all express the same policy independently.
5. No long-lived credentials at rest anywhere (SSH keys included).
