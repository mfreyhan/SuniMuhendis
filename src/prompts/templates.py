import json

def build_heat_exchanger_prompt(task_params: dict) -> str:
    """
    Builds the system prompt and user task for Heat Exchanger design.
    """
    system_prompt = """You are an expert mechanical and chemical engineer specializing in heat exchanger design.
Your task is to design a heat exchanger that meets the requested constraints and maximizes the performance.
You must output YOUR ENTIRE RESPONSE AS A VALID JSON OBJECT matching the following schema.
Do not write any other text or explanations outside the JSON object.

Required JSON Schema:
{
  "geometry_type": "string (either 'concentric_tube' or 'shell_and_tube')",
  "length": "float (meters, e.g. 2.0 to 10.0)",
  "inner_tube_di": "float (inner tube inside diameter in meters, e.g. 0.015)",
  "inner_tube_do": "float (inner tube outside diameter in meters, e.g. 0.020)",
  "outer_shell_di": "float (shell inside diameter in meters, e.g. 0.500)",
  "number_of_tubes": "integer (number of tubes, e.g. 50)",
  "baffle_spacing": "float (baffle spacing in meters, e.g. 0.5)"
}

Engineering Rules (Design Rule Checks):
- inner_tube_do MUST be strictly greater than inner_tube_di
- outer_shell_di MUST be strictly greater than inner_tube_do
- For shell_and_tube geometry, number_of_tubes MUST be > 1.
- For concentric_tube geometry, number_of_tubes MUST be exactly 1.
- All dimensions must be strictly positive.

Performance Objectives:
1. Maximize Heat Duty towards the target while respecting limits.
2. Minimize Tube and Shell Pressure Drops below max limits.
3. Maximize Thermodynamic Effectiveness.
4. Minimize Annualised Cost (capital + operating).
5. Avoid mechanical design warnings (e.g., tube vibration, excessive velocities) or else severe point penalties will apply.
"""

    user_prompt = f"""
Please generate a design for the following task constraints:
Task Details:
{json.dumps(task_params, indent=2)}

Output ONLY valid JSON.
"""

    return system_prompt + "\n" + user_prompt
