# Frontend deploy

Publishing `public-site` and `studio-app` to S3 + CloudFront. Normally this
happens automatically in CI; the manual path is for one-off pushes and
debugging.

## Automatic (CI)

`.github/workflows/deploy.yml` runs on push to the `staging` branch (paths
under `frontend/**`). It assumes the `flowform-staging-frontend-deploy`
role via GitHub OIDC — no AWS keys in GitHub — reads build config from SSM,
builds both apps, `s3 sync`s, and invalidates CloudFront. To trigger it
without a code change, use the workflow's manual dispatch from the GitHub
Actions UI.

## Manual (from your machine)

Needs active AWS credentials for the account. Bucket names are deterministic
(`flowform-<env>-<app>`); distribution IDs are not, so read them from SSM.

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm run build:site
pnpm run build:studio
```

```bash
# Distribution IDs (published by the Frontend stack):
env=staging
PUBLIC_DIST=$(aws ssm get-parameter --name "/flowform/$env/frontend/public-site-distribution-id" --query Parameter.Value --output text)
STUDIO_DIST=$(aws ssm get-parameter --name "/flowform/$env/frontend/studio-app-distribution-id" --query Parameter.Value --output text)
```

```bash
# Sync assets first, then index.html (HTML references content-hashed asset
# filenames — uploading it before its assets would briefly serve 404s),
# then invalidate.
for app in public-site studio-app; do
  bucket="s3://flowform-$env-$app"
  aws s3 sync "apps/$app/dist/" "$bucket/" --delete --exclude index.html
  aws s3 cp   "apps/$app/dist/index.html" "$bucket/index.html"
done
aws cloudfront create-invalidation --distribution-id "$PUBLIC_DIST" --paths "/*"
aws cloudfront create-invalidation --distribution-id "$STUDIO_DIST" --paths "/*"
```

## Verify

```bash
curl -sS -o /dev/null -w "%{url_effective}  HTTP %{http_code}\n" \
  https://staging.flow-form.com.au \
  https://studio.staging.flow-form.com.au
```

Both should return `HTTP 200`. A CloudFront invalidation takes a minute or
two to propagate, so a stale response right after publishing is expected.

## Notes

- `VITE_API_BASE_URL` currently points at `api.<domain>`, which won't
  resolve until `application_stack.py`'s ALB exists — the studio app builds
  and serves, but API calls fail until then.
- The buckets are private (CloudFront-only via OAC). Hitting the S3 URL
  directly returns 403 — that's correct, not a deploy failure.
