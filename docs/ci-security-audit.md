# GitHub Actions security audit

**Pass-with-warnings** — workflow review completed on 2026-10-09 using the
`gha-security-audit` skill. No reachable injection or path from pull-request code
to repository write tokens, deployment secrets, or OIDC credentials was found. Repository settings and the
full hosted Molecule run are outside this local audit's verification.

## Scope and action provenance

Reviewed `.github/workflows/ci.yml`, the invoked test scripts, and the Molecule
configuration. The skill's pattern scanner was followed by manual review;
absence of scanner matches is not proof of security.

Both existing action pins already resolve to the latest stable upstream releases
as of the review date. GitHub's release API and `git ls-remote --tags` agreed:

| Action | Release | Commit SHA |
| --- | --- | --- |
| [actions/checkout](https://github.com/actions/checkout/releases/tag/v7.0.1) | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| [actions/setup-python](https://github.com/actions/setup-python/releases/tag/v7.0.0) | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` |

All four `uses:` entries have full immutable commit pins. Their version comments
now identify the exact releases. These Git object IDs are 40-character commit
SHAs; SHA-256 digests are a separate format used for artifacts and container images.

## Findings

### [LOW, fixed] Checkout credentials retained during tests

Location: `.github/workflows/ci.yml:21` and `.github/workflows/ci.yml:70`.

Issue: Both checkout steps previously used the default credential persistence.
Impact: Code executed during CI could access an unnecessary read-only repository
credential. The workflows had no write permission, so this was a hardening issue.
Fix: Both steps now set `persist-credentials: false`.
Reference: audit taxonomy sections 1.1 and 2; least-privilege checklist.

```yaml
with:
  persist-credentials: false
```

### [LOW, fixed] Missing explicit execution limits and action update automation

Location: `.github/workflows/ci.yml:12` and `.github/dependabot.yml:1`.

Issue: Jobs relied on GitHub's default timeout and action pins had no updater.
Impact: Stalled tests could consume runner time, and immutable pins could grow stale.
Fix: Set job timeouts, cancel superseded runs on the same ref, and configure
weekly Dependabot PRs for GitHub Actions. Dependabot does not automatically merge.
Reference: supply-chain checklist and audit taxonomy section 2.

### [INFO, verified] Untrusted tests have no deployment privileges

Location: `.github/workflows/ci.yml:4`.

Issue: Pull-request code is executed by design.
Impact: Contributors can influence test commands on the disposable runner.
Controls: The triggers are `push` to `main` and `pull_request`; there is no
`pull_request_target`, `workflow_run`, self-hosted runner, raw event-text
interpolation in shell commands, shared artifact/cache consumption, secret
reference, or OIDC request. Workflow permissions are `contents: read`.
Concurrency expressions are evaluated as metadata, not passed to a shell.
The image-download step uses the existing public registry references through
`community.docker.docker_image_pull`, with bounded retries and a 30-minute step
timeout. It adds no registry secrets, shell interpolation, or daemon configuration
changes. Molecule builds reuse those downloaded images with `pull: false`.
Reference: audit taxonomy sections 1.1–1.5, 2, and 3.

### [INFO, remaining] Test dependencies and containers resolve live upstream content

Location: `.github/workflows/ci.yml:30` and `molecule/default/molecule.yml:10`.

Issue: Python/Galaxy tools, distro image tags, and some software installed by the
role are intentionally resolved from upstream during tests. Molecule containers
currently run privileged on an ephemeral GitHub-hosted runner.
Impact: Commit pins protect the Actions implementations, not every dependency
executed by the test suite. CI results can change as upstream software changes;
container privilege is not an isolation boundary against submitted test code.
Controls: Keep these jobs free of deployment secrets and write tokens. Do not move
them onto a persistent or sensitive self-hosted runner unchanged. A separate
locked-dependency test lane and reducing container capabilities are future work.
Reference: audit taxonomy sections 1.5 and 2.

### [INFO, unverified] GitHub repository-level protections

Issue: Branch/tag rulesets, fork-run approval settings, and allowed-action policies
are not stored in these files and were not inspected through an authenticated API.
Impact: This audit cannot establish who can replace a workflow or approve fork runs.
Recommendation: Require reviewed PRs and passing CI on the default branch, review
workflow changes, and keep GitHub's fork-contributor approval controls enabled.
Reference: audit taxonomy sections 1.4, 1.5, and 3.

## Validation and publishing boundary

The updated workflow passes `actionlint` and the skill's scan. Role lint and the
targeted regression checks run locally; the complete hosted distro matrix must
still pass in GitHub Actions.

There is currently no publishing workflow and no Galaxy credential in CI. A
future role release workflow should validate a semantic-version tag, test its
exact commit before import, and expose a Galaxy token only to the publication
job. Standalone roles use `ansible-galaxy role import`; collections use a separate
build/publish process. See the
[Galaxy role import documentation](https://docs.ansible.com/projects/galaxy-ng/en/latest/community/userguide.html#importing-roles).
