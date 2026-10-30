# TUI: recommended models on the HF pull screen

Date: 2026-10-30 · Type: feat · Branch: `feat/tui-pull-recommended`

## Goal

The HF pull dialog (`Shift+P`) opens on an empty search field that says
"Start typing to search HuggingFace, or paste an owner/repo slug." and offers
nothing else. Show the recommender's ranked picks for this host underneath that
line, the same list `init` / `llamastash recommend` offers, so the user can pick
a model that fits without typing a query.

## Scope

In:

- The Search stage renders the ranked recommendations while the query is empty
  and no HF results are on screen (dialog open, or the field cleared with Esc).
- A note appended to the existing "Start typing …" line saying the rows below
  are the recommended models for this hardware.
- `↑`/`↓` move a cursor over those rows; `Enter` opens the File picker on the
  recommended entry's GGUF repo with that entry's quant preselected.
- Same behaviour offline: the recommender reads the bundled benchmark snapshot,
  no network.

Out (not part of this change):

- No new recommender ranking, weights, or snapshot fields.
- No `recommend` CLI or IPC change; the existing `recommend()` stays the single
  source of the list.
- No on-disk (`RecommendationKind::OnDisk`) rows: they have no HF repo to pull.
  `init`'s interactive prompt already filters them out for the same reason.
- No change to the File picker / Confirm stages other than the preselect.

## Decisions

1. **Hardware source: the daemon's `host_metrics` block, no local probe.**
   `recommend()` needs a `HardwareSnapshot`. The TUI dialog already builds
   `HardwareFitContext` from `App::host_metrics` (backend label, VRAM total, RAM
   total) for the per-file `✓/⚠/✗` fit glyphs, so the recommendation list uses
   the same numbers plus `unified` / `uma_shared_total_bytes` from that block.
   Rejected: `detect_hardware()`, which spawns `nvidia-smi`/`rocm-smi`/
   `system_profiler` in the TUI process on every dialog open (hundreds of ms of
   frozen UI, or a background task plus event plumbing) and would describe the
   machine the TUI runs on rather than the machine that stores the models.
   Consequence: the list and the fit glyphs can never disagree.
2. **Reuse `init::recommender::recommend()`, with the row's numbers split out of
   its prose.** Each row carries a `RecommendationFacts` struct (`params`,
   `quant`, `peak_bytes`, `host_total`, `bench`, `spill_percent`) and
   `RecommendationFacts::prose()` renders that struct as the one-line
   justification `init` prints (R58). The pull dialog reads the fields and lays
   them out in the search table's columns instead of pasting the sentence, so
   the two views read one set of numbers. Only `RecommendationKind::Curated`
   rows are kept; the escape row is redundant because the note line above the
   list already says "paste an owner/repo slug".
3. **Recommendation rows use the search table's columns, plus `quant` and
   `fit`.** `repo` / `fmt` / `params` / `size` line up with
   `render_search_header`'s cells (shared width constants), and the variable
   last column carries the fit verdict instead of the sort-dependent metric: a
   curated row has no downloads to sort by. `fit` is `HardwareFitContext::fit_for`
   on the row's own size, i.e. the File picker's glyph and word, so a row and the
   file `Enter` preselects read the same way; an experts-in-RAM pick shows
   `⚠ spill ~N%` because the picker's `✗ oversize` would contradict the pick.
4. **`Enter` on a recommended row → File picker, recommended quant selected.**
   `Enter` on a search row already means "open this repo's file list", so the
   recommendation row behaves like a search row with two extras. (a) A
   `synthetic`-publisher catalog row names the upstream safetensors repo plus a
   GGUF file the snapshot invents per quant, which no publisher hosts; opening
   it as-is would offer a whole-repo safetensors pull the default backend cannot
   serve, so the row opens the first entry of
   `synthetic_publisher_fallbacks(&entry.repo)` — the head of the same chain
   `init` walks when its first choice misses. (b) The preselect matches the
   quant, not the file name, through `init::download::pick_quant_match` (the
   same case-insensitive rule `init` uses, shortest name wins), because the
   mirrored repo carries the publisher's own file naming. Otherwise the
   existing first-selectable-row rule applies.
