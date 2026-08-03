Here is the full practical gotcha list, combining the speaker’s direct mistakes with the important warnings that follow from his setup. 

# Biggest failure points

## 1. Packer cannot reach Proxmox

A Packer crash or vague error may actually just mean the initial Proxmox API connection failed.

Check:

* Proxmox IP address or hostname
* Port `8006`
* API path
* API token ID
* API token secret
* Token permissions
* TLS settings
* Firewall access between the build machine and Proxmox

The expected API endpoint is generally:

```text
https://proxmox-host:8006/api2/json
```

A connection failure happens before Packer creates the VM, so do not start debugging Ubuntu or Cloud-Init yet.

---

## 2. Incorrect API token format

The Proxmox token identifier must use the correct structure, including the username and token name separated by an exclamation mark.

Conceptually:

```text
user@realm!token-name
```

The token secret is separate.

A typo in either value will stop authentication.

---

## 3. API token secret is only shown once

Proxmox only displays the token secret when the token is created.

Store it securely immediately.

If it is lost, you normally need to create a new token. Do not commit it to Git or put it directly inside a shared Packer template.

---

## 4. Insufficient API permissions

The token may authenticate successfully but still fail when Packer tries to:

* Create a VM
* Configure hardware
* access storage
* attach an ISO
* start or stop the VM
* convert it into a template

The speaker disabled privilege separation and used a root-owned token because it was easier.

That works in a home lab, but it gives the token very broad access. A dedicated Packer service account with limited permissions is safer.

---

## 5. Privilege separation confusion

With Proxmox API tokens, the token’s permissions may be separated from the owning user’s permissions.

The speaker disabled privilege separation so the token inherited root’s privileges.

The gotcha is that a token can appear to belong to a powerful account while still lacking the permissions Packer needs.

Do not blindly copy the root-token approach into production. Explicitly define the required role instead.

---

## 6. Self-signed TLS certificate errors

Home-lab Proxmox installations often use self-signed certificates.

Packer may reject the connection unless TLS verification is disabled:

```hcl
insecure_skip_tls_verify = true
```

This is convenient for a lab, but it removes server certificate verification.

For production, use a trusted certificate instead.

---

# Networking and Autoinstall gotchas

## 7. The build VM must reach the Packer machine

This is probably the most important point in the video.

During Ubuntu installation, Packer starts a temporary HTTP server on the computer running Packer. The Ubuntu VM connects to that server to download:

* `user-data`
* `meta-data`

Therefore, communication must work in this direction:

```text
Proxmox build VM → computer running Packer
```

It is not enough for:

* Proxmox to have internet access
* your computer to reach Proxmox
* the VM to reach the internet

The VM must specifically reach Packer’s HTTP server.

---

## 8. WSL2 may be unreachable from the Proxmox VM

This was one of the speaker’s actual mistakes.

He ran Packer inside WSL2, but WSL2 was behind its own virtualized network. The Proxmox VM could not reliably connect back to the HTTP server inside WSL.

His solution was to run Packer from PowerShell instead.

For your setup, the safer choices are:

* Run Packer natively on Windows.
* Run it from a Linux machine directly reachable by the Proxmox network.
* Run it from a dedicated build VM.
* Explicitly configure routing and firewall rules for WSL.

Do not assume that because WSL can reach Proxmox, Proxmox can reach WSL.

---

## 9. Packer may advertise the wrong IP address

The speaker had multiple network interfaces, and Packer selected the wrong one.

Common interfaces that can confuse automatic selection include:

* Ethernet
* Wi-Fi
* WSL
* Hyper-V
* Docker
* VPN adapters
* Tailscale
* VirtualBox
* VMware

Packer may advertise an IP that the Proxmox VM cannot reach.

The fix is to explicitly bind the Packer HTTP server to the correct address and ensure the Autoinstall URL contains that same reachable address.

---

## 10. DHCP must work during image building

The temporary VM needs an IP address before Ubuntu can fetch the Autoinstall configuration.

The easiest option is connecting the VM to a Proxmox bridge with working DHCP.

If DHCP fails:

* the VM has no usable address,
* it cannot reach Packer,
* Autoinstall fails,
* the normal interactive installer may appear.

Static addressing is possible, but it adds more moving parts to the build.

---

## 11. Firewalls may block Packer’s temporary HTTP port

Packer usually starts its HTTP server on a temporary or random port.

Possible blockers include:

* Windows Defender Firewall
* Linux firewall rules
* VLAN ACLs
* Proxmox firewall
* UniFi firewall rules
* VPN security software

You may need to:

* restrict Packer to a known port range,
* allow that range through the host firewall,
* ensure the build VLAN can reach the Packer host.

A random port can make firewall troubleshooting harder.

---

## 12. Do not confuse inbound and outbound connectivity

There are two separate connections:

```text
Ubuntu installer → Packer HTTP server
Packer → Ubuntu SSH server
```

The first is needed to install Ubuntu.

The second is needed for provisioning.

One can work while the other fails.

