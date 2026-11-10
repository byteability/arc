## 1. Configuration

- [x] 1.1 Add `release-please-config.json` (root package, `release-type: python`, `package-name: arc`, `include-component-in-tag: false`, `bump-minor-pre-major: true`)
- [x] 1.2 Add `.release-please-manifest.json` with `{".": "0.0.0"}`

## 2. Workflow

- [x] 2.1 Rewrite `.github/workflows/release.yml`: trigger on push to `main`; `release-please` job (SHA-pinned v5.0.0, `contents`/`pull-requests: write`) exposing `release_created` and `tag_name`
- [x] 2.2 `build` job gated on `release_created == 'true'`: checkout, setup-uv, tests, `uv build`, `SHA256SUMS`, `gh release upload`

## 3. Docs and settings

- [x] 3.1 Enable "Allow GitHub Actions to create and approve pull requests" for the org and repo
- [x] 3.2 Document the release flow in README and CLAUDE.md

## 4. Verify

- [x] 4.1 JSON files parse; workflow YAML parses; pinned action SHA exists
- [ ] 4.2 After merge: release-please opens a 0.1.0 release PR; merging it creates `v0.1.0` with sdist, wheel and `SHA256SUMS`
