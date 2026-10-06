# FACTORY.md — Dark Fulcrum Force (tablekeeper track)

Every number below comes from the room export, the git history or the harness output named beside it.

## What this is

Dark Fulcrum Force is a six-seat software factory in Band Desktop. One human dispatch goes in; a band of coding agents plans the work, builds it twice independently, checks and attacks both builds, and recommends which one becomes the base. A human decides what ships. The result repository is this one: `stage-1/` is the code the band wrote, `mandates/` are the six seat mandates, `room.json` is the room that did the work.

## The seats (as run)

| Seat | Runtime | Model | Job |
|---|---|---|---|
| FORGE | Claude Code | claude-opus-5-5 | Coordinator: turns the dispatch into sealed handoff packets, routes the work, owns the room |
| HAMMER | Codex | gpt-6.1-sol | Implementer A (built in Python) |
| ANVIL | Claude Code | claude-opus-5-5 | Implementer B (built in Node); later made the one repair |
| PROBE | Codex | gpt-6.1-sol | Independent checker: runs the shipped harness plus its own spec-derived probes against each candidate |
| CONTRA | Claude Code | claude-opus-5-5 | Adversary: attacks each candidate and rates findings BLOCKING, MAJOR or MINOR |
| WARDEN | Claude Code | claude-sonnet-5-5 | Evidence: records diffs and verdicts, recommends the base by a fixed rule, packages the result |

Different runtimes sit on the two implementers (Codex vs Claude Code) to reduce correlated mistakes. Mandates are generic: no endpoints, field names or track terms; the specifics arrive only in the dispatch and the sealed packets.

## How a handoff works

FORGE seals every packet with `seal-packet.mjs` (a hash over the spec reference, base revision, target seat and the packet body). The receiving seat verifies the seal before acting; a failed check makes the handoff HANDOFF_INCOMPLETE and nothing proceeds. The lease is the handoff id plus the attempt number. A repair is allowed once (attempt 2) and only on the surfaces the defect packet names. Failure classes are fixed: IMPLEMENTATION_DEFECT, SPEC_DEFECT, ACCEPTANCE_GAP, HANDOFF_INCOMPLETE.

## How the factory catches a bad result

- Two independent builds, in two languages, from the same dispatch.
- PROBE runs the shipped checks in isolated mode and its own probes under 2 CPUs, 2 GiB and no network.
- CONTRA attacks both candidates and reports findings by severity.
- WARDEN applies a base rule fixed before the run (the candidate PROBE passes comes first), checks that every diff stays inside its allowed paths, and refuses a repair outside its scope.
- No seat accepts or merges anything.

## What happened in the run (times CDT, 2026-10-05; from `room.json` and git)

- 19:38 room created with the band CLI by FORGE (so FORGE owns it; it kept its creation-time name because renaming returned an error).
- 19:43 a pre-run check: the operator asked FORGE, CONTRA and WARDEN to quote their Entry Gate and confirm they carried no earlier context. The message said it was not the stage dispatch and asked for no work.
- 21:15 the Stage 1 dispatch, the only instruction to start work.
- 21:21 to 21:22 FORGE sealed and verified five opening packets.
- 21:46 ANVIL committed its candidate; 21:49 HAMMER committed its candidate. Both stayed inside `stage-1/`.
- PROBE passed HAMMER's candidate (shipped checks 120/120, independent probes 137/137, supplementary 8/8) and failed ANVIL's (a 500-user reset took 13.999 s against a 10 s limit). WARDEN recommended HAMMER's candidate as the base by the fixed rule.
- CONTRA found one BLOCKING issue in each candidate; for HAMMER's it was availability latency above 5 s with 50 requests in flight.
- ANVIL made the one allowed repair on HAMMER's base (commit `b31a575`, three files). CONTRA found the blocking latency issue fixed (availability 0.4 to 1.7 s under load). PROBE then failed the repaired candidate on one 500-user reset run that exceeded 10 s with the time unrecorded; an immediate repeat passed at 5.3 s.
- 23:33 FORGE closed the stage as INCONCLUSIVE: the candidate PROBE had passed carried an unfixed blocking finding, and the repair carried one unresolved PROBE failure. WARDEN's package was READY_FOR_HUMAN_DECISION.
- After the room ended, the human operator chose the repaired candidate and fast-forwarded it into `main`. A human, not a seat, made that choice and merge.
- Independent check afterwards on the committed `main` (`b31a575`): shipped Stage 1 checks 120 of 120, isolated mode, claimed stage 1, no overshoot.

