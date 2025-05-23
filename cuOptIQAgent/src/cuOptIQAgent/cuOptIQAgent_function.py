import logging
import json
import os
import base64
from datetime import datetime
from typing import Dict, Any, Callable, Awaitable
from pydantic import Field, BaseModel

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

# Configuration class for the CuOpt agent
class cuOptIQAgentFunctionConfig(FunctionBaseConfig, name="cuOptIQAgent"):
    """
    NVIDIA CuOpt Route Optimization Agent using AgentIQ Toolkit.
    This agent helps optimize routes for forklifts in a factory setting.
    """
    llm_name: LLMRef = Field(description="The name of the LLM to use")
    cuopt_api_key: str = Field(default="", description="API key for NVIDIA CuOpt service")
    visualization_enabled: bool = Field(default=True, description="Whether to generate visualizations")
    output_dir: str = Field(default="optimization_results", description="Directory to store visualization outputs")

class FactoryState(BaseModel):
    """State container for route optimization workflow"""
    query: str
    query_type: str = "route_optimization"
    solution: Dict = {}
    errors: list = []
    logs: list = []
    visualization_timestamp: str = None

# Config class (for compatibility)
class Config:
    pass

@register_function(config_type=cuOptIQAgentFunctionConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def cuOptIQAgent_function(
    config: cuOptIQAgentFunctionConfig, builder: Builder
):
    """
    Main function for the CuOpt route optimization agent.
    Now serves as a wrapper that delegates to individual tool functions.
    """
    # Import visualization utilities
    from cuOptIQAgent.visualization_utils import visualize_factory_state
    
    # Get LLM for prompts if needed
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    # Create output directory if it doesn't exist
    os.makedirs(config.output_dir, exist_ok=True)
    
    # Helper to safely get a function from its generator
    async def get_function_safely(
        fn_generator: Callable,
        config_obj: Any
    ) -> Any:
        """Safely get a function from its generator function"""
        async with fn_generator(config_obj, builder) as fn_info:
            return fn_info.single_fn
    
    # Create visualization function
    def create_visualizations(state: FactoryState, output_dir: str) -> FactoryState:
        """Creates visualizations of the optimization results"""
        logger.info("Creating Visualizations...")
        
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Generate timestamp for unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create visualizations for the current state
            visualize_factory_state(
                state,
                output_dir=output_dir,
                filename_prefix=f"optimization_{timestamp}"
            )
            
            # Store the timestamp in the state for UI reference
            state.visualization_timestamp = timestamp
            
            state.logs.append("Visualizations created successfully")
            logger.info("Visualization completed")
            
        except Exception as e:
            error_msg = f"Visualization failed: {str(e)}"
            state.errors.append(error_msg)
            state.logs.append(f"ERROR: {error_msg}")
            logger.error(error_msg)
            
        return state
    
    # Main processing function that coordinates the tools
    async def process_query(query: str) -> Dict:
        """Process a query by using tool functions sequentially"""
        logger.info("Starting query processing workflow...")
        
        # Create a state object to track the workflow
        state = FactoryState(query=query)
        
        try:
            # Import all necessary function modules
            from cuOptIQAgent.analyze_query_function import analyze_query_function, AnalyzeQueryConfig
            from cuOptIQAgent.data_modifier_function import data_modifier_function, DataModifierConfig
            from cuOptIQAgent.cuopt_preparation_function import cuopt_preparation_function, CuoptPreparationConfig
            from cuOptIQAgent.cuopt_solver_function import cuopt_solver_function, CuoptSolverConfig
            
            # Step 1: Analyze the query
            logger.info("Starting query analysis...")
            analyze_config = AnalyzeQueryConfig(name="analyze_query", llm_name=config.llm_name)
            analyze_fn = await get_function_safely(analyze_query_function, analyze_config)
            analyze_result = await analyze_fn(query)
            logger.info("Query analysis completed")
            
            # Step 2: Modify the data based on analysis
            logger.info("Starting data modification...")
            data_modifier_config = DataModifierConfig(name="data_modifier")
            data_modifier_fn = await get_function_safely(data_modifier_function, data_modifier_config)
            modified_data = await data_modifier_fn(analyze_result)
            logger.info("Data modification completed")
            
            # Step 3: Prepare CuOpt input
            logger.info("Starting CuOpt input preparation...")
            cuopt_prep_config = CuoptPreparationConfig(name="cuopt_preparation")
            cuopt_prep_fn = await get_function_safely(cuopt_preparation_function, cuopt_prep_config)
            cuopt_input = await cuopt_prep_fn(modified_data)
            logger.info("CuOpt input preparation completed")
            
            # Step 4: Solve the optimization problem
            logger.info("Starting optimization solve...")
            solver_config = CuoptSolverConfig(name="cuopt_solver", cuopt_api_key=config.cuopt_api_key)
            solver_fn = await get_function_safely(cuopt_solver_function, solver_config)
            solution = await solver_fn(cuopt_input)
            logger.info("Optimization completed")
            
            # Update the state with the solution
            if "solution" in solution:
                state.solution = solution["solution"]
            elif "error" in solution:
                state.errors.append(solution["error"])
            
            # Step 5: Create visualizations if enabled
            if config.visualization_enabled:
                state = create_visualizations(state, config.output_dir)
            
            # Return the results
            return {
                'query_type': state.query_type,
                'solution': state.solution,
                'errors': state.errors,
                'logs': state.logs,
                'visualization_timestamp': state.visualization_timestamp
            }
        
        except Exception as e:
            error_msg = f"Error in processing workflow: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "errors": [error_msg],
                "solution": {},
                "logs": state.logs
            }
    
    # Response function (formats the results for the user)
    async def _response_fn(input_message: str) -> str:
        """Process the input query and return a formatted response"""
        try:
            # Process the query
            result = await process_query(input_message)
            logger.info("Result: %s", result)
            
            # Format the response
            response_text = ""
            
            if result.get('solution'):
                response_text += "**Solution Details:**\n"
                response_text += f"- Total Cost: {result['solution'].get('solution_cost')}\n\n"
                
                if 'readable_routes' in result.get('solution', {}):
                    response_text += "\n**Vehicle Routes:**\n"
                    for vehicle, route in result['solution']['readable_routes'].items():
                        response_text += f"- Forklift {int(vehicle) + 1}: {' → '.join(route)}\n"
            
            if result.get('errors'):
                response_text += "\n**Errors:**\n"
                for error in result['errors']:
                    response_text += f"- {error}\n"
                    
            # Add visualization information
            if result.get('visualization_timestamp'):
                timestamp = result['visualization_timestamp']
                response_text += f"\n**Visualizations:**\n"
                
                # Add Gantt chart image
                gantt_path = f"{config.output_dir}/optimization_{timestamp}_gantt.png"
                if os.path.exists(gantt_path):
                    with open(gantt_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    response_text += f"\n![Gantt Chart](data:image/png;base64,{img_data})\n"
                
                # Add network visualizations for each forklift
                vehicle_data = result.get('solution', {}).get('vehicle_data', {})
                for vehicle_id in sorted(vehicle_data.keys(), key=lambda x: int(x)):
                    network_path = f"{config.output_dir}/optimization_{timestamp}_network_forklift_{int(vehicle_id) + 1}.png"
                    if os.path.exists(network_path):
                        with open(network_path, "rb") as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                        response_text += f"\n![Forklift {int(vehicle_id) + 1} Route](data:image/png;base64,{img_data})\n"
            
            return response_text
        
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    try:
        yield FunctionInfo.create(single_fn=_response_fn)
    except GeneratorExit:
        logger.info("Function exited early!")
    finally:
        logger.info("Cleaning up nvucopt_agent workflow.")