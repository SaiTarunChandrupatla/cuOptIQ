# cuOptIQ

# cuOptIQAgent: Intelligent Route Optimization with NVIDIA Agent Intelligence Toolkit

![NVIDIA Agent Toolkit Hackathon](https://img.shields.io/badge/NVIDIA-Agent%20Toolkit%20Hackathon-76B900?style=for-the-badge&logo=nvidia&logoColor=white)

#cuOptIQAgent is an intelligent agent system that solves route optimization problems for Intafactory logistics using NVIDIA's Agent Intelligence Toolkit and cuOpt service.

## Overview

This project demonstrates how to build a high-performance agentic AI system using NVIDIA's open-source Agent Intelligence toolkit. cuOptIQAgent helps optimize routes for forklifts transporting materials between storage locations and delivery trucks in a warehouse setting.

Users can interact with the agent using natural language to specify constraints like "optimize routes for 3 forklifts that can carry 2 items each," and receive detailed solutions with visualizations.

## Features

- **Natural Language Interface**: Understand user requirements through conversational queries
- **Intelligent Data Processing**: Modify transport orders and fleet parameters based on user needs
- **High-Performance Optimization**: Leverage NVIDIA cuOpt for solving complex routing problems
- **Rich Visualizations**: Generate interactive charts and network graphs to visualize solutions
- **Modular Architecture**: Specialized agent functions that work together seamlessly


## Architecture

cuOptIQAgent consists of several specialized functions:

- `analyze_query_function`: Interprets user requirements from natural language
- `data_modifier_function`: Adjusts transport data based on analysis
- `cuopt_preparation_function`: Prepares optimization problems for NVIDIA cuOpt
- `cuopt_solver_function`: Submits problems to NVIDIA cuOpt and processes solutions
- `visualization_function`: Creates visual representations of optimization results

## Installation

1. Clone this repository:

git clone https://github.com/NVIDIA/cuOptIQAgent.git
cd cuOptIQAgent

2. Set up the Python environment:

uv venv name
source /name/bin/activate # On Windows: venv\Scripts\activate

3. Install dependencies:

uv pip install agentiq
uv pip install matplotlib

cd cuOptIQAgent
uv pip install -e .

4. Set your API keys:
export OPENAI_API_KEY=your_openai_api_key
export CUOPT_API_KEY=your_nvidia_NIM_cuopt_api_key

Get NVIDIA NIM Cuopt API key from https://build.nvidia.com/



5. Start the agent:

aiq serve --config_file cuOptIQAgent/configs/config.yml --host 0.0.0.0 

6. Start the UI:

cd aiqtoolkit-opensource-ui

npm ci( dependency installation)

npm run dev



