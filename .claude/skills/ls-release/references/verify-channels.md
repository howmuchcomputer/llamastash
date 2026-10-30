# Channel verification

A green pipeline is not proof. Run these after `release.yml` finishes; every one hits the live thing, not the workflow log.

## Release and assets

```bash
gh release view vX.Y.Z --json isDraft,isPrerelease,url,assets --jq '{isDraft,isPrerelease,url,n:(.assets|length)}'
```

Expect `isDraft=false`, 27 assets for 11 targets (tarball + `.sha256` each, plus `install.sh`, `install.ps1`, their sidecars and the aggregate `SHA256SUMS`).

## One artifact, end to end

Download a tarball into a scratch dir on disk (not `/tmp`, which is tmpfs here), check it against the aggregate list, then run the binary:

```bash
d=$(mktemp -d "$PWD/target/.release-check.XXXX")   # on disk, not /tmp
curl -fsSL -o "$d/SHA256SUMS" https://github.com/llamastash/llamastash/releases/download/vX.Y.Z/SHA256SUMS
a=llamastash-X.Y.Z-x86_64-unknown-linux-gnu.tar.gz
curl -fsSL -o "$d/$a" "https://github.com/llamastash/llamastash/releases/download/vX.Y.Z/$a"
grep " $a\$" "$d/SHA256SUMS" > "$d/one.sha"
( cd "$d" && sha256sum -c one.sha && tar xzf "$a" && ./llamastash --version )
rm -rf "$d"
```

`sha256sum -c OK` proves the artifact; `llamastash X.Y.Z` proves the version stamp reached the binary. Also confirm the per-asset sidecar carries the same hash:

```bash
curl -fsSL "https://github.com/llamastash/llamastash/releases/download/vX.Y.Z/$a.sha256"
```

## Install scripts

```bash
curl -fsSL https://llamastash.dev/install.sh | head -1        # Source: ...@vX.Y.Z/scripts/install.sh
curl -fsSL https://llamastash.dev/install.ps1 | head -1
```

## Package channels

| Channel | Check | Expect |
|---|---|---|
| crates.io | `curl -s -A "release-check" https://crates.io/api/v1/crates/llamastash \| jq '.crate.max_stable_version'` | `X.Y.Z` (the API needs a User-Agent) |
| Homebrew tap | `curl -s https://raw.githubusercontent.com/llamastash/homebrew-llamastash/main/Formula/llamastash.rb \| grep -E '^  (version\|url)'` | `version "X.Y.Z"` and a `vX.Y.Z` url |
| Scoop bucket | `curl -s https://raw.githubusercontent.com/llamastash/scoop-llamastash/main/llamastash.json \| jq .version` | `X.Y.Z` |
| AUR source | `curl -s "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=llamastash" \| grep -m1 pkgver=` | `pkgver=X.Y.Z` |
| AUR bin | same with `h=llamastash-bin` | `pkgver=X.Y.Z` |
| AUR git | same with `h=llamastash-git` | the static placeholder `pkgver=0.0.1.r0.g0000000`; its `pkgver()` runs `git describe` at build time, so a real version there means it is stale, not that the release worked |
| Site | `curl -s https://raw.githubusercontent.com/llamastash/llamastash.github.io/main/src/data/version.ts` | `VERSION`/`TAG`/`RELEASED_AT` for this release |

AUR and crates.io can lag the pipeline by a minute or two after the publish job reports success; re-check before concluding anything.

## Nothing to do locally

The dev daemon and the user's real install are out of scope for verification. Never stop or swap a running daemon to "test the release"; verify the downloaded artifact in the scratch dir instead.
