import sys
import os
import json

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.environments.heat_exchanger.env import HeatExchangerEnv
from src.environments.heat_exchanger.simulator import HeatExchangerSimulator
from src.environments.heat_exchanger.reward import HeatExchangerReward
from src.core.logging import setup_logger, save_evaluation_result

def main():
    logger = setup_logger("heat_exchanger_demo")
    logger.info("Heat Exchanger Simulation is starting...")
    
    # Create real environment components
    env = HeatExchangerEnv(
        simulator=HeatExchangerSimulator(),
        reward_function=HeatExchangerReward()
    )
    
    # Task and Design file paths
    task_path = os.path.join(os.path.dirname(__file__), '../configs/tasks/heat_exchanger/task_001.json')
    design_path = os.path.join(os.path.dirname(__file__), '../examples/designs/heat_exchanger_valid_001.json')
    
    # Read files
    with open(task_path, 'r', encoding='utf-8') as f:
        task_params = json.load(f)
        
    with open(design_path, 'r', encoding='utf-8') as f:
        design_params = json.load(f)
        
    logger.info(f"Loaded Task Targets: {task_params}")
    logger.info(f"Design to be Evaluated: {design_params}")
    
    # Run evaluation
    logger.info("Physical simulation and calculations are running...")
    result = env.evaluate("he_task_001", task_params, "valid_design_001", design_params)
    
    # Show results
    logger.info(f"Status: {result.status}")
    if result.status == "success":
        logger.info(f"Calculated Heat Duty: {result.metrics.get('heat_duty', 0):.2f} W")
        logger.info(f"Tube Side Pressure Drop: {result.metrics.get('pressure_drop_tube', 0):.2f} Pa")
        logger.info(f"Shell Side Pressure Drop: {result.metrics.get('pressure_drop_shell', 0):.2f} Pa")
        logger.info(f"Total Area: {result.metrics.get('area', 0):.4f} m^2")
        logger.info(f"Earned Reward: {result.reward.normalized_total:.4f} / 1.0000")
    else:
        logger.error(f"Error Message: {result.error_message}")
        
    # Save as JSON to disk
    saved_path = save_evaluation_result(result)
    logger.info(f"All detailed results are saved here in JSON format: {saved_path}")

if __name__ == "__main__":
    main()
