#!/usr/bin/env bash
set -Eeuo pipefail

infra_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
image="${infra_root}/machine-images/tooling/image"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
mkdir -p "${tmp}/bin"
export FAKE_AWS_MUTATIONS="${tmp}/mutations"
: >"${FAKE_AWS_MUTATIONS}"

cat >"${tmp}/bin/aws" <<'FAKE_AWS'
#!/usr/bin/env bash
set -Eeuo pipefail

service="${1:-}"
operation="${2:-}"
case "${service}:${operation}" in
  sts:get-caller-identity)
    if [[ "$*" == *"--query Account"* ]]; then
      printf '908123139858\n'
    else
      printf '{"Account":"908123139858"}\n'
    fi
    ;;
  ssm:get-parameter)
    parameter=""
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == "--name" ]]; then parameter="$2"; break; fi
      shift
    done
    case "${parameter}" in
      /flowform/staging/ec2/appAmiId) printf 'ami-aa03\n' ;;
      /flowform/staging/ec2/proxyAmiId) printf 'ami-cc01\n' ;;
      *) exit 254 ;;
    esac
    ;;
  ec2:describe-instances)
    printf 'ami-cc03\n'
    ;;
  ec2:describe-images)
    cat <<'JSON'
{
  "Images": [
    {"ImageId":"ami-aa01","CreationDate":"2026-07-29T04:00:00Z","Tags":[{"Key":"image_role","Value":"app"},{"Key":"parent_ami_id","Value":"ami-ba01"}]},
    {"ImageId":"ami-aa02","CreationDate":"2026-07-29T03:00:00Z","Tags":[{"Key":"image_role","Value":"app"},{"Key":"parent_ami_id","Value":"ami-ba01"}]},
    {"ImageId":"ami-aa03","CreationDate":"2026-07-29T02:00:00Z","Tags":[{"Key":"image_role","Value":"app"},{"Key":"parent_ami_id","Value":"ami-ba02"}]},
    {"ImageId":"ami-aa04","CreationDate":"2026-07-29T01:00:00Z","Tags":[{"Key":"image_role","Value":"app"},{"Key":"parent_ami_id","Value":"ami-ba04"}]},
    {"ImageId":"ami-cc01","CreationDate":"2026-07-29T04:00:00Z","Tags":[{"Key":"image_role","Value":"proxy"},{"Key":"parent_ami_id","Value":"ami-ba01"}]},
    {"ImageId":"ami-cc02","CreationDate":"2026-07-29T03:00:00Z","Tags":[{"Key":"image_role","Value":"proxy"},{"Key":"parent_ami_id","Value":"ami-ba01"}]},
    {"ImageId":"ami-cc03","CreationDate":"2026-07-29T01:00:00Z","Tags":[{"Key":"image_role","Value":"proxy"},{"Key":"parent_ami_id","Value":"ami-ba03"}]},
    {"ImageId":"ami-ba01","CreationDate":"2026-07-29T00:00:00Z","Tags":[{"Key":"image_role","Value":"base"}]},
    {"ImageId":"ami-ba02","CreationDate":"2026-07-28T00:00:00Z","Tags":[{"Key":"image_role","Value":"base"}]},
    {"ImageId":"ami-ba03","CreationDate":"2026-07-27T00:00:00Z","Tags":[{"Key":"image_role","Value":"base"}]},
    {"ImageId":"ami-ba04","CreationDate":"2026-07-26T00:00:00Z","Tags":[{"Key":"image_role","Value":"base"}]},
    {"ImageId":"ami-bf00","CreationDate":"2026-07-25T00:00:00Z","Tags":[{"Key":"image_role","Value":"base"}]}
  ]
}
JSON
    ;;
  ec2:deregister-image)
    image_id=""
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == "--image-id" ]]; then image_id="$2"; break; fi
      shift
    done
    printf '%s\n' "${image_id}" >>"${FAKE_AWS_MUTATIONS}"
    printf '{"Return":true}\n'
    ;;
  *)
    printf 'unexpected fake AWS command: %s\n' "$*" >&2
    exit 1
    ;;
esac
FAKE_AWS
chmod +x "${tmp}/bin/aws"

PATH="${tmp}/bin:${PATH}" AWS_PROFILE=default \
  "${image}" prune aws --environment staging --dry-run \
  >"${tmp}/dry.out" 2>"${tmp}/dry.err"
[[ ! -s "${FAKE_AWS_MUTATIONS}" ]]
grep -Fq 'would deregister ami-aa04' "${tmp}/dry.err"
grep -Fq 'would deregister ami-ba04' "${tmp}/dry.err"
grep -Fq 'would deregister ami-bf00' "${tmp}/dry.err"
! grep -Fq 'would deregister ami-aa03' "${tmp}/dry.err"
! grep -Fq 'would deregister ami-ba01' "${tmp}/dry.err"
! grep -Fq 'would deregister ami-ba02' "${tmp}/dry.err"
! grep -Fq 'would deregister ami-ba03' "${tmp}/dry.err"

PATH="${tmp}/bin:${PATH}" AWS_PROFILE=default \
  "${image}" prune aws --environment staging --apply \
  >"${tmp}/apply.out" 2>"${tmp}/apply.err"
sort "${FAKE_AWS_MUTATIONS}" >"${tmp}/actual"
printf '%s\n' ami-aa04 ami-ba04 ami-bf00 | sort >"${tmp}/expected"
cmp "${tmp}/expected" "${tmp}/actual"

echo "prune-aws-images tests OK"
