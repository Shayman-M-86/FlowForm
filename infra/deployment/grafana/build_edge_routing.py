"""Generate dashboards/edge-routing.json (Grafana dashboard manifest).

Run: python3 infra/deployment/grafana/build_edge_routing.py
Push: gcx resources push -p infra/deployment/grafana/dashboards
"""

import json
from pathlib import Path

TEMPO = {"type": "tempo", "uid": "grafanacloud-traces"}
LOKI = {"type": "loki", "uid": "grafanacloud-logs"}
AU_EDGES = "MEL|SYD|ADL|PER|BNE|CBR|HBA|DRW"
EDGE = '{ resource.service.name = "edge_processing" && name = "cloudflare_request" }'
ORIGIN = '{ resource.service.name = "origin_fetch" && name = "dynamic" }'
BACKEND = '{ resource.service.name = "backend" && span.cloudflare.colo != nil }'
BROWSER = '{ resource.service.name = "flowform-studio-browser" && name =~ "HTTP .*" }'
CADDY_V6 = '{ resource.service.name = "caddy" && span.client.address =~ ".*:.*" }'
CADDY_V4 = '{ resource.service.name = "caddy" && span.client.address =~ "[0-9]+\\\\.[0-9]+\\\\.[0-9]+\\\\.[0-9]+" && span.client.address !~ "(10|127|172\\\\.(1[6-9]|2[0-9]|3[01])|192\\\\.168)\\\\..*" }'
# Tempo names series like {span.cloudflare.colo="MEL"} or {p=0.5, span.x="3"},
# and sets every frame's refId to the function name, so per-query overrides
# cannot match. Each panel therefore uses one grouped query plus renames.


def rename(regex, pattern):
    return {
        "id": "renameByRegex",
        "options": {"regex": regex, "renamePattern": pattern},
    }


ONE_LABEL = rename('^\\{[^"]*"([^"]*)"\\}$', "$1")
QUANTILE_LABEL = rename('^\\{p=([0-9.]+), [^"]*"([^"]*)"\\}$', "$2")


def tq(ref, query, instant=False, step=None):
    target = {
        "refId": ref,
        "datasource": TEMPO,
        "queryType": "traceql",
        "query": query,
        "metricsQueryType": "instant" if instant else "range",
        "limit": 20,
    }
    if step:
        target["step"] = step
    return target


panels = []


def row(title, y):
    panels.append(
        {
            "type": "row",
            "title": title,
            "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
            "panels": [],
        }
    )


def panel(
    kind,
    title,
    desc,
    pos,
    targets,
    unit=None,
    options=None,
    field=None,
    transforms=None,
    overrides=None,
):
    defaults = {"unit": unit} if unit else {}
    defaults.update(field or {})
    panels.append(
        {
            "type": kind,
            "title": title,
            "description": desc,
            "gridPos": dict(zip("hwxy", pos, strict=True)),
            "datasource": targets[0]["datasource"],
            "targets": targets,
            "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
            "options": options or {},
            "transformations": transforms or [],
        }
    )


row("Where requests entered Cloudflare", 0)
panel(
    "piechart",
    "Edge data centre",
    "Share of API requests by the Cloudflare data centre that received them. MEL/SYD/ADL are local; SIN, NRT or HKG mean the visitor's ISP routed them offshore (seen for Telstra over IPv4).",
    (8, 6, 0, 1),
    [tq("A", f"{EDGE} | count_over_time() by (span.cloudflare.colo)", instant=True)],
    options={
        "pieType": "donut",
        "displayLabels": ["name", "percent"],
        "legend": {
            "displayMode": "table",
            "placement": "right",
            "values": ["value", "percent"],
        },
        "reduceOptions": {"calcs": ["lastNotNull"]},
    },
    transforms=[ONE_LABEL],
)
panel(
    "stat",
    "Offshore edge requests",
    "API requests received by a Cloudflare data centre outside Australia in the selected range. 0 is healthy; compare with the edge data centre chart for the share.",
    (8, 4, 6, 1),
    [
        tq(
            "A",
            f'{{ resource.service.name = "edge_processing" && name = "cloudflare_request" && span.cloudflare.colo !~ "{AU_EDGES}" }} | count_over_time()',
            instant=True,
        )
    ],
    unit="short",
    options={
        "reduceOptions": {"calcs": ["lastNotNull"]},
        "textMode": "value",
        "colorMode": "value",
        "graphMode": "none",
    },
    field={
        "noValue": "0",
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": [
                {"color": "green", "value": None},
                {"color": "orange", "value": 1},
            ],
        },
    },
)
panel(
    "timeseries",
    "Requests by edge data centre",
    "Request rate per Cloudflare data centre over time.",
    (8, 14, 10, 1),
    [tq("A", f"{EDGE} | rate() by (span.cloudflare.colo)")],
    unit="reqps",
    field={
        "custom": {
            "drawStyle": "bars",
            "fillOpacity": 70,
            "stacking": {"mode": "normal"},
            "lineWidth": 0,
        }
    },
    options={
        "legend": {"displayMode": "list", "placement": "bottom"},
        "tooltip": {"mode": "multi", "sort": "desc"},
    },
    transforms=[ONE_LABEL],
)

