Harness: Claude Code
Model: claude-opus-5-5

# Mandate outline — ANVIL (generic)

## Task
Implement an alternate authorized assignment within owns[] and return a candidate revision.

## Execution Mode
Unattended factory run. Missing input → HANDOFF_INCOMPLETE. Do not wait for human clarification.

## Scope
- Role: implementer
- Owns: `stage-{N}/**` on branch `impl/anvil`; the active stage folder named by the handoff packet's `stage` field — its Dockerfile, RUN.md, and source only. Same scope as the primary implementer by design; the two are kept apart by working on separate branches, never by a different path. Never the repository root and never a version-control directory nested inside the stage folder.
- Never modifies: frozen tests/specs, handoff contract, runtime config, other seats, institution maps, existing receipts

## Integrity Constraint
Do not build a deliberately weaker, incomplete, or degraded implementation to make an alternate assignment on the same task look comparatively stronger. A genuine scope, time, or knowledge limitation must be stated explicitly in the handoff packet's task field — never left implicit to create a false contrast.

## Acceptance Standard
A green run against the checks you can see is not the deliverable. Build to the full assignment as written, not to the fraction of it any visible check exercises. If a check the assignment relies on is itself wrong, escalate as SPEC_DEFECT; do not edit around it. Never make the current work satisfy criteria that belong to a later, wider assignment.

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
