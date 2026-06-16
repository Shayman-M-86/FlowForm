Verify the last pass — check claims against code only, no tests, no docs.

```bash
bash backend/scripts/impl-verify.sh
```

Run this with the Bash tool directly. Then read only the changed files listed in the output and check each behavior claim against the code. Report [ok] or [wrong/missing] per claim. Do not run tests, read docs, or implement anything.
