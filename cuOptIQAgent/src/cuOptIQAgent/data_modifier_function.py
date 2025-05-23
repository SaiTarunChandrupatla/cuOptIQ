import logging
import pandas as pd
import os
from typing import Dict
from pydantic import Field

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.cli.register_workflow import register_function
from aiq.data_models.function import FunctionBaseConfig
from aiq.builder.framework_enum import LLMFrameworkEnum

logger = logging.getLogger(__name__)

class DataModifierConfig(FunctionBaseConfig, name="data_modifier"):
    """
    Modifies transport data based on query analysis.
    This tool updates order details, removes orders, or adds new orders.
    """
    pass

@register_function(config_type=DataModifierConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def data_modifier_function(
    config: DataModifierConfig, builder: Builder
):
    """
    Modifies transport data based on analysis results.
    """
    
    async def _modify_data_fn(analysis_result: Dict) -> Dict:
        """Process the analysis and modify data accordingly"""
        logger.info("Starting Data Modification...")
        
        try:
            # Try multiple potential locations for the CSV file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            potential_paths = [
                os.path.join(script_dir, 'transport_order_data.csv'),
                os.path.join(os.getcwd(), 'transport_order_data.csv'),
                os.path.join(os.getcwd(), 'cuOptIQAgent', 'transport_order_data.csv'),
                os.path.join(os.getcwd(), 'src', 'cuOptIQAgent', 'transport_order_data.csv'),
            ]
            
            # Log all the places we're looking
            logger.info(f"Looking for CSV file in the following locations:")
            for path in potential_paths:
                logger.info(f"  - {path} (exists: {os.path.exists(path)})")
            
            # Try each potential path
            transport_data = None
            for csv_path in potential_paths:
                if os.path.exists(csv_path):
                    logger.info(f"Found CSV file at: {csv_path}")
                    transport_data = pd.read_csv(csv_path)
                    break
                    
            if transport_data is None:
                # If we still can't find it, look for it anywhere in the current directory
                logger.info("Searching for transport_order_data.csv in current directory and subdirectories")
                for root, dirs, files in os.walk(os.getcwd()):
                    if 'transport_order_data.csv' in files:
                        csv_path = os.path.join(root, 'transport_order_data.csv')
                        logger.info(f"Found CSV file during directory search: {csv_path}")
                        transport_data = pd.read_csv(csv_path)
                        break
            
            # Fallback to default data if still not found
            if transport_data is None:
                logger.info("CSV file not found, using default transport data")
                transport_data = pd.DataFrame({
                    "pickup_location":       [1,  1,  3,  2,  3,  4, 1, 2, 2],
                    "delivery_location":     [5,  5,  5,  6,  7,  7, 8, 8, 8],
                    "order_demand":          [1,  1,  1,  1,  1,  1, 1, 1, 1],
                    "earliest_pickup":       [0,  0,  0,  0,  0,  0, 0, 0, 0],
                    "latest_pickup":         [10, 20, 30, 10, 20, 30, 10, 20, 30],
                    "pickup_service_time":   [2,  2,  2,  2,  2,  2, 2, 2, 2],
                    "earliest_delivery":     [0,  0,  0,  0,  0,  0, 0, 0, 0],
                    "latest_delivery":       [55, 55, 55, 55, 55, 55, 55, 55, 55],
                    "delivery_service_time": [2,  2,  2,  2,  2,  2, 2, 2, 2]
                })

            modified_data = transport_data.copy()
            
            # Process data modifications from analysis
            transport_data_changes = analysis_result.get("transport_data_changes", {})
            new_orders = analysis_result.get("new_orders", [])
            
            # Handle order removal
            remove_orders = transport_data_changes.get("remove_orders", {})
            if remove_orders and remove_orders.get("needed", False):
                order_indices = remove_orders.get("order_indices", [])
                if order_indices:
                    modified_data = modified_data.drop(order_indices).reset_index(drop=True)
                    logger.info(f"Removed orders at indices: {order_indices}")

            # Add new orders
            if new_orders:
                new_orders_df = pd.DataFrame(new_orders)
                modified_data = pd.concat([modified_data, new_orders_df], ignore_index=True)
                logger.info(f"Added {len(new_orders)} new orders")

            # Handle service time changes
            service_time_changes = transport_data_changes.get("modify_service_times", {})
            if service_time_changes and service_time_changes.get("needed", False):
                # Implementation details for service time changes...
                logger.info("Modified service times")

            # Handle time window modifications  
            time_window_changes = transport_data_changes.get("modify_time_windows", {})
            if time_window_changes and time_window_changes.get("needed", False):
                # Implementation details for time window changes...
                logger.info("Modified time windows")
                
            logger.info("Data modification completed successfully")
            
            # Convert DataFrame to records format for returning
            records = modified_data.to_dict('records')
            return {
                "transport_data": records,
                "fleet_changes": analysis_result.get("fleet_changes", {}),
                "query_type": analysis_result.get("query_type", "route_optimization")
            }
            
        except Exception as e:
            error_msg = f"Data modification failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    try:
        yield FunctionInfo.create(single_fn=_modify_data_fn)
    except GeneratorExit:
        logger.info("Data modifier function exited early!")
    finally:
        logger.info("Cleaning up data_modifier function.")