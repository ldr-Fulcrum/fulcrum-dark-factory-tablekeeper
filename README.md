# fulcrum-dark-factory-tablekeeper

WeAreDevelopers × BAND Dark Factory, hackathon edition. Submission for the **tablekeeper** track by Fulcrum Fortress Consulting.

## Team

Fulcrum Fortress Consulting. Team / factory name: **Dark Fulcrum Force**.

Human participant: **Larry Ross (LDR)**.

## How to read this repository

| Path | What it is |
|---|---|
| `FACTORY.md` | How the factory works, the choices behind it, what it cost, what it caught, and its limits |
| `mandates/` | One standing instruction file per seat, each starting with the harness and model that seat runs |
| `room.json` | The full-session download of the run room, with four tool-result bodies replaced by a redaction notice because they quoted private workspace files. Nothing else was changed. |
| `stage-1/` | Stage 1 service. Build and run it by following `stage-1/RUN.md` |

Only completed stages are included. Add `stage-2/` and later folders here only if they were completed and pass their own checks.

## Seats

| Seat | Harness | Model |
|---|---|---|
| FORGE | Claude Code | `claude-opus-5-5` |
| HAMMER | Codex | `gpt-6.1-sol` |
| ANVIL | Claude Code | `claude-opus-5-5` |
| PROBE | Codex | `gpt-6.1-sol` |
| CONTRA | Claude Code | `claude-opus-5-5` |
| WARDEN | Claude Code | `claude-sonnet-5-5` |

## Running a stage

Each stage folder is a complete, buildable service. It needs only Docker and has no outbound network dependency at run time. Follow the `RUN.md` inside the folder.

## License

MIT, see `LICENSE`.
