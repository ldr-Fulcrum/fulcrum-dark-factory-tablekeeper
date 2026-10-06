# FACTORY.md — Working in the Dark (control layer)

**Repo:** `ldr-Fulcrum/working-in-the-dark`  
**Role of this folder:** control / membrane-out factory tooling. Not stage product code.  
**Graded Band result repo:** separate; produced by Band. Do not dump control tooling into it except generic seat packages when the guide requires them.  
**Anti-sprawl rule:** one tree only — `factory/`. Never create dated `oxymoron-*` or rehearsal copy folders for this work. Update in place. Log changes in `00-SESSION-CONTROL.md` as `SC-NNN`.

## Locks (2026-09-29 LDR)

| Item | Value |
|---|---|
| Track | tablekeeper |
| Roster | FORGE, HAMMER, ANVIL, PROBE, CONTRA, WARDEN |
| Option B | private/public membrane; TWIN not an in-room seat |
| CAP-006 working | v2.3 Candidate (`skill-3.zip`, SHA-256 `51e18561ac0356ef771c63f5bd4dc8087b0bdd72161b78e3b06294d4702e8449`); generic fold-in only |
| Contract path | `factory/contracts/handoff_contract.mjs` (+ tests under `factory/tests/`) |
| Repair cap | `attempt_id` ≤ 2 then escalate to WARDEN / LDR |
| Runtimes | Band Desktop = factory; Claude Code / Codex = seat runners + WAR writers; BUILD = external desks |

## LDR decision 2026-10-05: real-run seat runtime and result repository

Decided by LDR on 2026-10-05 for the judged (real) run. Supersedes the narrower seat sandboxes in `SEAT_RUNTIME.md` and the toy seat-local settings under `band-work/seat-config/toy` for the real run.

| Seat | Harness | Band runtime settings (real run) |
|---|---|---|
| FORGE, ANVIL, CONTRA, WARDEN | Claude Code | Full Band runtime access: `permission_mode = bypassPermissions`, `context_mode = bare`, Band spawn sandbox **off**, auth via the wrapper `C:\Users\lross\AppData\Local\Band\claude-bare-with-auth.cmd` as the spawn command |
| HAMMER, PROBE | Codex | `approval_policy = never`, `sandbox_mode = danger-full-access`, Band spawn sandbox off |

**Result repository for the real run:** `dark-factory\band-work\run-result` (fresh repo, branch `main`, operator-authored root files only). Seat working directories: HAMMER `band-work\run-hammer` (`impl/hammer`), ANVIL `band-work\run-anvil` (`impl/anvil`), PROBE `band-work\run-checks`, WARDEN `band-work\run-evidence`, FORGE `band-work\seat-work\run-forge`, CONTRA `band-work\seat-work\run-contra`; implementer harness output `band-work\impl-runs\run`. The real run does **not** use `band-work\result`, `band-work\result-anvil`, `toy-result` or `tk-result`.

**Human-only, unchanged:** Accept, final merge into the graded history branch, submission, and any push remain LDR's alone (ARC_LOCK_005 A2, `WORKTREE_NAMING.md`). Full runtime access widens what a seat *can* touch on this host; it does not delegate any of these decisions. WARDEN still stops at `READY_FOR_HUMAN_DECISION`.

### Run room setup (real run)

The run room was created on 2026-10-05 at 19:38 CT with the band CLI. The CLI makes the creating seat the room owner, so FORGE owns the room and LDR is a posting member. The room is still named "New Session" because the rename request returned HTTP 403. This fits the principle that the band runs the work: the room belongs to a seat, and LDR takes part as a member. All six seats were freshly spawned for this room, with no carry-over from the toy rehearsal.

### Stage 1 disclosures and known interpretations (real run)

Recorded by LDR on 2026-10-05 after WARDEN's Stage 1 report (`S1-H-WARDEN-RET`, status `READY_FOR_HUMAN_DECISION`). Evidence: `band-work\run-evidence\stage-1\PACKAGE.md` and `contra\findings-HAMMER-C2.md`.

**Git identity disclosure (HAMMER C1).** HAMMER's candidate commit `ac80f588` on `impl/hammer` in `run-result` was authored and committed under the operator's global git identity `ldr-Fulcrum <ldr@infinteearth.net>`, not a seat identity. The HAMMER worktree (`band-work\run-hammer`) had no per-worktree `user.name` / `user.email` when HAMMER committed, so git fell back to the global identity. The commit's content is HAMMER's work; LDR did not write it. Per-worktree seat identities were set afterwards (HAMMER now commits as `HAMMER <hammer@seats.invalid>`). The commit was not rewritten, so its hash stays the same as the one cited in the evidence.

**Known interpretation 1: 422 vs 401 on login (CONTRA C2-F1, FORGE reading I22).** The format-validation rows in spec §6 (for example "email not of the form local@domain -> 422") are not scoped to an endpoint. The only row scoped to login is "wrong password or unknown email -> 401". On candidate C2 (`b31a5755`), `POST /auth/login` with a malformed email returns 422 `validation_failed`, not 401. FORGE's reading I22 expects 401. CONTRA rated this MAJOR (interpretation-only) and found no spec sentence that contradicts either reading directly. PROBE noted that the unscoped §6 rows conflict with the I22 reading. WARDEN recorded both readings and left the choice to LDR. LDR accepts the 422 behaviour as a known interpretation of an unscoped spec row, not as a defect. No code change was made for it.

