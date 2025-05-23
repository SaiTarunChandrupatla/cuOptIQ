import logging
import json
import pandas as pd
import numpy as np
from typing import Dict, Any
from pydantic import Field

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.cli.register_workflow import register_function
from aiq.data_models.function import FunctionBaseConfig

logger = logging.getLogger(__name__)

class CuoptPreparationConfig(FunctionBaseConfig, name="cuopt_preparation"):
    """
    Preparation function for NVIDIA CuOpt VRP optimization.
    This tool prepares the transport data into the format needed by NVIDIA CuOpt.
    """
    pass  # No special config needed for this function

class Config:
    """Configuration for the factory and CuOpt"""
    # Updated waypoint graph configuration
    WAYPOINT_GRAPH = {
        "edges": [1, 2, 3, 4, 5, 6, 7, 8, 0, 5, 6, 7, 8, 0, 5, 6, 7, 8, 0, 5, 6, 7, 8, 0,
                 5, 6, 7, 8, 0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 1, 2, 3, 4],
        "offsets": [0, 8, 13, 18, 23, 28, 33, 38, 43, 48],
        "weights": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 3, 4, 2, 3, 4, 4, 5, 3, 5, 4, 4, 4, 4,
                   5, 4, 3, 3, 1, 2, 3, 5, 5, 2, 3, 4, 4, 4, 3, 3, 4, 4, 3, 4, 4, 5, 4, 3]
    }

@register_function(config_type=CuoptPreparationConfig)
async def cuopt_preparation_function(
    config: CuoptPreparationConfig, builder: Builder
):
    """
    Prepares the transport data in the format needed for NVIDIA CuOpt.
    """
    
    async def _prepare_fn(input_data: Dict) -> Dict:
        """Prepares cuOpt input from transport data"""
        logger.info("Starting CuOpt input preparation...")
        
        try:
            # Extract the transport data
            transport_data = input_data.get('transport_data')
            
            # Validate transport data
            if transport_data is None or len(transport_data) == 0:
                raise ValueError("Transport data is missing or empty")
                
            # Convert to DataFrame if it's a list of dictionaries
            if isinstance(transport_data, list):
                transport_data = pd.DataFrame(transport_data)
            
            # Prepare task data with explicit type conversion
            task_locations = []
            demand = []
            task_time_windows = []
            service_times = []
            pickup_delivery_pairs = []
            
            # Process each transport order with validation
            for idx, row in transport_data.iterrows():
                try:
                    pickup_loc = int(row['pickup_location'])
                    delivery_loc = int(row['delivery_location'])
                    order_demand = int(row['order_demand'])
                    
                    # Validate pickup data
                    earliest_pickup = int(row['earliest_pickup'])
                    latest_pickup = int(row['latest_pickup'])
                    pickup_service = int(row['pickup_service_time'])
                    
                    # Validate delivery data
                    earliest_delivery = int(row['earliest_delivery'])
                    latest_delivery = int(row['latest_delivery'])
                    delivery_service = int(row['delivery_service_time'])
                    
                    # Add pickup location
                    task_locations.append(pickup_loc)
                    demand.append(order_demand)
                    task_time_windows.append([earliest_pickup, latest_pickup])
                    service_times.append(pickup_service)
                    
                    # Add delivery location
                    task_locations.append(delivery_loc)
                    demand.append(-order_demand)
                    task_time_windows.append([earliest_delivery, latest_delivery])
                    service_times.append(delivery_service)
                    
                    # Add pickup-delivery pair
                    pickup_delivery_pairs.append([2*idx, 2*idx + 1])
                    
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid data in row {idx}: {str(e)}")
            
            # Handle fleet configuration
            num_forklifts = 4  # Default
            forklift_capacity = 1  # Default
            
            # Check for fleet size changes
            fleet_changes = input_data.get('fleet_changes', {})
            if fleet_changes.get("modify_fleet_size", {}).get("needed"):
                num_forklifts = fleet_changes["modify_fleet_size"]["new_size"]
                logger.info(f"Using modified fleet size: {num_forklifts} forklifts")
            
            # Check for capacity changes
            if fleet_changes.get("modify_capacity", {}).get("needed"):
                forklift_capacity = fleet_changes["modify_capacity"]["new_capacity"]
                logger.info(f"Using modified forklift capacity: {forklift_capacity}")
                
            # Create all the vehicle locations at depot (0)
            vehicle_locations = [[0, 0] for _ in range(num_forklifts)]
            
            # Single capacity list for all vehicles
            capacities = [[forklift_capacity] * num_forklifts]
            
            # Time windows for each vehicle
            vehicle_time_windows = [[0, 100] for _ in range(num_forklifts)]
            
            # Construct cuOpt input exactly matching the working format
            cuopt_input = {
                "cost_waypoint_graph_data": {
                    "waypoint_graph": {
                        "0": Config.WAYPOINT_GRAPH
                    }
                },
                "task_data": {
                    "task_locations": task_locations,
                    "demand": [demand],
                    "task_time_windows": task_time_windows,
                    "service_times": service_times,
                    "pickup_and_delivery_pairs": pickup_delivery_pairs
                },
                "fleet_data": {
                    "vehicle_locations": vehicle_locations,
                    "capacities": capacities,
                    "vehicle_time_windows": vehicle_time_windows
                },
                "solver_config": {
                    "time_limit": 5
                }
            }
            
            logger.info("CuOpt input preparation completed successfully")
            return cuopt_input
                
        except Exception as e:
            error_msg = f"cuOpt preparation failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    try:
        yield FunctionInfo.create(single_fn=_prepare_fn)
    except GeneratorExit:
        logger.info("Cleaning up cuopt_preparation function.")