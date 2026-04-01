# Agent instructions

This project uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) for spec-driven changes.

- **Source of truth**: `openspec/specs/<domain>/spec.md`
- **Proposals**: create under `openspec/changes/<change-name>/` (use Cursor command `/opsx:propose` or OpenSpec CLI)
- **Stack**: Python; CLI entry `main.py`; automation in `phone_agent/`

Baseline domains: `architecture`, `cli-and-environment`, `agent-runtime`, `model-and-actions` (under `openspec/specs/<domain>/spec.md`).

Before implementing a feature, read the relevant domain spec and align new behavior with OpenSpec delta specs when using `/opsx:apply` / archive workflow.