5. **Recommendations show when `query is empty && results.is_empty()`.** Under
   the Trending sort an empty query does return HF rows; those stay visible
   rather than being replaced. This keeps one rule ("what used to be the empty
   state now lists recommendations") and no new state machine. Emptying the
   field has to clear the last query's rows and mark its seq dispatched, because
   no new search dispatches for an empty query: otherwise the old results sit
   there and a response still in flight lands in an empty field.
6. **Row text stays on one line**, truncated with `crate::tui::fmt::truncate_end`
   like the search rows, so the 86-column modal never re-wraps a row into two.
7. **The dialog ranks from the bundled snapshot, then refreshes it the way the
   search stage reaches the network.** `init` and `llamastash recommend` rank
   against the snapshot the release pipeline publishes daily
   (`benchmark::load_remote`, gated on a newer `bundle_date` + `min_version`),
   while the binary carries an older copy, so the two lists disagreed on live
   data: three of `init`'s ten picks existed only in the remote tier, and the
   bundled rows for the models both carry were score-0 fork mirrors that lost
   the composite ranking. Opening the dialog now ranks from the bundled copy at
   once and dispatches `spawn_hf_snapshot_refresh`, which sends
   `HfDialogEvent::Snapshot` on the same event channel and runtime the HF search
   uses. A newer snapshot rebuilds `recs` and the fit band in place; anything
   else (offline, fetch or parse failure, nothing newer) leaves the bundled
   ranking and says nothing, as `init`'s fallback does. The snapshot is cached on
   `App` for the session, so this is one ~1.2 MB request per TUI run rather than
   one per dialog open. Rejected: routing the fetch through the daemon (the TUI
   already fetches HF live from its own tasks, and a daemon poll would widen the
   IPC surface for a list only this dialog reads).

8. **Sizing uses the smallest card of the ranked backend, not the daemon's VRAM
   sum.** `host_metrics.gpu_mem_total_bytes` sums every device, so a 2x24 GiB
   box would rank 48 GiB models and a hybrid laptop would rank the iGPU's
   memory on top of the RTX's. `ranked_vram_bytes` takes the minimum non-zero
   `total_memory_bytes` among the rows that belong to the backend it ranked for
   (`init::detection::aggregate_vram_bytes` does the same for `init`). A `multi`
   host that resolves to `cuda` or `hip` is ranked as discrete even when the
   host verdict says `unified`: that verdict comes from `any` device carrying
   the UMA marker, which on a hybrid box is the iGPU.
9. **The `params` column shows the entry's real count**
   (`format_param_count(entry.params)`, the formatter search rows use). The
   recommender's bucket (`32B`, `70B+`) stays in `RecommendationFacts.params`
   because it is what `init`'s prose line says; showing it under a `params`
   header made three different models read identically.
10. **The golden builds its own three-row catalog** instead of ranking the
    bundled snapshot, so a catalog regen cannot fail a rendering test. The
    fixture pins a fits / tight / spill row and asserts all three ranked, so a
    recommender change that drops a row fails loudly instead of silently
    shrinking the fixture.

## Units

One unit; implemented in a single session (the pieces share `hf_dialog.rs`).

### U1 — recommendations in the Search stage

Files created:

- `docs/plans/2026-10-30-001-feat-tui-pull-recommended-models-plan.md` (this file)

Files edited:

- `src/init/detection.rs` — `hardware_from_metrics_inputs()`: build a
  `HardwareSnapshot` from `{ backend key, vram_bytes, ram_total_bytes, unified,
  uma_shared_total_bytes }` for callers that cannot probe locally. Lives here
  because `HardwareSnapshot` is constructed nowhere else outside `detect_hardware()`.
- `src/init/download.rs` — `pick_quant_match` becomes `pub(crate)` so the
  dialog's picker preselect uses `init`'s quant-matching rule instead of a
  second copy of it.
- `src/tui/hf_dialog.rs` — `HardwareFitContext` gains `unified` +
  `uma_shared_total_bytes` and a `recommendations()` method; `HfDialogState`
  gains `recs` (filled by `App::open_hf_dialog`), a `shows_recommendations()`
  predicate, cursor + submit + preselect handling, and the note/rows rendering;
  unit tests.
- `src/tui/app.rs` — `hf_hardware_fit_ctx()` fills the two new fields.
- `src/tui/hf_pull.rs` — nothing expected: keys already route through
  `move_up`/`move_down`/`submit_search`. Verify.
- `src/init/recommender.rs` — `RecommendationFacts` holds the row's numbers and
  `Recommendation::prose()` renders them as the one-line justification `init`
  prints, replacing the stored `justification` string and
  `estimated_peak_bytes`. `FileFit::word()` joins `glyph()`.
- `src/tui/hf_pull.rs` — `spawn_hf_snapshot_refresh()` plus the
  `HfDialogEvent::Snapshot` arm in `apply_hf_dialog_event`, which rebuilds the
  ranking and caches the snapshot on `App`.
- `src/tui/app.rs` — `hf_snapshot` field (session cache) and the refresh
  dispatch in `open_hf_dialog`; tests that a fresher snapshot replaces the
  ranking and survives the next open.
- `tests/tui_e2e_render_test.rs` + `tests/golden/hf-search-empty.txt` — golden
  render of the empty-search state with a fixed `HardwareFitContext` and a
  three-row catalog written into the test, so the fixture is neither
  machine-dependent nor catalog-dependent.
- `docs/usage.md` § HuggingFace pull dialog — the empty-field behaviour + note +
  `Enter` semantics.
- `FEATURES.md` § In-TUI HuggingFace browser — one sentence.
- `CHANGELOG.md` — one line under `[Unreleased]`.

Dependencies: none (single unit).

## Verification

Setup: the worktree shares the main checkout's cargo target dir
(`CARGO_TARGET_DIR=/mnt/work/Workspace/oss-libs/llamastash-rs/llamastash/target`)
so dependency compilation is warm; nothing else to install.

```bash
cargo nextest run --features test-fixtures --test tui_e2e_render_test
cargo nextest run --features test-fixtures --lib tui::hf_dialog
cargo nextest run --features test-fixtures --test tui_e2e_render_test   # goldens
# live: open the dialog against an isolated daemon and confirm the list
# picks up the remote tier's entries (Qwen3.5-35B-A3B, Kimi-Linear, Nemotron)
cargo test --doc --features test-fixtures
```

Plus the repo's normal gates through the pre-commit / pre-push hooks
(`make lint`, `make doc`, full nextest).

E2E (required, user-visible change):

```bash
CARGO_TARGET_DIR=…/target cargo build --bin llamastash
LLAMASTASH_STATE_DIR=<tmp state> ./target/debug/llamastash daemon start
LLAMASTASH_STATE_DIR=… ./target/debug/llamastash   # Shift+P, look at the empty state
```

## Definition of done

- Opening the pull dialog shows the note line plus the host's recommended models;
  clearing the field (Esc on a resting field) shows them again.
- `↑`/`↓` walk the recommendation rows, `Enter` lands on the File picker with the
  recommended quant selected, and the pull flow is unchanged from there.
- Typing a query shows HF results exactly as before; the goldens for the other
  stages are unchanged.
- Docs + CHANGELOG updated in the same commits; goldens regenerated only for the
  intended change.
