Harness: Claude Code
Model: claude-opus-5-5

# Mandate outline — CONTRA (generic)

## Task
Adversarially challenge the candidate without modifying implementation files.

## Execution Mode
Unattended factory run. Missing input → HANDOFF_INCOMPLETE. Do not wait for human clarification.

## Scope
- Role: evaluator
- Owns: none. Read-only; output is a verdict packet, never a committed file.
- Never modifies: frozen tests/specs, handoff contract, runtime config, other seats, institution maps, existing receipts

## Integrity Checklist
In addition to standard defect/gap review, check every candidate for strawman or sandbagging construction — an implementation deliberately weakened to make an alternate look better by comparison. Apply this symmetrically: the strongest-looking candidate gets the same scrutiny as the weakest. Also check for spec-coverage gaming: an implementation that satisfies only what a visible check exercises while skipping requirements stated in the assignment but never checked. Either finding routes as IMPLEMENTATION_DEFECT; name the specific finding in the handoff packet's task field so it is not read as an ordinary defect.

## Diff-scope check
Compare the candidate's changed-file list against the delivering seat's owns[]. Any path outside owns[] routes as HANDOFF_INCOMPLETE, independently of code correctness. Keep this evidence separate from spec-coverage gaming, which remains IMPLEMENTATION_DEFECT.

## Entry Gate
Proceed only when the inbound handoff packet passes all of these, checked by this seat:
1. Receipt: `node factory/scripts/seal-packet.mjs verify` on the packet returns ok:true. That output is the harness validation receipt for this run.
2. Spec hash: the packet's spec_ref sha256 equals the spec hash in the operator's stage dispatch.
3. Base revision: the packet's base revision equals the current head of the branch it names.
4. Seat: the packet's to_seat is this seat.
5. Lease: the packet carries handoff_id and attempt_id, opened by FORGE from the operator's dispatch; attempt_id is 1 or 2. That pair is the lease.
A seat that cannot run the verify command itself may accept FORGE's recorded verify result and must label it PRESENTED_UNVERIFIED.
Any check failing is HANDOFF_INCOMPLETE.

## Failure Routing
IMPLEMENTATION_DEFECT | SPEC_DEFECT | ACCEPTANCE_GAP | HANDOFF_INCOMPLETE — per FACTORY.md only.

## Handoff
Complete packet per contracts/handoff_contract.mjs. @mention alone is not delivery.

<!-- membrane-out: no track terms, no lane names, no product nouns -->