**Known interpretation 2: RUN.md start command is PowerShell-only (CONTRA HAM-F7).** The one-line start command in `run-result`'s `stage-1/RUN.md` uses PowerShell syntax (`; if ($LASTEXITCODE -eq 0) { ... }`). It runs in PowerShell, but not in plain bash or a POSIX shell. PROBE judged it §2-compliant (one documented start command). CONTRA rated it MINOR, and it was left out of the single repair. After LDR merges the chosen candidate, LDR will add a bash/POSIX-equivalent line to `RUN.md`, disclosed in the file as an operator convenience addition. The band-authored PowerShell line stays unchanged. The proposed line is in `band-work\drafts\RUN_md_bash_equivalent.md`.

## Deterministic routing (failure classes)

| Class | Meaning | Route |
|---|---|---|
| `HANDOFF_INCOMPLETE` | Packet missing/invalid; seat must not guess | Return to prior seat or FORGE; do not implement |
| `IMPLEMENTATION_DEFECT` | Code fails frozen acceptance | One repair to HAMMER or ANVIL (same attempt lane); else WARDEN |
| `SPEC_DEFECT` | Spec/design wrong vs outcome | FORGE (ARC design), not silent code patch |
| `ACCEPTANCE_GAP` | New expectation after freeze | BUILD-AUTHOR + LDR; version acceptance; do not weaken suite |

Verdicts from PROBE/CONTRA are **void** unless they bind `stage`, `spec_sha256`, `commit_sha`, `attempt_id` to the current revision (`verifyVerdictBinding`).

## Seat map (Band room)

| Seat | Job | Runtime rec | Model family rec |
|---|---|---|---|
| FORGE | Spec / stage plan / acceptance freeze against track Stage N | Claude Code (planning depth) | Anthropic |
| HAMMER | Primary implementer | **Codex** (sandbox + AGENTS.md) | OpenAI |
| ANVIL | Second implementer / alternate path | **Claude Code** | Anthropic |
| PROBE | Acceptance runner + binding verdict | Codex or Claude Code + `acceptance-runner` skill; Gemini API optional behind runner | Mixed OK |
| CONTRA | Adversarial review; no code edits | Claude Code read-only | Anthropic or Gemini |
| WARDEN | Evidence package, promotion, escalation | Claude Code or human-assisted | Anthropic |

Different families on HAMMER vs ANVIL/CONTRA reduce correlated blind spots. Gemini API key is for seat/model or PROBE tool calls — not a seventh Band seat and not ARC.

## Control session vs receipt emitter

**Use `00-SESSION-CONTROL.md` (SC-NNN) here.** It is the human/operator control log for this competition repo: locks, corrections, source hashes, open items. Independent session from oxymoron / Hack_Trick — same *format*, not a continuation folder.

**Receipt emitter / lab-receipt bridge** is a different use case: machine-readable evidence receipts for runs (integrity, counts, packet delivery). That belongs under `factory/evidence/` and harness outputs, not as a replacement for Session Control. Pattern source on box: Infinite Network lab-receipt reader/bridge mirrors — extract mechanism only; no Tank/lane nouns in membrane-out files.

Do both: Session Control for LDR/ARC narrative state; receipts for deterministic run proof.

## Tooling boundary (guide-facing)

Seats may invoke **control-layer** tools (`handoff_contract` validator, acceptance runner, R-CLI-shaped test runner) without that counting as hand-built stage product code. Hand-built stage code in the **graded result repo** remains disallowed. Custom Band *seat harness* is unverified — until Discord/Desktop confirm, use stock Band harness names and treat R-CLI as a **tool** PROBE invokes, not as the seat harness itself.

## Layout (single tree)

```text
factory/
├── FACTORY.md                 # this file
├── ARC_HANDOFF.md             # paste packet for TEAM_DARK_FORCE
├── SEAT_RUNTIME.md            # Codex vs Claude Code + seat assignment
├── contracts/
│   └── handoff_contract.mjs
├── tests/
│   └── handoff_contract.test.mjs
├── mandates/                  # generic outlines (membrane-out)
├── skeletons/
│   ├── codex/                 # AGENTS.md + config templates
│   └── claude-code/           # CLAUDE.md + settings templates
├── _institution_map/          # membrane-IN; gitignored from graded export
├── evidence/                  # harness receipts (append-only intent)
└── README.md
```

## Anti-sprawl (explicit)

- Do **not** create `oxymoron-*`, `*-rehearsal-YYYYMMDD`, or parallel Arena copies for Dark Factory control work.
- Canonical paths: GitHub `working-in-the-dark` and local Arena sibling `...\02_The_Arena\working-in-the-dark\` (sync; do not fork).
- Box mirror: `/workspace/gh-review/working-in-the-dark/factory/`.

## Next materialization order

1. Contract + tests (WAR: Codex primary writer).
2. Six mandate outlines (ARC), then WAR fills seat packages.
3. Band Desktop: create six seats; dry-run Stage 1.
4. Optional: Gemini-backed PROBE runner behind acceptance skill.

## Build invariants

Locked table: [`BUILD_INVARIANTS.md`](./BUILD_INVARIANTS.md). ARC owns policy; WAR materializes against it only.
