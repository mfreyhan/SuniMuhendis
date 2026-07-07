from json_repair import repair_json
import json

def parse_llm_json(raw_text: str) -> dict:
    """
    Takes raw text from LLM, extracts JSON using json_repair, and returns a dictionary.
    """
    try:
        # json-repair handles markdown blocks like ```json ... ``` automatically
        # and fixes missing quotes, trailing commas etc.
        repaired_string = repair_json(raw_text)
        if not repaired_string:
            raise ValueError("No JSON could be extracted from the LLM response.")
            
        parsed_dict = json.loads(repaired_string)
        if isinstance(parsed_dict, list) and len(parsed_dict) > 0:
             return parsed_dict[0] # Sometimes repair returns a list of objects
        return parsed_dict
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from LLM: {str(e)}")
