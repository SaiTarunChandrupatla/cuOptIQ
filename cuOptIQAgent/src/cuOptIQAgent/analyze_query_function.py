
import logging
import json
from typing import Dict
from pydantic import Field
import os

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.cli.register_workflow import register_function
from aiq.data_models.function import FunctionBaseConfig
from aiq.builder.framework_enum import LLMFrameworkEnum
from aiq.data_models.component_ref import LLMRef
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

# Configuration class for the analyze query tool
class AnalyzeQueryConfig(FunctionBaseConfig, name="analyze_query"):
    """
    Analyzes user queries for NVIDIA CuOpt route optimization.
    This tool extracts requirements for fleet size, capacity, and other parameters.
    """
    llm_name: LLMRef = Field(description="The name of the LLM to use")

@register_function(config_type=AnalyzeQueryConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def analyze_query_function(
    config: AnalyzeQueryConfig, builder: Builder
):
    """
    Analyzes user queries to determine optimization requirements.
    """
    # Get the LLM from the builder
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    async def _analyze_fn(query: str) -> Dict:
        """Process the query and return analysis results"""
        logger.info("Starting Query Analysis...")
        
        try:
            prompt = f"""
            You are analyzing queries about route optimization using transport order data.
            
            Current transport order structure:
            - pickup_location: Location where materials need to be picked up (1-4: Insulation, Weather Stripping, Fiber Glass, Shingles)
            - delivery_location: Location where materials need to be delivered (5-8: Trucks 1-4)
            - order_demand: Quantity to be moved
            - earliest_pickup/latest_pickup: Time window for pickup
            - pickup_service_time: Time needed for loading
            - earliest_delivery/latest_delivery: Time window for delivery
            - delivery_service_time: Time needed for unloading

            Location mapping:
            - 1: Insulation
            - 2: Weather Stripping
            - 3: Fiber Glass
            - 4: Shingles
            - 5: Truck 1
            - 6: Truck 2
            - 7: Truck 3
            - 8: Truck 4

            Analyze this query: {query}

            Return a JSON object with:
            {{
                "query_type": string,  // route_optimization, loading_time_analysis, conflict_analysis, add_order, remove_order
                "transport_data_changes": {{
                    "modify_service_times": {{
                        "needed": boolean,
                        "new_value": number or null,
                        "affected_orders": [list of order indices] or "all"
                    }},
                    "modify_time_windows": {{
                        "needed": boolean,
                        "type": "pickup" or "delivery" or null,
                        "new_values": {{
                            "earliest": number or null,
                            "latest": number or null
                        }},
                        "affected_orders": [list of order indices] or "all"
                    }},
                    "remove_orders": {{
                        "needed": boolean,
                        "order_indices": [list of order indices to remove] or null
                    }}
                }},
                "fleet_changes": {{
                    "modify_capacity": {{
                        "needed": boolean,
                        "forklift_id": number or null,
                        "new_capacity": number or null
                    }},
                    "modify_fleet_size": {{
                        "needed": boolean,
                        "new_size": number or null
                    }}
                }},
                "new_orders": [
                    {{
                        "pickup_location": number,
                        "delivery_location": number,
                        "order_demand": number,
                        "earliest_pickup": number,
                        "latest_pickup": number,
                        "pickup_service_time": number,
                        "earliest_delivery": number,
                        "latest_delivery": number,
                        "delivery_service_time": number
                    }}
                ],
                "required_analyses": {{
                    "baseline_needed": boolean,
                    "visualization_needed": true,
                    "conflict_analysis": boolean
                }}
            }}
            
            Make sure to properly parse the number of forklifts and their capacity from the query.
            If the query mentions a specific number of forklifts, set "modify_fleet_size" to "needed": true and "new_size" to that number.
            If the query mentions capacity (how many items each forklift can carry), set "modify_capacity" to "needed": true and "new_capacity" to that number.
            If the query mentions removing orders (like "remove first order" or "remove order 1"), set "remove_orders" to "needed": true and "order_indices" to the indices of orders to remove (0 for first order, 1 for second order, etc.).
            
            """
            
            response = await llm.ainvoke(prompt)
            
            # Add robust error handling for JSON parsing
            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's embedded in text
                content = response.content
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    try:
                        analysis = json.loads(json_str)
                    except:
                        # Create default analysis
                        analysis = create_default_analysis(query)
                else:
                    analysis = create_default_analysis(query)
            
            # Force visualization_needed to True
            if "required_analyses" not in analysis:
                analysis["required_analyses"] = {}
            analysis["required_analyses"]["visualization_needed"] = True
            
            logger.info("Analysis completed successfully")
            logger.info("Analysis Result: %s", json.dumps(analysis, indent=2))
            return analysis
            
        except Exception as e:
            error_msg = f"Query analysis failed: {str(e)}"
            logger.error(error_msg)
            return create_default_analysis(query)
    
    def create_default_analysis(query):
        """Create a default analysis based on the query text"""
        analysis = {
            "query_type": "route_optimization",
            "transport_data_changes": {
                "modify_service_times": {"needed": False},
                "modify_time_windows": {"needed": False},
                "remove_orders": {"needed": False}
            },
            "fleet_changes": {
                "modify_capacity": {"needed": False},
                "modify_fleet_size": {"needed": False}
            },
            "required_analyses": {"visualization_needed": True}
        }
        
        # Check for specific keywords
        if "2 forklifts" in query.lower() or "two forklifts" in query.lower():
            analysis["fleet_changes"]["modify_fleet_size"] = {
                "needed": True,
                "new_size": 2
            }
        elif "3 forklifts" in query.lower() or "three forklifts" in query.lower():
            analysis["fleet_changes"]["modify_fleet_size"] = {
                "needed": True,
                "new_size": 3
            }
        
        if "two items" in query.lower() or "2 items" in query.lower() or "carry two" in query.lower():
            analysis["fleet_changes"]["modify_capacity"] = {
                "needed": True,
                "new_capacity": 2
            }
            
        return analysis
    
    try:
        yield FunctionInfo.create(single_fn=_analyze_fn)
    except GeneratorExit:
        logger.info("Analyze query function exited early!")
    finally:
        logger.info("Cleaning up analyze_query function.")