For example, Ubuntu may successfully install but Packer may never connect over SSH.

---

# Ubuntu Autoinstall gotchas

## 13. Falling back to the manual installer usually means Autoinstall failed

This was another major problem the speaker encountered.

Ubuntu booted, but instead of continuing automatically, it returned to the normal installation interface.

Likely causes:

* Packer HTTP server was unreachable
* wrong HTTP IP
* blocked port
* malformed `user-data`
* incorrect datasource URL
* boot command was wrong
* Ubuntu version did not match the expected boot sequence

The visible installer is often only the symptom.

---

## 14. Boot commands are version-specific

The boot key sequence used in the video was written for Ubuntu Server 20.04.

Boot menus and kernel command syntax can change between versions.

A boot sequence that works for Ubuntu 20.04 may fail on:

* Ubuntu 22.04
* Ubuntu 24.04
* Debian
* Rocky Linux
* another ISO build

Watch the Proxmox console to confirm that Packer is pressing the expected keys and entering the command correctly.

Do not treat boot commands as permanent.

---

## 15. Boot timing can be fragile

Packer types into the VM console according to expected delays.

Possible problems include:

* the ISO boots more slowly than expected,
* the boot menu appears later,
* Packer types before the console is ready,
* the machine is faster and the expected menu has already disappeared.

You may need to tune:

* boot wait time,
* pause intervals,
* key sequences,
* timeout values.

Always watch the console during early tests.

---

## 16. `user-data` YAML formatting is unforgiving

This was one of the speaker’s explicit failure points.

A small indentation error can invalidate the entire file.

Common YAML mistakes include:

* wrong indentation
* tabs instead of spaces
* missing colons
* incorrectly nested sections
* invalid quoting
* malformed password hashes
* duplicate keys

Ubuntu may not show a clear error. It may simply fall back to the interactive installer.

Validate the YAML before running a full Packer build.

---

## 17. Both NoCloud files should exist

The HTTP directory generally contains:

```text
http/
├── meta-data
└── user-data
```

The `meta-data` file may be empty, but it should still exist when the datasource expects it.

A wrong filename, path, or directory can cause the installer to receive nothing.

---

## 18. The NoCloud URL syntax must be exact

The kernel boot command must correctly point to the HTTP datasource.

Mistakes can include:

* wrong IP
* wrong port
* missing trailing slash
* incorrect datasource syntax
* shell or bootloader escaping problems
* Packer interpolation not resolving

Inspect the final command shown in the VM console, not just the template source.

---

# SSH and provisioning gotchas

## 19. SSH must be installed during Autoinstall

Packer normally provisions the completed machine over SSH.

If OpenSSH is not installed or enabled, Ubuntu may install successfully but Packer will wait until the SSH timeout expires.

Ensure the Autoinstall configuration installs and starts SSH.

---

## 20. Packer’s SSH credentials must match `user-data`

The user created during Autoinstall must match the communicator configuration in Packer.

Check:

* username
* password
* private key
* password authentication settings
* sudo access

A mismatch produces a build that installs successfully but fails at provisioning.

---

## 21. The provisioning user needs working `sudo`

Many installation and cleanup commands require root privileges.

Creating a user is not sufficient. It must be able to run the required commands through `sudo`.

Also consider whether `sudo` expects a password. A script may hang or fail if it cannot provide one.

---

## 22. Do not put too much work into Autoinstall

The speaker deliberately used Autoinstall mainly to:

* install Ubuntu,
* install SSH,
* create the build user,
* install basic required packages.

He moved software installation into Packer provisioners.

This makes failures easier to isolate.

A good separation is:

* **Autoinstall:** create a functioning OS that Packer can access.
* **Provisioners:** install Docker and customize the image.
* **Cloud-Init:** configure each deployed clone.

---

## 23. Start with the smallest possible image

The speaker strongly recommended not adding everything immediately.

First prove that you can:

1. Create the VM.
2. Start Autoinstall.
3. Install Ubuntu.
4. Connect over SSH.
5. Convert it to a template.

Then add:

* Cloud-Init preparation
* guest agent
* Docker
* application tools
* security hardening

Otherwise, one failed build may have dozens of possible causes.

---

## 24. Provisioning commands can become outdated

The speaker copied Docker installation commands from the installation guide.

Those commands may change over time.

Repositories, signing keys, package names, and installation methods are not permanent.

Pin or validate:

* Ubuntu version
* Docker repository
* package names
* package versions
* signing-key method

A script that worked when the video was recorded may not work unchanged today.

---

## 25. Package manager operations can be unreliable

Typical problems include:

* another process holding the APT lock,
* network mirrors being unavailable,
* interactive prompts,
* package restarts,
* package repository changes,
* temporary DNS failures.

Provisioning scripts should be non-interactive and fail clearly.

---

# Template preparation warnings

## 26. Clear the machine ID before templating

The speaker specifically cleaned the Linux machine ID before converting the VM into a template.

If you do not, cloned machines can inherit the same identity.

That can affect:

