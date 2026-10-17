# sentinel_link

`SentinelLink` provides a process-local append-only ledger. Each entry is
SHA-256 chained and HMAC-SHA256 sealed; `entries()`, `verify()`, and `head()`
operate only on in-memory state. The ledger is discarded when the link object
is released.

- Records the zero-state and, when supplied, the coordinator's Genesis anchor.
- `ingest_substrate(dict)` accepts Waxtablet Engine substrate values.
- Keys may be supplied with `key=` (at least 32 bytes) or through
  `SENTINEL_DOT_KEY`; otherwise an ephemeral in-memory key is used.
- Persistent `log_path` values are rejected. `anchor_record()` returns an
  in-memory value and never creates a file.

```python
from sentinel_link.adapter import connect

link = connect()
link.ingest_substrate({"density": 0.8})
assert link.verify()[0]
```
