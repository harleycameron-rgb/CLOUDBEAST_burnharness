# sentinel_link

Opens the shared Burnharness ledger: a [Sentinel_dot](https://github.com/harleycameron-rgb/sentinel_dot)
append-only JSONL log, HMAC-SHA256 chained. The other three connectors write through it.

- Records the zero-state (Sentinel_dot genesis hash) and, if a `SentinelDotCoordinator` is passed, its Genesis `block_id`.
- `ingest_substrate(dict)` — Waxtablet_Engine `ignition_substrate -> sentinel_link`.
- `entries()` only reads from a ledger that verifies; `verify()`, `head()`, `anchor_record()` (offline anchor, no network).
- Key: `key=` (≥ 32 bytes) or `SENTINEL_DOT_KEY` (base64). Otherwise an ephemeral key is used (`key_mode = hmac-ephemeral`) and the ledger can only be verified while the object lives.

```python
from sentinel_link.adapter import connect
link = connect("burnharness.jsonl")          # key from SENTINEL_DOT_KEY
```
