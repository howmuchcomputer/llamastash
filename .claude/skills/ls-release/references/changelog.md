# CHANGELOG format

File layout, top down:

```markdown
## [Unreleased]

## [1.2.3] — 2026-11-30

<intro paragraph>

### Added

- ...

### Changed

- ...

### Fixed

- ...

### Security

- ...

### Contributors

- [@deepu105](https://github.com/deepu105): everything

## [1.2.2] — 2026-11-02
...
```

The em dash in the dated heading is the file's heading format, not prose. The GitHub anchor for `## [1.2.3] — 2026-11-30` is `#123--2026-11-30`: dots, brackets and the em dash dropped, each of the two spaces becomes a dash. Check a rendered anchor with `curl -s https://github.com/llamastash/llamastash/blob/main/CHANGELOG.md | grep -o 'href="#123[^"]*"'`.

## Keeping `[Unreleased]` useful while work lands

Add a bullet the moment a user-visible change lands, not at release time. `## [Unreleased]` stays empty but present so `ci.yml`'s `release-readiness` job always finds the header.

## Writing the bullets

One bullet per user-visible change, one to three sentences, facts and numbers over adjectives.

- Lead with the behaviour a user can observe, then the flag, config key, column or endpoint involved.
- Backticks on every command, flag, config key, metric name and file path.
- Link a PR only when the change reached `main` through a merge: `([#120](https://github.com/llamastash/llamastash/pull/120))`. A direct-to-`main` commit has no PR to link; check with `git log --first-parent v<LAST>..HEAD`.
- Related changes share one bullet with both links: `([#120](...), [#122](...))`.
- A fix bullet names the symptom and the cause in the reader's terms ("the delete reached past what it was shown"), not the internal function.
- No implementation detail, no plan or unit ids, no "internal refactor" entries. A dependency bump only earns a line when it closes an advisory or changes what the binary does.
- Sections you have nothing for are omitted, not left empty.

## Ordering

`Added`, `Changed`, `Fixed`, `Security`, then `Contributors`. Inside a section the headline of the release goes first, then the rest roughly by how much a user notices it.

## The intro paragraph

Two to five sentences, placed under the dated heading and before the first `###`. Name what the release is for in the first sentence, then the two or three facts that make it concrete: a config snippet shape, a route, a metric, a number of new recipes. This is also the text the GitHub release body starts from.

A patch release says so and lists its fixes in one sentence ("A patch release with two TUI fixes. The right pane now follows the row you move to, and ...").

## `### Security`

One bullet per advisory: `crate old → new, clearing [RUSTSEC-2026-0382](https://rustsec.org/advisories/RUSTSEC-2026-0382): what an attacker could do. Transitive via rustls and reqwest.` Note when the affected code is platform-specific. Find the advisories the bump cleared from `cargo audit` output before the bump, not after.

## `### Contributors`

```markdown
### Contributors

- [@external-dev](https://github.com/external-dev): the thing they shipped ([#131](https://github.com/llamastash/llamastash/pull/131))
- [@deepu105](https://github.com/deepu105): everything else
```

A solo release writes `everything` and skips the `Thanks to everyone who shipped code in this release:` line. Dependabot is not listed.

## What does not get a bullet

Dependabot actions bumps, CI plumbing, test-only changes, and doc reorganisations with no new content. A doc change that adds tested recipes or a new config block does get one, because the reader can use it.
