# GitHub release body

The pipeline creates the release with `gh release create --generate-notes`. Replace those notes. Start from the release before this one so the shape matches: `gh release view v<PREV> --json body -q .body`.

## Section order

```markdown
# LlamaStash vX.Y.Z

<intro, same text as the CHANGELOG intro, rewritten to stand alone>

## <headline feature, as a claim>

<2-4 short paragraphs: what a user does now, the config or CLI shape, one
concrete number or example. YAML/bash fenced blocks for anything they type.>

## <second headline>

...

## Other fixes worth knowing

- <one line each, backticks on flags and columns>

Full details are in the [changelog](https://github.com/llamastash/llamastash/blob/main/CHANGELOG.md#xyz--yyyy-mm-dd).

## Install

<copied verbatim from the previous release>

## Contributors

- [@deepu105](https://github.com/deepu105): everything
```

Rules:

- One `##` per headline, at most three for a minor release, one for a patch. Ask which change is the headline before ordering; do not lead with whichever section is longest.
- `## Other fixes worth knowing` covers everything else the user notices. Internal work stays out.
- Install block, copied so the one-liners never drift:

```bash
gh release view v<PREV> --json body -q .body | awk '/^## Install/{f=1} /^## Contributors/{f=0} f'
```

- A link to the CHANGELOG anchor, not a copy of the bullets.
- No emoji, no badges, no harness or model attribution, no "what's next" paragraph.

## Before posting

1. Facts final (numbers, flag names, metric names checked against the code or docs).
2. An edit pass over the whole body with whichever no-slop skill is installed (for example `ce-noslop` or `slop-stopper:final-review`); it rewrites wording only, so re-check any length budget afterwards.
3. The operator's writing style guide, if they have one. Its bans win over the skill's choices.
4. No em dash, no curly quotes, no ellipsis character:
   `grep -n "—\|…\|[“”‘’]" /tmp/body.md` should come back empty.

## Apply and confirm

```bash
gh release edit vX.Y.Z --notes-file /tmp/body.md
gh release view vX.Y.Z --json body -q .body > /tmp/readback.md
diff /tmp/body.md /tmp/readback.md
```

`gh release edit` takes no `--json`. The only expected diff is GitHub appending two trailing newlines.