row("Where requests came from", 9)
panel(
    "piechart",
    "Client IP version",
    "Client IP version of API requests (from CF-Connecting-IP; the address itself is not recorded). Over IPv6, Telstra hands traffic to Cloudflare in Melbourne; over IPv4 it currently goes via Singapore/Asia. Recorded from backend release f02bec80+ onward.",
    (8, 6, 0, 10),
    [
        tq(
            "A",
            f"{BACKEND} | count_over_time() by (span.flowform.client.ip_version)",
            instant=True,
        )
    ],
    options={
        "pieType": "donut",
        "displayLabels": ["name", "percent"],
        "legend": {
            "displayMode": "table",
            "placement": "right",
            "values": ["value", "percent"],
        },
        "reduceOptions": {"calcs": ["lastNotNull"]},
    },
    transforms=[rename('^\\{[^"]*"([^"]*)"\\}$', "IPv$1")],
    overrides=[
        {
            "matcher": {"id": "byName", "options": "IPv6"},
            "properties": [
                {"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}}
            ],
        },
        {
            "matcher": {"id": "byName", "options": "IPv4"},
            "properties": [
                {"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}
            ],
        },
    ],
)
panel(
    "bargauge",
    "Client region → edge (IP version)",
    "Backend requests by client region (Cloudflare geolocation), IP version and receiving edge, e.g. 'AU-VIC 4 SIN'. Recorded from backend release f02bec80+ onward; empty before.",
    (8, 18, 6, 10),
    [
        tq(
            "A",
            f"{BACKEND} | count_over_time() by (span.geo.region.iso_code, span.flowform.client.ip_version, span.cloudflare.colo)",
            instant=True,
        )
    ],
    unit="short",
    options={
        "displayMode": "basic",
        "orientation": "horizontal",
        "showUnfilled": True,
        "valueMode": "text",
        "reduceOptions": {"calcs": ["lastNotNull"]},
    },
    field={"color": {"mode": "fixed", "fixedColor": "blue"}},
    transforms=[
        rename('^\\{[^"]*"([^"]*)"[^"]*"([^"]*)"[^"]*"([^"]*)"\\}$', "$3 · IPv$2 → $1")
    ],
)

row("How they got back: edge → tunnel → origin", 18)
panel(
    "bargauge",
    "Edge → origin round trip (p50)",
    "Median time from the receiving edge to the Proxmox origin and back, through the Cloudflare network and tunnel. Caddy is origin-only time; the difference is network transit. Offshore edges cross back to the Australian tunnel connectors.",
    (8, 12, 0, 19),
    [
        tq(
            "A",
            f"{ORIGIN} | quantile_over_time(duration, .5) by (span.cloudflare.colo)",
            instant=True,
        ),
        tq(
            "B",
            '{ resource.service.name = "caddy" } | quantile_over_time(duration, .5)',
            instant=True,
        ),
    ],
    unit="s",
    options={
        "displayMode": "gradient",
        "orientation": "horizontal",
        "valueMode": "color",
        "showUnfilled": True,
        "reduceOptions": {"calcs": ["lastNotNull"]},
    },
    field={
        "min": 0,
        "decimals": 3,
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": [
                {"color": "green", "value": None},
                {"color": "orange", "value": 0.05},
                {"color": "red", "value": 0.2},
            ],
        },
    },
    transforms=[QUANTILE_LABEL, rename("^0\\.5$", "Caddy + backend (origin only)")],
)
panels.append(
    {
        "type": "table",
        "title": "Tunnel connectors",
        "description": "Cloudflare data centres the cloudflared connector registered with (latest first). Requests reach the origin through one of these, so an offshore edge must cross back to them.",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 19},
        "datasource": LOKI,
        "targets": [
            {
                "refId": "A",
                "datasource": LOKI,
                "queryType": "range",
                "editorMode": "code",
                "expr": '{container="flowform-proxy-cloudflared-1"} |= "Registered tunnel connection" | regexp "connIndex=(?P<conn>[0-9]+) .*location=(?P<location>[a-z0-9]+) protocol=(?P<protocol>[a-z0-9]+)" | line_format "{{.location}}"',
            }
        ],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {
            "showHeader": True,
            "sortBy": [{"displayName": "Time", "desc": True}],
        },
        "transformations": [
            {"id": "extractFields", "options": {"source": "labels"}},
            {
                "id": "organize",
                "options": {
                    "includeByName": {
                        "Time": True,
                        "conn": True,
                        "location": True,
                        "protocol": True,
                    },
                    "indexByName": {"Time": 0, "location": 1, "conn": 2, "protocol": 3},
                    "renameByName": {"conn": "connection", "location": "location"},
                },
            },
        ],
    }
)