* DHCP behavior
* systemd identity
* logging
* software licensing
* monitoring
* configuration management

The template should be generalized before conversion.

---

## 27. Avoid baking personal credentials into the image

Do not leave your personal:

* SSH public keys
* private keys
* passwords
* API secrets
* cloud credentials
* environment files

inside a reusable template.

Use temporary build credentials where necessary and remove them before conversion. Inject deployment-specific access through Cloud-Init or another secure runtime mechanism.

---

## 28. SSH host keys may need regeneration

Although the speaker focused on machine ID cleanup, cloned templates should also be checked for duplicated SSH host keys.

Every deployed VM should have its own SSH host identity.

Whether Cloud-Init handles this depends on your image preparation and configuration.

---

## 29. Clean temporary build artifacts

Before converting the VM into a template, remove unnecessary data such as:

* APT caches
* package lists if appropriate
* temporary files
* shell history
* build logs containing secrets
* downloaded installers
* temporary SSH keys

Every leftover file will be copied into every clone.

---

## 30. Install and enable the QEMU Guest Agent correctly

Adding the guest-agent option in Proxmox is only half of the setup.

The package must also exist and run inside Ubuntu.

Otherwise, Proxmox may not receive:

* guest IP information,
* clean shutdown support,
* enhanced guest status.

---

## 31. Cloud-Init must be prepared inside the OS and in Proxmox

Cloud-Init requires both sides:

* the `cloud-init` package and correct datasource configuration inside Ubuntu,
* the Cloud-Init drive and related configuration in Proxmox.

Enabling only one side is not enough.

---

# Deployment gotchas

## 32. Regenerate the Cloud-Init image after editing settings

This was explicitly highlighted in the video.

After changing:

* username
* SSH key
* IP address
* gateway
* DNS

click **Regenerate Image** before booting.

Otherwise, the VM may use old Cloud-Init data.

---

## 33. Do not boot the template itself

A Proxmox template should remain the clean source image.

Deploy by cloning it.

Booting and modifying the source template can:

* consume Cloud-Init’s first boot,
* generate machine-specific state,
* create configuration drift,
* make the template unreproducible.

Make changes in Packer and rebuild the template instead.

---

## 34. Linked clones depend on the original template

Linked clones are extremely fast and storage-efficient, but they remain dependent on the source storage/template structure.

Use them carefully for long-lived or important workloads.

A full clone takes longer and uses more storage but is independent.

---

## 35. Static IP conflicts are easy to create

Cloud-Init will generally apply the IP address you specify, even if another device already uses it.

Keep a reliable source of truth for:

* addresses
* gateways
* VLANs
* DNS
* hostnames

This becomes especially important once deployment is automated.

---

## 36. Cloud-Init normally acts on first boot

If you boot a clone before entering the final settings, Cloud-Init may initialize the machine with incomplete or default values.

Configure it before the first boot.

Repeatedly changing Cloud-Init values after initialization may not produce the result you expect without cleaning Cloud-Init state.

---

# Workflow and maintenance warnings

## 37. Always run `packer validate`

Validate the template before starting the full build.

Also include the same variables file that the actual build uses. Otherwise, validation may fail because required variables are missing.

Validation catches syntax and configuration issues, but it cannot prove that:

* networking works,
* credentials are valid,
* the ISO boot sequence still matches,
* provisioning commands succeed.

---

## 38. Watch both Packer output and the Proxmox console

The Packer logs show orchestration and provisioning.

The Proxmox console shows:

* boot command timing,
* installer behavior,
* network failures,
* manual-installer fallback.

Using both is much more effective than relying on one.

---

## 39. Errors may be misleading

A failure may surface at a different layer than its actual cause.

Examples:

* “Packer crash” → incorrect Proxmox API credentials.
* Ubuntu installer appears → HTTP server or YAML failure.
* SSH timeout → user mismatch or SSH not installed.
* Cloud-Init did nothing → image not regenerated or template not prepared.

Always identify the pipeline stage before changing things.

---

## 40. Build images; do not manually patch them

Manual changes to a finished template are undocumented and cannot be reproduced.

The better process is:

1. Change the Packer source.
2. Rebuild.
3. Test the new template.
4. Replace or version the previous one.

The Packer files should be the source of truth, not the current state of the Proxmox template.

---

# The most important precautions for your setup

For your Windows, WSL, Proxmox, and shared AWS image work, I would prioritise these:

1. Run Packer from a network location directly reachable by the Proxmox build VM. Avoid relying on WSL2 NAT.
2. Explicitly bind the Packer HTTP server to the correct LAN IP.
3. Restrict its HTTP port range and allow it through Windows and network firewalls.
4. Validate `user-data` independently before every build.
5. Keep the initial Autoinstall minimal.
6. Use a dedicated Proxmox Packer account rather than a root token.
7. Use temporary SSH build credentials and remove them before templating.
8. Clear machine-specific identity, SSH host keys, temporary files, and Cloud-Init state.
9. Test a clone fully before treating the template as valid.
10. Version the image and rebuild it instead of editing it manually.
