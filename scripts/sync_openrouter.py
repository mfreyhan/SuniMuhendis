import os
import json
import urllib.request
import argparse

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODELS_JSON_PATH = os.path.join(REPO_ROOT, "configs", "benchmarks", "models.json")

def load_models_json():
    with open(MODELS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_models_json(data):
    with open(MODELS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        # Append new line at the end
        f.write("\n")

def fetch_openrouter_models():
    print("Fetching models from OpenRouter API (https://openrouter.ai/api/v1/models)...")
    req = urllib.request.Request("https://openrouter.ai/api/v1/models")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("data", [])
    except Exception as e:
        print(f"Error: Could not fetch models from API! ({e})")
        return []

def is_model_free(m):
    # If "free" is in the ID
    if ":free" in m.get("id", ""):
        return True
    
    # or if pricing is 0
    pricing = m.get("pricing", {})
    p_prompt = pricing.get("prompt", "0")
    p_comp = pricing.get("completion", "0")
    
    def is_zero(val):
        if isinstance(val, (int, float)):
            return val == 0
        if isinstance(val, str):
            try:
                return float(val) == 0.0
            except ValueError:
                return False
        return False

    if is_zero(p_prompt) and is_zero(p_comp):
        return True
        
    return False

def is_text_only(m):
    arch = m.get("architecture", {})
    if not arch:
        return True
    modality = arch.get("modality", "")
    if modality == "text->text":
        return True
    if modality: # Reject if it is something like 'text+image->text'
        return False
    return True

def get_model_cost(m, key):
    pricing = m.get("pricing", {})
    val = pricing.get(key, "0")
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return float('inf') # Assume most expensive if unparseable
    return float('inf')

def is_cost_under(m, max_prompt, max_comp):
    if max_prompt is not None:
        if get_model_cost(m, "prompt") > max_prompt:
            return False
    if max_comp is not None:
        if get_model_cost(m, "completion") > max_comp:
            return False
    return True


def build_model_metadata(model):
    """Keep the live API fields that affect benchmark execution."""
    architecture = model.get("architecture") or {}
    top_provider = model.get("top_provider") or {}
    reasoning = model.get("reasoning")

    metadata = {
        "context_length": model.get("context_length"),
        "max_completion_tokens": top_provider.get("max_completion_tokens"),
        "supported_parameters": sorted(model.get("supported_parameters") or []),
        "input_modalities": architecture.get("input_modalities") or [],
        "output_modalities": architecture.get("output_modalities") or [],
        "pricing": model.get("pricing") or {},
    }
    if reasoning is not None:
        metadata["reasoning"] = {
            key: reasoning[key]
            for key in (
                "mandatory",
                "default_enabled",
                "supported_efforts",
                "default_effort",
                "supports_max_tokens",
            )
            if key in reasoning
        }
    return metadata


def refresh_model_metadata(existing_models, api_models):
    """Refresh live capabilities for registry entries already in models.json."""
    api_by_id = {m.get("id"): m for m in api_models if m.get("id")}
    updated = 0
    for item in existing_models:
        api_model = api_by_id.get(item.get("model"))
        if api_model is None:
            continue
        metadata = build_model_metadata(api_model)
        if item.get("metadata") != metadata:
            item["metadata"] = metadata
            updated += 1
    return updated

def prune_openrouter_models(existing_models, api_models):
    """
    Validates existing OpenRouter models against the live OpenRouter API model list.
    Removes models that no longer exist.
    If a :free model no longer exists on OpenRouter, converts it to its base model
    if the base model is live and not already present; otherwise removes it.
    """
    live_ids = {m.get("id") for m in api_models if m.get("id")}
    pruned = []
    converted = []
    kept_models = []
    seen_model_ids = set()

    for item in existing_models:
        m_id = item.get("model")
        if not m_id:
            continue

        if m_id in live_ids:
            if m_id not in seen_model_ids:
                kept_models.append(item)
                seen_model_ids.add(m_id)
            continue

        # Model is not in live_ids!
        if ":free" in m_id:
            base_id = m_id.replace(":free", "")
            if base_id in live_ids:
                if base_id not in seen_model_ids:
                    item["model"] = base_id
                    item["name"] = base_id.split("/")[-1]
                    kept_models.append(item)
                    seen_model_ids.add(base_id)
                    converted.append((m_id, base_id))
                else:
                    # Base model is already in list, drop this dead free duplicate
                    pruned.append(f"{m_id} (redundant, {base_id} already exists)")
            else:
                pruned.append(m_id)
        else:
            pruned.append(m_id)

    return kept_models, pruned, converted

def main():
    parser = argparse.ArgumentParser(
        description="Syncs OpenRouter models and live capability metadata to models.json."
    )
    parser.add_argument("--free-only", action="store_true", help="Only adds free models.")
    parser.add_argument("--text-only", action="store_true", help="Only adds text-to-text models.")
    parser.add_argument("--max-prompt-cost", type=float, default=None, help="Max prompt (input) token cost (USD)")
    parser.add_argument("--max-comp-cost", type=float, default=None, help="Max completion (output) token cost (USD)")
    parser.add_argument("--prune", action="store_true", help="Remove or update models in models.json that no longer exist on OpenRouter.")
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Refresh metadata (and optionally prune) without adding new models.",
    )
    args = parser.parse_args()

    config_data = load_models_json()
    
    # Find or create the "openrouter" provider list
    if "providers" not in config_data:
        config_data["providers"] = {}
    if "openrouter" not in config_data["providers"]:
        config_data["providers"]["openrouter"] = []
        
    existing_models = config_data["providers"]["openrouter"]

    api_models = fetch_openrouter_models()
    if not api_models:
        return

    modified = False

    if args.prune:
        print("\nPruning dead models from models.json...")
        kept_models, pruned, converted = prune_openrouter_models(existing_models, api_models)
        
        for old_id, new_id in converted:
            print(f"  [Converted dead :free] {old_id} -> {new_id}")
        for p in pruned:
            print(f"  [Pruned dead model] {p}")
            
        print(f"Prune summary: {len(pruned)} dead models removed, {len(converted)} dead :free models converted to standard.")
        config_data["providers"]["openrouter"] = kept_models
        existing_models = kept_models
        if pruned or converted:
            modified = True

    metadata_count = refresh_model_metadata(existing_models, api_models)
    if metadata_count:
        modified = True
    print(f"\nMetadata refreshed for {metadata_count} existing models.")

    if not args.no_sync:
        existing_ids = {item.get("model") for item in existing_models if item.get("model")}
        added_count = 0
        for m in api_models:
            m_id = m.get("id")
            if not m_id:
                continue

            if args.free_only and not is_model_free(m):
                continue

            if args.text_only and not is_text_only(m):
                continue

            if not is_cost_under(m, args.max_prompt_cost, args.max_comp_cost):
                continue

            if m_id not in existing_ids:
                new_entry = {
                    "name": m_id.split("/")[-1].replace(":free", ""),
                    "model": m_id,
                    "params": {},
                    "metadata": build_model_metadata(m),
                }
                existing_models.append(new_entry)
                existing_ids.add(m_id)
                added_count += 1
                print(f"Added: {new_entry['name']} ({m_id})")

        if added_count > 0:
            modified = True
            print(f"\nSuccess! A total of {added_count} new models were added to 'models.json'.")
        else:
            print("\nNo new models to add.")

    if modified:
        save_models_json(config_data)
        print("\nSaved updated models to 'models.json'.")
    else:
        print("\n'models.json' is already up to date. No changes made.")

if __name__ == "__main__":
    main()
