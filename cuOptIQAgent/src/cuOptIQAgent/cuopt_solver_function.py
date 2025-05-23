import logging
import json
import os
import requests
import time
from typing import Dict, Any
from pydantic import Field

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.cli.register_workflow import register_function
from aiq.data_models.function import FunctionBaseConfig
from aiq.builder.framework_enum import LLMFrameworkEnum

logger = logging.getLogger(__name__)

class CuoptSolverConfig(FunctionBaseConfig, name="cuopt_solver"):
    """
    Solver function for NVIDIA CuOpt VRP optimization.
    This tool submits the optimization problem to NVIDIA CuOpt.
    """
    cuopt_api_key: str = Field(default="", description="API key for NVIDIA CuOpt service")

class Config:
    """Configuration for the CuOpt solver"""
    # API endpoints
    CUOPT_INVOKE_URL = "https://optimize.api.nvidia.com/v1/nvidia/cuopt"
    CUOPT_STATUS_URL = "https://optimize.api.nvidia.com/v1/status/"
    
    # Location mapping for readable output
    LOCATION_MAP = {
        0: "Forklift Depot",
        1: "Insulation",
        2: "Weather Stripping",
        3: "Fiber Glass", 
        4: "Shingles",
        5: "Truck 1",
        6: "Truck 2",
        7: "Truck 3",
        8: "Truck 4"
    }

@register_function(config_type=CuoptSolverConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def cuopt_solver_function(
    config: CuoptSolverConfig, builder: Builder
):
    """
    Submits the optimization problem to NVIDIA CuOpt and retrieves the solution.
    """
    
    async def _solve_fn(input_data: Dict) -> Dict:
        """Solve the optimization problem using NVIDIA CuOpt API"""
        logger.info("Starting CuOpt solver invocation...")
        logger.info("CuOpt Input: %s", json.dumps(input_data, indent=2))
        
        try:
            # Ensure we have a valid API key
            api_key = config.cuopt_api_key
            if not api_key:
                api_key = os.environ.get("CUOPT_API_KEY", "")
                
            if not api_key:
                raise ValueError("No API key provided for NVIDIA CuOpt")
            
            # Extract the cuopt_input if needed
            cuopt_input = input_data
            if "cuopt_input" in input_data:
                cuopt_input = input_data["cuopt_input"]
                
            # Remove any error key if it exists (from preparation phase)
            if "error" in cuopt_input:
                error_msg = cuopt_input["error"]
                logger.error(f"Error in CuOpt input: {error_msg}")
                return {"error": error_msg}
            
            # Prepare the request headers and data - using the exact format from the tutorial
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Prepare the payload in the correct format with action field
            payload = {
                "action": "cuOpt_OptimizedRouting",
                "data": cuopt_input
            }
            
            logger.info("Submitting problem to NVIDIA CuOpt API...")
            
            # Use a session object like in the example
            session = requests.Session()
            response = session.post(Config.CUOPT_INVOKE_URL, headers=headers, json=payload)
            
            # Handle the 202 response code with polling
            while response.status_code == 202:
                request_id = response.headers.get("NVCF-REQID")
                logger.info(f"Request ID: {request_id}")
                fetch_url = Config.CUOPT_STATUS_URL + request_id
                response = session.get(fetch_url, headers=headers)
                time.sleep(1)  # Wait between polls
            
            # Check for successful response
            response.raise_for_status()
            solution = response.json()
            
            # Extract the solver response from the proper nesting
            if 'response' in solution and 'solver_response' in solution['response']:
                solver_response = solution['response']['solver_response']
                
                # Process routes into readable format
                readable_map = {
                    0: ": Forklift",
                    1: ": Insulation",
                    2: ": Weather Stripping",
                    3: ": Fiber Glass",
                    4: ": Shingles",
                    5: ": Truck 1",
                    6: ": Truck 2",
                    7: ": Truck 3",
                    8: ": Truck 4"
                }
                
                converted_route = {}
                if 'vehicle_data' in solver_response:
                    for vehicle in solver_response['vehicle_data']:
                        if vehicle not in converted_route:
                            converted_route[vehicle] = []
                        count = 0
                        vehicle_data = solver_response['vehicle_data'][vehicle]
                        for loc in vehicle_data['route']:
                            if count < len(vehicle_data['type']) and vehicle_data['type'][count] != 'w':
                                converted_route[vehicle].append(
                                    f"{vehicle_data['type'][count]}{readable_map[loc]}"
                                )
                            count += 1
                
                # Format the processed solution
                processed_solution = {
                    'status': solver_response.get('status'),
                    'solution_cost': solver_response.get('solution_cost'),
                    'vehicle_data': solver_response.get('vehicle_data', {}),
                    'readable_routes': converted_route,
                }
                
                return {
                    "solution": processed_solution,
                    "raw_response": solution
                }
            else:
                error_msg = "Invalid response format from CuOpt API"
                logger.error(error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"Error in CuOpt solver: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    try:
        yield FunctionInfo.create(single_fn=_solve_fn)
    except GeneratorExit:
        logger.info("Cleaning up cuopt_solver function.") 