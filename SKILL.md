---
name: hermes-model-menu-cleanup
description: 當 `/model` 選單出現過多無用模型、幽靈 provider、或大小寫/前綴重複條目時，執行完整的根因分析與修復流程。涵蓋五層注入機制的審計與修正。
version: 1.0.0
---

# Hermes Model Menu Cleanup

## 問題症狀
- `/model` 選單顯示的 provider/模型數量遠超 `config.yaml` 定義
- 出現無 API Key 的幽靈 provider（如 GitHub Copilot）
- 同一 provider 出現兩次（`OpenRouter (6)` + `openrouter (6)`）
- 單一 provider 下列出數十個非配置模型

## 根因：五層注入機制

`/model` 選單**不是**只讀 `config.yaml`。它由 `model_switch.py` → `list_authenticated_providers()` 構建，經過五層疊加：

```
config.yaml (15 models)
    ↓
第 1 層: _PROVIDER_MODELS (models.py)      ← 靜態 curated list
    ↓
第 2 層: OPENROUTER_MODELS 全量注入          ← 34 個硬編碼模型（無視 config.yaml）
    ↓
第 3 層: _MODELS_DEV_PREFERRED 合併          ← models.dev 即時資料污染 curated list
    ↓
第 4 層: PROVIDER_TO_MODELS_DEV 遍歷        ← 有 API Key = 自動出現
    ↓
第 5 層: Phase 4 custom_providers (custom: 前綴)  ← config.yaml providers 被二次轉換
```

## 診斷步驟

### 1. 模擬 Gateway 實際行為

```python
import sys, yaml
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".hermes/hermes-agent"))

from hermes_cli.model_switch import list_authenticated_providers
from hermes_cli.config import get_compatible_custom_providers

cfg = yaml.safe_load(open(Path.home() / ".hermes/config.yaml"))
results = list_authenticated_providers(
    current_provider=cfg["model"]["provider"],
    current_base_url=cfg["model"].get("base_url", ""),
    current_model=cfg["model"]["default"],
    user_providers=cfg.get("providers"),
    custom_providers=get_compatible_custom_providers(cfg),
    max_models=50,
)

for r in results:
    print(f"  [{r['source']}] slug='{r['slug']}' name='{r['name']}' | {r['total_models']} models")
```

### 2. 檢查重複 slug

```python
from collections import Counter
dupes = {s: c for s, c in Counter([r['slug'].lower() for r in results]).items() if c > 1}
```

## 標準修復序列

### Fix 1: 限制 `_PROVIDER_MODELS` 僅含已配置的 provider

**檔案**: `hermes_cli/models.py` — `_PROVIDER_MODELS`

將 dict 替換為僅含用戶已配置 API Key 的 provider。移除所有無 API Key 的條目（nous, openai, anthropic, xiaomi, bedrock 等）。

```python
_PROVIDER_MODELS: dict[str, list[str]] = {
    "gemini": [...],
    "nvidia": [...],
    "deepseek": [...],
}
```

### Fix 2: 從 `_MODELS_DEV_PREFERRED` 移除受 curated list 管控的 provider

**檔案**: `hermes_cli/models.py` — `_MODELS_DEV_PREFERRED`

若 provider 已在 `_PROVIDER_MODELS` 中有精心篩選的清單，不應被 models.dev 的即時資料覆蓋。移除 `nvidia`、`gemini` 等。

```python
# 從 frozenset 中刪除 "nvidia" 和 "gemini"
```

效果：NVIDIA 從 53 個 models.dev 模型 → 僅 curated list 的 2 個。Gemini 從 11 → 3。

### Fix 3: 限制 openrouter 僅顯示 config.yaml 中的模型

**檔案**: `hermes_cli/model_switch.py` — `list_authenticated_providers()`

原代碼強制注入全部 34 個 `OPENROUTER_MODELS`。改為從 config.yaml 讀取：

```python
# 替換:
curated["openrouter"] = [mid for mid, _ in OPENROUTER_MODELS]

# 為:
_config_or_models = None
try:
    import yaml
    from hermes_constants import get_hermes_home
    with open(get_hermes_home() / "config.yaml") as _f:
        _cfg = yaml.safe_load(_f)
    _or_cfg = (_cfg.get("providers") or {}).get("openrouter", {})
    _config_or_models = _or_cfg.get("models") if isinstance(_or_cfg, dict) else None
except Exception:
    pass
if _config_or_models:
    curated["openrouter"] = list(_config_or_models)
else:
    curated["openrouter"] = [mid for mid, _ in OPENROUTER_MODELS]
```

同時移除 nous auto-fallback（`curated["nous"] = curated["openrouter"]`）。

### Fix 4: 三個階段加入 0 模型過濾

**檔案**: `hermes_cli/model_switch.py`

在 Phase 1（PROVIDER_TO_MODELS_DEV）、Phase 2（HERMES_OVERLAYS）、Phase 2b（CANONICAL_PROVIDERS）各段的 `total = len(model_ids)` 之前加入：

```python
if not model_ids:
    continue
```

效果：消除 GitHub Copilot 等 0 模型的幽靈條目。

### Fix 5（關鍵）：Phase 4 `custom:` 前綴重複防護

**檔案**: `hermes_cli/model_switch.py` — Phase 4 for 迴圈

這是大小寫重複（`OpenRouter` vs `openrouter`）的真正根因。

`config.py` 的 `_normalize_custom_provider_entry`（line 2390）在 provider 沒有 `name` 欄位時，將 `provider_key` 當作 `name`。Phase 4 用這個 name 生成 `custom:openrouter` slug，與 Phase 1 的 `openrouter` 不同，無法被 `seen_slugs` 攔截。

在 Phase 4 的 entry 遍歷開始處加入 `provider_key` 檢查：

```python
for entry in custom_providers:
    if not isinstance(entry, dict):
        continue

    # Skip if this provider_key is already present as a built-in
    # or user-config slug (avoids custom:openrouter vs openrouter dupes).
    _pk = (entry.get("provider_key") or "").strip().lower()
    if _pk and _pk in seen_slugs:
        continue

    raw_name = (entry.get("name") or "").strip()
    ...
```

## 驗證

修復後執行診斷腳本，確認：

- Provider 數 = config.yaml 中的 provider 數
- 模型總數 = config.yaml 中各 provider 模型數之和
- 零個重複 slug（`Counter` 檢查）
- 無 0 模型幽靈條目

## 部署

```bash
# 清除 pycache
rm -f ~/.hermes/hermes-agent/hermes_cli/__pycache__/model_switch.cpython-*.pyc
rm -f ~/.hermes/hermes-agent/hermes_cli/__pycache__/models.cpython-*.pyc
rm -f ~/.hermes/hermes-agent/hermes_cli/__pycache__/config.cpython-*.pyc

# 重啟 Gateway（需用戶手動執行）
hermes gateway restart
```

## 重要提醒

- **Phase 4 的 `custom:` 前綴重複** 是最容易漏掉的根因。即使 `seen_slugs` 正確，`custom:openrouter` ≠ `openrouter`，繞過了所有 slug-level dedup
- 修復後 Gateway **必須重啟**。Agent 無法在自身會話中重啟 Gateway
- `_MODELS_DEV_PREFERRED` 對已精心篩選的 provider 是汙染源，不是增強
