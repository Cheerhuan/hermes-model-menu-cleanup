# Hermes Model Menu Cleanup 🧹

**Hermes Model Menu Cleanup** is a diagnostic and repair toolkit for the Hermes Agent `/model` menu. When your model picker is cluttered with hundreds of useless entries, duplicate providers (upper/lowercase variants), or ghost entries showing 0 models — this tool precisely identifies the root cause and provides the exact patches needed.

## 🌟 Key Features

- **Five-Layer Injection Audit:** Traces the full `/model` menu construction pipeline — `_PROVIDER_MODELS` → `OPENROUTER_MODELS` → `_MODELS_DEV_PREFERRED` → `PROVIDER_TO_MODELS_DEV` → Phase 4 `custom:` prefix — identifying exactly which layer is injecting unwanted entries.
- **Duplicate Detection:** Catches both slug-level duplicates (identical names) and the subtle `custom:openrouter` vs `openrouter` pattern that bypasses standard dedup mechanisms.
- **Exact Patch Generation:** Produces targeted file-level patches for `models.py` and `model_switch.py` with line numbers and before/after code.

## 🛠 Installation

Requires **Python 3.8+** and Hermes Agent.

```bash
pip install pyyaml
```

The scripts must run from within a Hermes Agent environment (they import from `hermes_cli` and `agent` modules).

## 🚀 Quick Start

```bash
python scripts/audit-model-menu.py
```

This simulates the Gateway's exact provider resolution path and outputs:
- Total providers and models (compared against `config.yaml`)
- Per-provider breakdown with source (`built-in`, `hermes`, `user-config`)
- Duplicate slug/name detection
- Ghost entry detection (0 models)

## 🔍 Five-Layer Injection Model

The `/model` menu is NOT driven by `config.yaml` alone. Five independent layers stack:

| Layer | Source | Effect |
|-------|--------|--------|
| 1 | `_PROVIDER_MODELS` (models.py) | Static curated list |
| 2 | `OPENROUTER_MODELS` hardcoded injection | Forces 34 models regardless of config |
| 3 | `_MODELS_DEV_PREFERRED` merge | models.dev live data overrides curated lists |
| 4 | `PROVIDER_TO_MODELS_DEV` iteration | Any provider with API key appears |
| 5 | Phase 4 `custom:` prefix (model_switch.py) | `config.yaml` providers double-converted |

## ⚙️ Standard Fix Sequence

1. **Trim `_PROVIDER_MODELS`** to only providers with API keys
2. **Remove from `_MODELS_DEV_PREFERRED`** any provider already in curated list
3. **Replace hardcoded OPENROUTER_MODELS** with config.yaml read
4. **Add 0-model filters** at all three Phase append points
5. **Add `provider_key` collision check** in Phase 4 to prevent `custom:openrouter` vs `openrouter` duplicates

Full details in [`SKILL.md`](SKILL.md).

## 🔍 Troubleshooting

- **Audit shows duplicates even after patches:** Clear `.pyc` cache (`rm -f *.pyc`) and restart gateway (`hermes gateway restart`).
- **`custom:openrouter` still appears:** The Phase 4 `provider_key` check may be missing — verify Fix 5 was applied.
- **GitHub Copilot shows 11 models:** This is an auth-store artifact, not a config issue. Separate OAuth cleanup needed.

## 📜 Version History

### v1.0.0
- Initial release with 5-layer audit script and full fix documentation
- Real-world case: reduced 99 models → 15, eliminated 3 duplicate provider pairs

## 📦 Repository

- **License:** MIT
- **Core Files:**
  - `scripts/audit-model-menu.py`: Diagnostic script
  - `SKILL.md`: Complete fix documentation
  - `install.sh`: Cross-platform installer
  - `manifest.json`: Skill manifest

## 🙏 Credits

Built from real-world debugging sessions with Hermes Agent. The `custom:` prefix duplicate discovery was a multi-session investigation spanning model switch failures, gateway restart cycles, and pycache corruption.
