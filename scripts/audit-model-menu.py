#!/usr/bin/env python3
"""
audit-model-menu.py — Simulate Gateway behavior and audit /model menu contents.

Usage:
    python3 audit-model-menu.py

Output:
    - Provider count and model count (compared against config.yaml)
    - Per-provider breakdown with source
    - Duplicate slug/name detection
    - Ghost entry detection (0 models)
"""

import sys, yaml, json
from pathlib import Path
from collections import Counter

HERMES_HOME = Path.home() / ".hermes"
sys.path.insert(0, str(HERMES_HOME / "hermes-agent"))

# Clear cached modules to ensure fresh import
for mod in list(sys.modules):
    if any(x in mod for x in ['model_switch', 'models', 'models_dev', 'config', 'providers', 'hermes_constants', 'auth']):
        del sys.modules[mod]

def main():
    cfg = yaml.safe_load(open(HERMES_HOME / "config.yaml"))

    model_cfg = cfg.get("model", {})
    current_model = model_cfg.get("default", "")
    current_provider = model_cfg.get("provider", "openrouter")
    current_base_url = model_cfg.get("base_url", "")

    user_provs = cfg.get("providers")
    from hermes_cli.config import get_compatible_custom_providers
    custom_provs = get_compatible_custom_providers(cfg)

    from hermes_cli.model_switch import list_authenticated_providers
    results = list_authenticated_providers(
        current_provider=current_provider,
        current_base_url=current_base_url,
        current_model=current_model,
        user_providers=user_provs,
        custom_providers=custom_provs,
        max_models=50,
    )

    # Compute expected values from config.yaml
    config_total = 0
    config_providers = set()
    for p_name, p_cfg in cfg.get("providers", {}).items():
        if isinstance(p_cfg, dict):
            config_models = len(p_cfg.get("models", []))
            config_total += config_models
            config_providers.add(p_name)

    menu_total = sum(r['total_models'] for r in results)
    menu_providers = len(results)

    print("=" * 50)
    print(f"config.yaml: {len(config_providers)} providers, {config_total} models")
    print(f"/model menu:  {menu_providers} providers, {menu_total} models")
    print("=" * 50)

    if menu_providers == len(config_providers) and menu_total == config_total:
        print("✅ 完全一致 (Perfect match)")
    else:
        provider_diff = menu_providers - len(config_providers)
        model_diff = menu_total - config_total
        print(f"⚠️  差異: providers {provider_diff:+d}, models {model_diff:+d}")
        print()

    print("\nProvider 明細:")
    for r in results:
        current = " ← CURRENT" if r['is_current'] else ""
        print(f"  [{r['source']:12s}] {r['slug']:25s} | {r['name']:15s} | {r['total_models']:3d} models{current}")

    # Duplicate detection
    slugs = [r['slug'].lower() for r in results]
    dupes = {s: c for s, c in Counter(slugs).items() if c > 1}
    names = [r['name'].lower() for r in results]
    name_dupes = {s: c for s, c in Counter(names).items() if c > 1}

    print(f"\n重複檢查:")
    if not dupes and not name_dupes:
        print("  ✅ 無重複 slug 或 name")
    if dupes:
        print(f"  ⚠️  重複 slug: {dupes}")
    if name_dupes:
        print(f"  ⚠️  重複 name: {name_dupes}")

    # Ghost entry detection
    ghosts = [r for r in results if r['total_models'] == 0]
    if ghosts:
        print(f"  ⚠️  幽靈條目 (0 models): {[r['slug'] for r in ghosts]}")
    else:
        print("  ✅ 無幽靈條目")

if __name__ == "__main__":
    main()
