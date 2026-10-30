---
name: ls-release
description: Cut a LlamaStash release (vX.Y.Z) end to end - promote the CHANGELOG, bump Cargo.toml and the TUI goldens, commit and push, tag, watch the publish pipeline, write the GitHub release body, verify every channel. Use when asked to release, ship, or publish a new version of llamastash.
---

# LlamaStash release

Cuts `vX.Y.Z` from `main`. Follow the steps in order; each one ends with the check that says it is safe to continue. Never tag through a red `ci` run.

Commands run from the repo root. `scripts/` and `references/` paths below are inside this skill's own directory (`.claude/skills/ls-release/` here, `.agents/skills/ls-release/` through the symlink Pi reads).

## Rules that hold all the way through

- **One release commit.** Version bump + CHANGELOG promotion + golden re-stamp, nothing else. Feature work must already be on `main`.
- **Never block the turn.** The push, `ci` and the release pipeline take tens of minutes together. Arm each wait in the background (the harness's background or monitor facility, or a `wait-for.sh`-style poller if the operator has one), say what is being watched and its deadline, then end the turn. No `sleep` loops, no polling once per check.
- **Outward actions need an explicit ask.** Pushing `main`, pushing the tag and everything the tag publishes are outward-facing. Do them only when asked in this session.
- **A rerun beats a code change for infra flakes.** See `references/flakes.md` before editing anything because CI went red once.
- **Verify the channels, not the pipeline.** A green run is not proof the artifacts are good: `references/verify-channels.md`.

## 1. Preflight

```bash
git status --short              # must be clean; stash or commit first
git pull --ff-only origin main
git log --first-parent v<LAST>..HEAD --oneline   # what is shipping
gh run list -c "$(git rev-parse HEAD)" --json workflowName,status,conclusion --jq '.[]'
```

Stop unless the tree is clean and `ci` on `main`'s tip is `completed success`. `cargo audit` is a `ci` job, so a fresh RustSec advisory blocks the release: fix the dependency on `main` first, and say which advisory in the CHANGELOG `### Security` section.

Pick the number: `patch` = fixes plus small additions, `minor` = a new user-facing surface, `major` reserved. If the diff makes the choice unclear, ask before writing anything.

## 2. Write the release section

Read `references/changelog.md` first. Write the intro and the Contributors block to two temp files, then promote `[Unreleased]` with the helper. Dry run first and read it, then `--write`:

```bash
s=.claude/skills/ls-release/scripts/promote_changelog.py
python3 $s --version X.Y.Z --date "$(date +%F)" --intro /tmp/intro.md --contributors /tmp/contributors.md
python3 $s --version X.Y.Z --date "$(date +%F)" --intro /tmp/intro.md --contributors /tmp/contributors.md --write
```

The helper refuses to run twice for the same version and leaves the bullets exactly as they were. `python3 $s --self-test` checks the helper itself.

Check the result: empty `## [Unreleased]` on top, `## [X.Y.Z] — YYYY-MM-DD`, headline bullets first under `Added`, a `### Contributors` block, and no PR link on a commit that went straight to `main`. If any doc now says something wrong about what shipped, fix that doc in the same commit.

## 3. Bump the version everywhere it appears

```bash
sed -i '0,/^version = /s/^version = .*/version = "X.Y.Z"/' Cargo.toml   # first match is the package version
cargo metadata --format-version 1 > /dev/null          # refreshes Cargo.lock
sed -i 's/LlamaStash v<LAST>/LlamaStash vX.Y.Z/' tests/golden/*.txt
cargo nextest run --features test-fixtures --test tui_e2e_render_test
```

Two checks that the bump reached everything: the goldens agree on one version, and nothing outside the history files still names the old one (the CHANGELOG keeps every past version, `Cargo.lock` has unrelated crates that happen to sit at it, and `TODO.md` headings record which release a checklist belonged to):

```bash
grep -h -o 'LlamaStash v[0-9.]*' tests/golden/*.txt | sort -u
rg -n -F "<LAST>" -g '!CHANGELOG.md' -g '!Cargo.lock' -g '!TODO.md'
```

`README.md` and `docs/` carry no version string at all, so neither check expects a hit there.

## 4. Commit and push

```bash
git add -A
git commit -m 'chore(release): X.Y.Z' -m '<two lines naming the headline>'
git push origin main            # pre-push runs fmt, clippy, doc, full nextest
```

Run the push in the background and confirm it landed with `git ls-remote origin refs/heads/main`. A quiet auto-close in a dispatched session does not mean the push died, and it does not mean it survived: check the ref.

## 5. Tag

Wait for the `ci` run on the release SHA to go green (full SHA in `-c`), then:

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

That starts `release.yml`: `prepare-release` (fails if `Cargo.toml` or the CHANGELOG heading disagrees with the tag) then `release-gate` (nextest plus cold CPU-only UAT on Linux and macOS) then `create-release`, 11 builds and the publish jobs. Green end to end is ~25 min. Watch it in the background; on a failure read only the failing job's log: `gh run view <id> --log-failed`. `gh run rerun <id> --failed` re-runs just the failed jobs and is the right first move for a flake (see `references/flakes.md`).

## 6. Release body

Once `create-release` succeeds, the release exists with auto-generated notes. Replace them: draft from the CHANGELOG section, run an edit pass with whichever no-slop skill is installed (for example `ce-noslop` or `slop-stopper:final-review`), then apply the writing style guide named in the operator's instructions if there is one. Format and the exact section list are in `references/release-body.md`.

```bash
gh release edit vX.Y.Z --notes-file /tmp/body.md
gh release view vX.Y.Z --json body -q .body > /tmp/readback.md
diff /tmp/body.md /tmp/readback.md      # only trailing newlines may differ
```

## 7. Verify

`references/verify-channels.md` has the commands and the expected values. Download one tarball, check it against the aggregate `SHA256SUMS`, untar it and run `--version`; a pipeline that says success and a binary that prints the old version are different truths.

## 8. Report

Close with: what shipped, the tag and release URL, the channel check results, what was skipped or not verified, and any risk. No social posts unless asked (see `references/social.md`).

## Things not to do

- No backwards-compat shims or legacy paths in a release commit.
- Do not edit a dated CHANGELOG section that is already released; add to `[Unreleased]`.
- Do not add a CHANGELOG bullet for a Dependabot actions bump, and do not put implementation detail in one.
- Docs-only release changes need no cargo runs; the hooks skip them.
