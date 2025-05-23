import logging
import os
from typing import Dict, Any
from pydantic import Field
from datetime import datetime

from aiq.builder.builder import Builder
from aiq.builder.function_info import FunctionInfo
from aiq.cli.register_workflow import register_function
from aiq.data_models.function import FunctionBaseConfig
from aiq.builder.framework_enum import LLMFrameworkEnum

# Import visualization utilities
from cuOptIQAgent.visualization_utils import (
    visualize_factory_state, 
    get_visualization_markdown
)

logger = logging.getLogger(__name__)

class VisualizationConfig(FunctionBaseConfig, name="visualization"):
    """
    Creates visualizations for route optimization solutions.
    This tool generates route maps, Gantt charts, and other visual outputs.
    """
    output_dir: str = Field(default="optimization_results", description="Directory to store visualization outputs")

@register_function(config_type=VisualizationConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def visualization_function(
    config: VisualizationConfig, builder: Builder
):
    """
    Creates visualizations for CuOpt optimization solutions.
    """
    
    async def _visualize_fn(data: Dict) -> Dict:
        """Create visualizations from solution data"""
        logger.info("Starting visualization generation...")
        
        try:
            # Extract data
            solution = data.get("solution", {})
            raw_solution = data.get("raw_solution", {})
            query_type = data.get("query_type", "route_optimization")
            
            if not solution:
                error_msg = "No solution data provided for visualization"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Create output directory if it doesn't exist
            output_dir = config.output_dir
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")
            
            # Generate timestamp for unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create a state object that mimics the expected structure
            # This is needed because visualization_utils expects a specific state format
            class VisualizationState:
                def __init__(self, solution_data):
                    self.solution = solution_data
                    self.query = query_type
            
            state = VisualizationState(solution)
            
            # Generate visualizations
            logger.info(f"Generating visualizations with timestamp {timestamp}...")
            visualize_factory_state(
                state=state,
                output_dir=output_dir,
                filename_prefix=f"optimization_{timestamp}"
            )
            
            # Generate markdown for embedding visualizations
            visualization_markdown = get_visualization_markdown(
                output_dir=output_dir,
                timestamp=timestamp
            )
            
            logger.info("Visualization generation completed successfully")
            
            # Return the enhanced data
            return {
                "solution": solution,
                "raw_solution": raw_solution if raw_solution else None,
                "visualization_timestamp": timestamp,
                "visualization_dir": output_dir,
                "visualization_markdown": visualization_markdown
            }
            
        except Exception as e:
            error_msg = f"Visualization generation failed: {str(e)}"
            logger.error(error_msg)
            return {
                "solution": data.get("solution", {}),
                "errors": [error_msg]
            }
    
    try:
        yield FunctionInfo.create(single_fn=_visualize_fn)
    except GeneratorExit:
        logger.info("Visualization function exited early!")
    finally:
        logger.info("Cleaning up visualization function.")
        