row("Browser view (Studio)", 27)
panel(
    "timeseries",
    "Browser API call duration by HTTP version",
    "Studio API calls as measured in the browser, p50 and p90, split by negotiated HTTP version (3 = QUIC, 2 = TCP). TCP calls are the ones likely to land offshore.",
    (8, 16, 0, 28),
    [
        tq(
            "A",
            f"{BROWSER} | quantile_over_time(duration, .5, .9) by (span.network.protocol.version)",
        )
    ],
    unit="s",
    options={
        "legend": {"displayMode": "list", "placement": "bottom"},
        "tooltip": {"mode": "multi", "sort": "desc"},
    },
    transforms=[
        rename('^\\{p=0\\.([0-9]), [^"]*"([^"]*)"\\}$', "HTTP/$2 p$10"),
        rename("^0\\.([0-9])$", "unrecorded version p$10"),
    ],
)
STAT_MS = {
    "unit": "ms",
    "options": {
        "reduceOptions": {"calcs": ["lastNotNull"]},
        "textMode": "value",
        "colorMode": "value",
        "graphMode": "none",
    },
    "field": {
        "decimals": 1,
        "noValue": "–",
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": [
                {"color": "green", "value": None},
                {"color": "orange", "value": 20},
                {"color": "red", "value": 80},
            ],
        },
    },
}
panel(
    "stat",
    "Preflight / queue (avg)",
    "Average browser time between the connection being ready and the request being sent: the CORS preflight round trip plus queueing. Should fall towards 0 now preflights are cached for 2 h.",
    (8, 4, 16, 28),
    [
        tq(
            "A",
            '{ resource.service.name = "flowform-studio-browser" && span.flowform.timing.preflight_or_queue_ms >= 0 } | avg_over_time(span.flowform.timing.preflight_or_queue_ms)',
            instant=True,
        )
    ],
    **STAT_MS,
)
panel(
    "stat",
    "New connection setup (avg)",
    "Average DNS + TCP/TLS (or QUIC) setup for calls that opened a new connection. Offshore (IPv4/TCP) connections cost several round trips here.",
    (8, 4, 20, 28),
    [
        tq(
            "A",
            '{ resource.service.name = "flowform-studio-browser" && span.flowform.timing.connect_ms > 0 } | avg_over_time(span.flowform.timing.connect_ms)',
            instant=True,
        )
    ],
    **STAT_MS,
)

for i, p in enumerate(panels, start=1):
    p["id"] = i

manifest = {
    "apiVersion": "dashboard.grafana.app/v1beta1",
    "kind": "Dashboard",
    "metadata": {
        "name": "flowform-edge-routing",
        "annotations": {"grafana.app/folder": "flowform"},
    },
    "spec": {
        "title": "FlowForm – API edge routing",
        "description": "Where staging API requests entered Cloudflare, where they came from, and how they got back through the tunnel. Source: infra/deployment/grafana/build_edge_routing.py",
        "tags": ["flowform", "cloudflare", "staging"],
        "timezone": "browser",
        "schemaVersion": 39,
        "refresh": "",
        "time": {"from": "now-24h", "to": "now"},
        "templating": {"list": []},
        "panels": panels,
    },
}
out = Path(__file__).parent / "dashboards" / "edge-routing.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