Run size from the export: 1,491 messages, 572 tool calls, about 2 h 18 min from dispatch to FORGE's last turn. Cost was not measured.

## What went wrong, and what we learned

- Earlier rehearsals stopped at the entry gate because nothing produced the "receipt" the mandates required. We defined the receipt (`seal-packet.mjs verify`) and the lease, and gave FORGE the commands it needed to seal packets and add seats.
- Two API rate-limit errors (429) hit FORGE and CONTRA at about 22:13 during the run.
- Timings in the reset probe were sensitive to machine load. The reset failure on the repaired candidate is unresolved: it may be a cold-start or load effect, and we did not rerun it three times.
- Neither build passed everything first time: one was rejected by PROBE and the other needed a repair. That is the review loop doing its job.

## Disclosures

- The operator created the seats and bound them to the room before the dispatch.
- Seats ran with full runtime access on a development host (Claude Code in bypass mode, Codex with approval never and full access). File fences were not enforced, so independence between the two implementers rests on their mandates and on the room and git record, not on sandboxing.
- HAMMER's commit `ac80f58` is authored under the operator's git identity because its worktree had no seat identity set; the room shows HAMMER made it. Identities were fixed for later commits. The repair commit is authored by ANVIL.
- The operator authored three later commits on `main`: a bash-compatible start line added to `stage-1/RUN.md`, the FACTORY.md file, and the README team line. The first touches a file inside `stage-1/`; it is documentation, not service code.
- Four tool results in `room.json` that quoted private workspace instructions were replaced with a redaction notice before publication; nothing else in the export was changed.
- **Known interpretation 1: 422 on login (CONTRA finding I22, rated MAJOR).** Spec section 6 lists format-validation rows (for example a malformed email) without saying which endpoint they bind to. On the login endpoint, a malformed email returns 422 rather than 401. CONTRA reads those rows as endpoint-agnostic; WARDEN treats this as an interpretation gap, since the spec does not scope them. We kept 422 and are recording it here.
- **Known interpretation 2: RUN.md start command (CONTRA finding HAM-F7, MINOR).** The original one-line start command in `stage-1/RUN.md` was PowerShell syntax and did not run in a plain bash shell. PROBE judged it compliant with section 2 of the spec and the spec does not require a POSIX shell. The operator added a bash-compatible line beside it after the room ended.

## Operator decision after the room ended (C2)

The room closed with FORGE's final report: Stage 1 INCONCLUSIVE, with WARDEN's package marked READY_FOR_HUMAN_DECISION. WARDEN had recommended the candidate PROBE passed (C1, HAMMER, `ac80f58`) and left the choice between C1 and the repaired candidate (C2, `b31a575`, ANVIL's single repair on C1) to the human. The operator chose **C2** and fast-forwarded it into `main`, so the history stays linear and unedited. No message was posted in the room for this decision; the room contains the dispatch as its only instruction to start work.

Why C2: C1 passed PROBE but carried one BLOCKING finding from CONTRA, availability latency above the 5 s per-request limit with 50 requests in flight (measured 7.9 s to 104 s depending on grid size). C2 fixes it (0.4 to 1.7 s under load). C2's cost is one PROBE failure: a single 500-user reset run exceeded 10 s with its time unrecorded, and an immediate repeat took 5.3 s (C1's one measurement was 7.0 s). We judged a measured, spec-relevant latency failure worse than one unreproduced cold-start timing, and we say plainly that this trade is a judgement, not a pass.

After the merge, an independent isolated run of the shipped Stage 1 checks on `b31a575` passed 120 of 120, claimed stage 1, with no overshoot.

## Standing the factory up elsewhere

Install Band Desktop and Docker. Create six seats with the mandates in `mandates/` (one file per seat, named after the seat). Give each implementer its own working copy and git identity. Give FORGE a way to run the room commands and the seal command. Send one dispatch from a file, not as an inline argument. Download the full session from the Band console as `room.json`.
