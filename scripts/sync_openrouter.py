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

def main():
    parser = argparse.ArgumentParser(description="Automatically appends models from OpenRouter to models.json.")
    parser.add_argument("--free-only", action="store_true", help="Only adds free models.")
    parser.add_argument("--text-only", action="store_true", help="Only adds text-to-text models.")
    parser.add_argument("--max-prompt-cost", type=float, default=None, help="Max prompt (input) token cost (USD)")
    parser.add_argument("--max-comp-cost", type=float, default=None, help="Max completion (output) token cost (USD)")
    args = parser.parse_args()

    config_data = load_models_json()
    
    # Find or create the "openrouter" provider list
    if "providers" not in config_data:
        config_data["providers"] = {}
    if "openrouter" not in config_data["providers"]:
        config_data["providers"]["openrouter"] = []
        
    existing_models = config_data["providers"]["openrouter"]
    # Put existing model IDs into a set to avoid duplicates
    existing_ids = {item.get("model") for item in existing_models if item.get("model")}

    api_models = fetch_openrouter_models()
    if not api_models:
        return

    added_count = 0
    for m in api_models:
        m_id = m.get("id")
        m_name = m.get("name", m_id.split("/")[-1] if m_id else "Unknown")
        
        if not m_id:
            continue
            
        if args.free_only and not is_model_free(m):
            continue
            
        if args.text_only and not is_text_only(m):
            continue
            
        if not is_cost_under(m, args.max_prompt_cost, args.max_comp_cost):
            continue
            
        if m_id not in existing_ids:
            # Add default parameters to the model
            new_entry = {
                "name": m_id.split("/")[-1].replace(":free", ""), # Short name
                "model": m_id,
                "params": {
                    "temperature": 0.7,
                    "max_tokens": 8192
                }
            }
            existing_models.append(new_entry)
            existing_ids.add(m_id)
            added_count += 1
            print(f"Added: {new_entry['name']} ({m_id})")

    if added_count > 0:
        save_models_json(config_data)
        print(f"\nSuccess! A total of {added_count} new models were added to 'models.json'.")
    else:
        print("\nNo new models to add (All may already exist or none fit the filter).")

if __name__ == "__main__":
    main()
