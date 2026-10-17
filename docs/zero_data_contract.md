# Zero-Data Contract — CLOUDBURNER17

- No runtime artifact writes or persistent application state.
- Agent, supervisor, benchmark, and adapter state remains in process memory.
- Supervised filesystem access is rejected by `zero_data.forbid_file_io`.
- Benchmark sampling uses a local deterministic random generator; it does not
  modify process-global random state.
- Sentinel values are derived from canonical step outputs and are reproducible
  for equivalent inputs.
- Source code and dependencies are loaded before the runtime guard is entered.
