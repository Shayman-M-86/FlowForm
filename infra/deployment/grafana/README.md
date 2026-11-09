# Grafana dashboards

Dashboards for the FlowForm Grafana Cloud stack, kept as `gcx` resource
manifests in `dashboards/`, together with the `FlowForm` folder.

| Dashboard | Source | Shows |
| --- | --- | --- |
| FlowForm – API edge routing (`flowform-edge-routing`) | `build_edge_routing.py` | Cloudflare edge per request, client region and IP version, edge-to-origin time per edge, tunnel connectors, and browser timing |

Edit the generator rather than the JSON, then publish:

```bash
python3 infra/deployment/grafana/build_edge_routing.py
gcx resources validate -p infra/deployment/grafana/dashboards
gcx resources push -p infra/deployment/grafana/dashboards
```

Tempo returns every instant metrics frame with the function name as its
`refId`, so per-query overrides do not match. Each panel uses one grouped query
and renames series by label pattern instead.
