#!/usr/bin/env bash
set -Eeuo pipefail

infra_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
verifier="${infra_root}/machine-images/tooling/lib/actions/aws-ami-verify.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

cp "${infra_root}/machine-images/packer/variables/aws.auto.pkrvars.hcl.example" \
  "${tmp}/aws.pkrvars.hcl"
cat >"${tmp}/manifest.json" <<'JSON'
{
  "builds": [
    {
      "builder_type": "amazon-ebs",
      "artifact_id": "ap-southeast-2:ami-abc123",
      "custom_data": {
        "architecture": "x86_64",
        "image_role": "base",
        "region": "ap-southeast-2",
        "source_commit": "0123456789abcdef0123456789abcdef01234567"
      }
    }
  ]
}
JSON

mkdir -p "${tmp}/bin"
cat >"${tmp}/bin/aws" <<'FAKE_AWS'
#!/usr/bin/env bash
set -Eeuo pipefail
case "${2:-}" in
  describe-images)
    cat <<JSON
{
  "Images": [{
    "Architecture": "x86_64",
    "RootDeviceType": "ebs",
    "State": "available",
    "RootDeviceName": "/dev/xvda",
    "VirtualizationType": "hvm",
    "Tags": [
      {"Key": "project", "Value": "flowform"},
      {"Key": "managed_by", "Value": "packer"},
      {"Key": "image_role", "Value": "base"},
      {"Key": "source_commit", "Value": "0123456789abcdef0123456789abcdef01234567"}
    ],
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "DeleteOnTermination": true,
        "Encrypted": true,
        "SnapshotId": "snap-def456",
        "VolumeSize": ${FAKE_AWS_VOLUME_SIZE:-10},
        "VolumeType": "gp3"
      }
    }]
  }]
}
JSON
    ;;
  describe-snapshots)
    cat <<JSON
{"Snapshots": [{"Encrypted": true, "SnapshotId": "snap-def456", "VolumeSize": ${FAKE_AWS_VOLUME_SIZE:-10}}]}
JSON
    ;;
  *)
    echo "unexpected fake AWS command: $*" >&2
    exit 1
    ;;
esac
FAKE_AWS
chmod +x "${tmp}/bin/aws"

PATH="${tmp}/bin:${PATH}" "${verifier}" \
  --role base \
  --vars-file "${tmp}/aws.pkrvars.hcl" \
  --manifest "${tmp}/manifest.json" >"${tmp}/success.out"
grep -Fq $'role=base\tami=ami-abc123' "${tmp}/success.out"
grep -Fq $'size=10GiB\ttype=gp3\tencrypted=true' "${tmp}/success.out"
jq -e '
  .flowform_verification.image_role == "base"
  and .flowform_verification.ami_id == "ami-abc123"
  and .flowform_verification.root_snapshot_id == "snap-def456"
' "${tmp}/manifest.json" >/dev/null

if FAKE_AWS_VOLUME_SIZE=12 PATH="${tmp}/bin:${PATH}" "${verifier}" \
  --role base \
  --vars-file "${tmp}/aws.pkrvars.hcl" \
  --manifest "${tmp}/manifest.json" >"${tmp}/oversized.out" 2>&1; then
  echo "oversized AWS AMI unexpectedly passed validation" >&2
  exit 1
fi
grep -Fq 'AMI root is 12 GiB; expected exactly 10 GiB' "${tmp}/oversized.out"

echo "verify-aws-ami tests OK"
