# syntax=docker/dockerfile:1

FROM grafana/alloy:v1.18.0@sha256:491b0578c04983fd54fe99b587b6fab4404dc46d0dc16677bd6b00cc1140b308

COPY config/app.alloy /etc/flowform/alloy/app.alloy
COPY config/proxy.alloy /etc/flowform/alloy/proxy.alloy
COPY --chmod=0755 entrypoint.sh /usr/local/bin/flowform-alloy-entrypoint

ENTRYPOINT ["/usr/local/bin/flowform-alloy-entrypoint"]
