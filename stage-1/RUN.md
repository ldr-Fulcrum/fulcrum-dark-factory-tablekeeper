# Stage 1 HTTP service

From the repository root, run this single PowerShell command:

```powershell
docker build -t hammer-stage-1 ./stage-1; if ($LASTEXITCODE -eq 0) { docker run --rm --cpus 2 --memory 2g -e PORT=8080 -p 8080:8080 hammer-stage-1 }
```

The service listens on `0.0.0.0:$PORT` (default 8080). Health is `GET /health`.
The container contains Python and IANA tzdata and requires no outbound access
or external services at runtime. State starts empty; `POST /_test/reset` seeds it.

All Stage 1 routes are implemented using Python's standard library. Booking
transactions and completed retry receipts share one lock, so creations, amendments,
cancellations, batches, resets, imports and exports cannot expose partial state.
Authentication hashes passwords with scrypt (`N=2048, r=8, p=1`, random 128-bit
salt); hashes are computed outside the booking lock, with two bounded workers for
fixture seeding to meet the reset timeout. Bearer sessions never expire.
Repeated local times select the first instant; nonexistent closing times select
the clock transition. Reservation durations are elapsed time.

Exports include private credential hashes, bearer tokens and retry bodies. Keep
them private. Import validates a complete replacement before installing it.
All state is in memory and is lost when the container stops, as permitted.
The unauthenticated test control routes are enabled for the required test contract.
