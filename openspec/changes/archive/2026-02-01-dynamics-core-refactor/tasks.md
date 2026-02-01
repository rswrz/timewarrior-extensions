## 1. Shared core and config resolution

- [x] 1.1 Create `dynamics_common.py` with canonical record dataclass and shared helpers (parsing, merging, formatting helpers)
- [x] 1.2 Implement config resolution defaults -> header -> env, including env key mapping to `TIMEWARRIOR_REPORTS_DYNAMICS_*`
- [x] 1.3 Move LLM refiner into core and wire it to resolved `reports.dynamics.llm.*` settings
- [x] 1.4 Update core to load project config from resolved `reports.dynamics.config_file`

## 2. Refactor report scripts

- [x] 2.1 Update `dynamics_csv.py` to consume `dynamics_common` and keep CSV output identical
- [x] 2.2 Update `dynamics_summary.py` to consume `dynamics_common` and keep table output identical
- [x] 2.3 Ensure only CSV applies LLM refinement and summary remains opt-in

## 3. Documentation

- [x] 3.1 Update `docs/dynamics_csv.md` with new header keys, precedence, and env names
- [x] 3.2 Update `docs/dynamics_summary.md` with new header keys, precedence, and env names
