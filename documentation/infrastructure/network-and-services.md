# Network and services

**Status: Target topology under evaluation.**

The platform network distinguishes public ingress, proxy/edge services, application services and private data services. In a hybrid deployment, externally reachable entry points must not imply direct public access to the application database.

The proposed Proxmox design separates proxy and application networks, with management access controlled independently of workload ingress. Tunnel routing, service authentication, outbound access and the interface between local networks and cloud services require explicit configuration references.

Network diagrams and service addresses should be derived from the current IaC and host configuration rather than copied from an earlier plan.
