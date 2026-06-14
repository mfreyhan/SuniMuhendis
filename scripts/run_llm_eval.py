import sys
import os
import json
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.environments.heat_exchanger.env import HeatExchangerEnv
from src.environments.heat_exchanger.simulator import HeatExchangerSimulator
from src.environments.heat_exchanger.reward import HeatExchangerReward
from src.prompts.templates import build_heat_exchanger_prompt
from src.parsing.json_parser import parse_llm_json
from src.model_clients.dummy_random import DummyRandomClient
from src.model_clients.interactive_browser import InteractiveBrowserClient
from src.core.logging import setup_logger

def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM responses")
    parser.add_argument("--client", type=str, default="dummy", choices=["dummy", "interactive"], help="Client to use")
    args = parser.parse_args()

    logger = setup_logger("llm_evaluator")
    
    # 1. Setup Environment
    env = HeatExchangerEnv(HeatExchangerSimulator(), HeatExchangerReward())
    
    # 2. Load Task
    task_path = os.path.join(os.path.dirname(__file__), '../configs/tasks/heat_exchanger/task_001.json')
    with open(task_path, 'r', encoding='utf-8') as f:
        task_params = json.load(f)
        
    # 3. Setup Client
    if args.client == "interactive":
        client = InteractiveBrowserClient()
    else:
        client = DummyRandomClient()
        
    logger.info(f"Running LLM Evaluation with {client.model_name}")
    
    # 4. Generate Prompt
    prompt = build_heat_exchanger_prompt(task_params)
    
    # 5. Get Model Response
    logger.info("Waiting for model response...")
    raw_response = client.generate_design(prompt)
    logger.info("Received raw response from model.")
    
    # 6. Parse JSON
    try:
        design = parse_llm_json(raw_response)
        logger.info(f"Successfully parsed JSON design: {design}")
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Raw response was: {raw_response}")
        return
        
    # 7. Evaluate in Simulator
    res = env.evaluate("he_task_001", task_params, "llm_design_001", design)
    
    # 8. Report Results
    logger.info(f"Evaluation Status: {res.status}")
    if res.status == "success":
        logger.info(f"Simulation Success! Reward: {res.reward.normalized_total:.4f}")
        logger.info(f"Metrics: {res.metrics}")
    else:
        logger.warning(f"Simulation/DRC/Schema failed. Reason: {res.status}")
        if res.error_message:
            logger.warning(f"Error Details: {res.error_message}")

if __name__ == "__main__":
    main()
