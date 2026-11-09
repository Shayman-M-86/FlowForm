#!/usr/bin/env bash
set -Eeuo pipefail

# Match the two guest NICs by their Terraform addresses so Docker bridge
# traffic can continue while forwarding directly between the NICs is denied.
iface_for() {
  ip -o -4 addr show | awk -v target="$1" '
    { split($4, address, "/"); if (address[1] == target) { print $2; count++ } }
    END { if (count != 1) exit 1 }
  '
}
app_iface=$(iface_for "${APP_PRIVATE_IP:?}")
db_iface=$(iface_for "${HYBRID_APP_DB_IP:?}")
for iface in "$app_iface" "$db_iface"; do
  [[ $iface =~ ^[[:alnum:]_.-]{1,15}$ ]] || exit 1
done
[[ $app_iface != "$db_iface" ]]

policy=/etc/nftables/flowform-hybrid-app.nft
include=/etc/sysconfig/nftables.conf
install -d -m 0755 /etc/nftables
candidate=$(mktemp /etc/nftables/.flowform-hybrid-app.XXXXXXXX)
trap 'rm -f -- "$candidate"' EXIT
cat > "$candidate" <<POLICY
table inet flowform_hybrid_app
flush table inet flowform_hybrid_app
table inet flowform_hybrid_app {
    chain forward {
        type filter hook forward priority -10; policy accept;
        iifname "$app_iface" oifname "$db_iface" drop
        iifname "$db_iface" oifname "$app_iface" drop
    }
}
POLICY
nft --check --file "$candidate"
nft --file "$candidate"
chmod 0644 "$candidate"
mv -T -- "$candidate" "$policy"
line="include \"$policy\""
grep -Fxq "$line" "$include" 2>/dev/null || printf '\n%s\n' "$line" >> "$include"
