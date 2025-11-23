#!/usr/bin/env python3
"""
Main Coordinator Agent - Orchestrates the multi-agent system
Coordinates between Topology Repair Agent and Resource Optimization Agent
"""

from typing import Dict, List, Optional, Any
import json
import os

# Google ADK imports
from google.adk.agents import Agent
from google.adk.llms import LiteLlm

# Import tool functions directly from specialized agents
from .topology_repair_agent import (
    validate_topology,
    repair_topology_file,
    analyze_topology_structure
)
from .resource_optimization_agent import (
    analyze_topology_resources,
    optimize_deployment_configuration,
    get_gcp_pricing_information,
    compare_deployment_options
)


# ADK Tools for Main Coordinator Agent
def analyze_and_repair_topology(topology_file: str, repair_if_broken: bool = True, output_file: Optional[str] = None) -> dict:
    """Analyze and repair ContainerLab topology file using the Topology Repair Agent.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        repair_if_broken (bool): Whether to repair broken topology files
        output_file (str): Optional output file for repaired topology
        
    Returns:
        dict: Analysis and repair results
    """
    try:
        # First, validate the topology
        validation_result = validate_topology(topology_file)

        if validation_result['status'] != 'success':
            return validation_result

        # If topology is invalid and repair is requested, repair it
        if not validation_result['is_valid'] and repair_if_broken:
            repair_result = repair_topology_file(topology_file, output_file)
            
            if repair_result['status'] != 'success':
                return repair_result
            
            return {
                "status": "success",
                "action": "repaired",
                "original_validation": validation_result,
                "repair_result": repair_result,
                "final_topology_file": output_file or topology_file
            }
        else:
            return {
                "status": "success",
                "action": "validated",
                "validation_result": validation_result,
                "topology_file": topology_file
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def analyze_resources_and_optimize(topology_file: str, region: str = 'us-east4', 
                                 max_vms: int = 10, prefer_spot: bool = False) -> dict:
    """Analyze topology resources and optimize deployment using the Resource Optimization Agent.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        region (str): Google Cloud region
        max_vms (int): Maximum number of VMs to consider
        prefer_spot (bool): Whether to prefer spot instances
        
    Returns:
        dict: Resource analysis and deployment optimization results
    """
    try:
        # Analyze topology resources
        resource_analysis = analyze_topology_resources(topology_file)

        if resource_analysis['status'] != 'success':
            return resource_analysis

        # Optimize deployment based on resource requirements
        total_cpu = resource_analysis['total_cpu']
        total_memory = resource_analysis['total_memory']

        optimization_result = optimize_deployment_configuration(
            total_cpu, total_memory, region, max_vms, prefer_spot
        )
        
        if optimization_result['status'] != 'success':
            return optimization_result
        
        return {
            "status": "success",
            "resource_analysis": resource_analysis,
            "deployment_optimization": optimization_result,
            "summary": {
                "topology_name": resource_analysis['topology_name'],
                "total_nodes": resource_analysis['node_count'],
                "total_cpu": total_cpu,
                "total_memory": total_memory,
                "monthly_cost": optimization_result['deployment_plan']['total_monthly_cost'],
                "region": region,
                "spot_instances": prefer_spot
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def complete_topology_analysis(topology_file: str, region: str = 'us-east4', 
                             repair_if_broken: bool = True, max_vms: int = 10, 
                             prefer_spot: bool = False, output_file: Optional[str] = None) -> dict:
    """Complete end-to-end analysis: repair topology, analyze resources, and optimize deployment.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        region (str): Google Cloud region
        repair_if_broken (bool): Whether to repair broken topology files
        max_vms (int): Maximum number of VMs to consider
        prefer_spot (bool): Whether to prefer spot instances
        output_file (str): Optional output file for repaired topology
        
    Returns:
        dict: Complete analysis results including repair, resources, and optimization
    """
    try:
        # Step 1: Analyze and repair topology
        repair_result = analyze_and_repair_topology(topology_file, repair_if_broken, output_file)
        
        if repair_result['status'] != 'success':
            return repair_result
        
        # Determine which topology file to use for resource analysis
        analysis_file = topology_file
        if repair_result['action'] == 'repaired':
            analysis_file = repair_result['final_topology_file']
        
        # Step 2: Analyze resources and optimize deployment
        optimization_result = analyze_resources_and_optimize(analysis_file, region, max_vms, prefer_spot)
        
        if optimization_result['status'] != 'success':
            return optimization_result
        
        # Step 3: Get cost comparison
        total_cpu = optimization_result['resource_analysis']['total_cpu']
        total_memory = optimization_result['resource_analysis']['total_memory']

        cost_comparison = compare_deployment_options(total_cpu, total_memory, region)
        
        return {
            "status": "success",
            "complete_analysis": {
                "topology_repair": repair_result,
                "resource_analysis": optimization_result['resource_analysis'],
                "deployment_optimization": optimization_result['deployment_optimization'],
                "cost_comparison": cost_comparison,
                "summary": {
                    **optimization_result['summary'],
                    "repairs_applied": repair_result.get('repair_result', {}).get('repair_count', 0),
                    "topology_valid": repair_result.get('validation_result', {}).get('is_valid', True)
                }
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def get_deployment_recommendations(topology_file: str, region: str = 'us-east4', 
                                 budget_constraint: Optional[float] = None, 
                                 performance_priority: str = 'balanced') -> dict:
    """Get deployment recommendations based on topology analysis and constraints.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        region (str): Google Cloud region
        budget_constraint (float): Optional monthly budget constraint
        performance_priority (str): 'cost', 'performance', or 'balanced'
        
    Returns:
        dict: Deployment recommendations with multiple options
    """
    try:
        # Get complete analysis
        analysis = complete_topology_analysis(topology_file, region, True, 10, False)
        
        if analysis['status'] != 'success':
            return analysis
        
        # Extract key information
        total_cpu = analysis['complete_analysis']['resource_analysis']['total_cpu']
        total_memory = analysis['complete_analysis']['resource_analysis']['total_memory']
        
        # Get different deployment options
        options = {}

        # Option 1: On-demand standard
        ondemand_result = optimize_deployment_configuration(total_cpu, total_memory, region, 10, False)
        if ondemand_result['status'] == 'success':
            options['on_demand_standard'] = ondemand_result['deployment_plan']

        # Option 2: Spot standard
        spot_result = optimize_deployment_configuration(total_cpu, total_memory, region, 10, True)
        if spot_result['status'] == 'success':
            options['spot_standard'] = spot_result['deployment_plan']

        # Option 3: High availability (multiple smaller VMs)
        ha_result = optimize_deployment_configuration(total_cpu, total_memory, region, 5, False)
        if ha_result['status'] == 'success':
            options['high_availability'] = ha_result['deployment_plan']
        
        # Filter options based on budget constraint
        if budget_constraint:
            filtered_options = {}
            for option_name, option_data in options.items():
                if option_data['total_monthly_cost'] <= budget_constraint:
                    filtered_options[option_name] = option_data
            options = filtered_options

        # Check if we have any options available
        if not options:
            return {
                "status": "error",
                "error_message": f"No deployment options available within budget constraint of ${budget_constraint}/month"
            }

        # Select best option based on priority
        best_option = None
        if performance_priority == 'cost':
            best_option = min(options.items(), key=lambda x: x[1]['total_monthly_cost'])
        elif performance_priority == 'performance':
            # Prefer on-demand standard for performance
            if 'on_demand_standard' in options:
                best_option = ('on_demand_standard', options['on_demand_standard'])
            else:
                # Fallback to cheapest option if on-demand not available
                best_option = min(options.items(), key=lambda x: x[1]['total_monthly_cost'])
        else:  # balanced
            # Prefer spot standard for balanced approach
            if 'spot_standard' in options:
                best_option = ('spot_standard', options['spot_standard'])
            else:
                # Fallback to cheapest option
                best_option = min(options.items(), key=lambda x: x[1]['total_monthly_cost'])
        
        return {
            "status": "success",
            "recommendations": {
                "all_options": options,
                "recommended_option": {
                    "name": best_option[0],
                    "configuration": best_option[1]
                },
                "budget_constraint": budget_constraint,
                "performance_priority": performance_priority,
                "analysis_summary": analysis['complete_analysis']['summary']
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def generate_deployment_commands(topology_file: str, region: str = 'us-east4', 
                               deployment_option: str = 'spot_standard') -> dict:
    """Generate ready-to-use gcloud CLI commands for deployment.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        region (str): Google Cloud region
        deployment_option (str): Deployment option to use
        
    Returns:
        dict: Generated deployment commands and instructions
    """
    try:
        # Get deployment recommendations
        recommendations = get_deployment_recommendations(topology_file, region)
        
        if recommendations['status'] != 'success':
            return recommendations
        
        # Get the selected deployment option
        if deployment_option not in recommendations['recommendations']['all_options']:
            deployment_option = recommendations['recommendations']['recommended_option']['name']
        
        deployment_config = recommendations['recommendations']['all_options'][deployment_option]

        # Determine if this is a spot instance deployment
        is_spot = 'spot' in deployment_option.lower()

        # Generate gcloud commands
        commands = []
        instructions = []

        # Set project and region
        commands.append(f"# Set your Google Cloud project and region")
        commands.append(f"export PROJECT_ID=your-project-id")
        commands.append(f"export REGION={region}")
        commands.append(f"gcloud config set project $PROJECT_ID")
        commands.append("")

        # Create VMs
        vm_counter = 0
        for vm_config in deployment_config['vm_configurations']:
            machine_type = vm_config['machine_type']
            count = vm_config['count']

            if vm_config['is_custom']:
                # Custom machine type - memory must be in MB
                cpu_cores = vm_config['cpu_cores']
                memory_mb = vm_config['memory_gb'] * 1024

                for i in range(count):
                    vm_counter += 1
                    vm_name = f"containerlab-vm-{vm_counter}"
                    commands.append(f"# Create custom VM {vm_counter} (CPU: {cpu_cores}, Memory: {vm_config['memory_gb']}GB)")
                    commands.append(f"gcloud compute instances create {vm_name} \\")
                    commands.append(f"    --zone=$REGION-a \\")
                    commands.append(f"    --machine-type=custom-{cpu_cores}-{memory_mb} \\")
                    commands.append(f"    --image-family=ubuntu-2004-lts \\")
                    commands.append(f"    --image-project=ubuntu-os-cloud \\")
                    commands.append(f"    --boot-disk-size=20GB \\")
                    if is_spot:
                        commands.append(f"    --preemptible \\")
                    commands.append(f"    --tags=containerlab")
                    commands.append("")
            else:
                # Standard machine type
                for i in range(count):
                    vm_counter += 1
                    vm_name = f"containerlab-vm-{vm_counter}"
                    commands.append(f"# Create standard VM {vm_counter} ({machine_type})")
                    commands.append(f"gcloud compute instances create {vm_name} \\")
                    commands.append(f"    --zone=$REGION-a \\")
                    commands.append(f"    --machine-type={machine_type} \\")
                    commands.append(f"    --image-family=ubuntu-2004-lts \\")
                    commands.append(f"    --image-project=ubuntu-os-cloud \\")
                    commands.append(f"    --boot-disk-size=20GB \\")
                    if is_spot:
                        commands.append(f"    --preemptible \\")
                    commands.append(f"    --tags=containerlab")
                    commands.append("")
        
        # Add ContainerLab installation commands
        commands.append("# Install ContainerLab on each VM")
        commands.append("for vm in $(gcloud compute instances list --filter='tags.items=containerlab' --format='value(name)'); do")
        commands.append("    echo \"Installing ContainerLab on $vm...\"")
        commands.append("    gcloud compute ssh $vm --zone=$REGION-a --command=\"")
        commands.append("        curl -sL https://get.containerlab.dev/installer | sudo bash")
        commands.append("    \"")
        commands.append("done")
        commands.append("")
        
        # Add topology deployment command
        commands.append("# Deploy ContainerLab topology")
        commands.append("# Copy your topology file to one of the VMs and deploy:")
        commands.append("# gcloud compute scp your-topology.clab.yml containerlab-vm-1:~/ --zone=$REGION-a")
        commands.append("# gcloud compute ssh containerlab-vm-1 --zone=$REGION-a --command=\"sudo containerlab deploy -t your-topology.clab.yml\"")
        
        # Generate instructions
        instructions.extend([
            f"Deployment Configuration: {deployment_option}",
            f"Total Monthly Cost: ${deployment_config['total_monthly_cost']:.2f}",
            f"Region: {region}",
            f"VM Count: {sum(vm['count'] for vm in deployment_config['vm_configurations'])}",
            "",
            "Steps:",
            "1. Set your Google Cloud project ID",
            "2. Run the gcloud commands to create VMs",
            "3. Install ContainerLab on all VMs",
            "4. Deploy your topology file",
            "",
            "Note: Make sure to enable the Compute Engine API in your project"
        ])
        
        return {
            "status": "success",
            "deployment_commands": commands,
            "instructions": instructions,
            "deployment_config": deployment_config,
            "estimated_cost": deployment_config['total_monthly_cost']
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


# Validate required environment variables
def _get_openai_base_url() -> str:
    """Get and validate OPENAI_BASE_URL environment variable."""
    base_url = os.getenv("OPENAI_BASE_URL")
    if not base_url:
        raise ValueError(
            "OPENAI_BASE_URL environment variable is not set. "
            "Please configure it in multi_agent_system/.env file."
        )
    return base_url


# ADK Agent for Main Coordinator
coordinator_agent = Agent(
    name="containerlab_gcp_coordinator",
    model=LiteLlm(
        model="openai/Llama-3.1-8B-Instruct",
        api_base=_get_openai_base_url()
    ),
    description=(
        "Main coordinator agent for ContainerLab to Google Cloud Engine deployment. "
        "This agent orchestrates the multi-agent system, coordinating between the "
        "Topology Repair Agent and Resource Optimization Agent to provide complete "
        "end-to-end analysis and deployment recommendations."
    ),
    instruction=(
        "You are the main coordinator agent for ContainerLab to Google Cloud Engine deployment. "
        "You orchestrate a multi-agent system with specialized agents:\n\n"
        "**Available Agents:**\n"
        "1. **Topology Repair Agent**: Validates and repairs ContainerLab topology files\n"
        "2. **Resource Optimization Agent**: Analyzes resources and optimizes GCP deployments\n\n"
        "**Your Responsibilities:**\n"
        "1. **End-to-End Analysis**:\n"
        "   - Coordinate topology repair and resource analysis\n"
        "   - Provide complete deployment recommendations\n"
        "   - Generate ready-to-use deployment commands\n\n"
        "2. **Multi-Agent Coordination**:\n"
        "   - Route requests to appropriate specialized agents\n"
        "   - Combine results from multiple agents\n"
        "   - Provide unified responses to users\n\n"
        "3. **Deployment Planning**:\n"
        "   - Consider budget constraints and performance priorities\n"
        "   - Provide multiple deployment options\n"
        "   - Generate gcloud CLI commands\n\n"
        "4. **User Experience**:\n"
        "   - Provide clear, comprehensive responses\n"
        "   - Explain the multi-agent workflow\n"
        "   - Offer actionable recommendations\n\n"
        "**Workflow:**\n"
        "1. **Topology Analysis**: Use Topology Repair Agent to validate/repair files\n"
        "2. **Resource Analysis**: Use Resource Optimization Agent to analyze requirements\n"
        "3. **Deployment Optimization**: Get optimized GCP deployment configurations\n"
        "4. **Command Generation**: Provide ready-to-use deployment commands\n\n"
        "**Key Features:**\n"
        "- Automatic topology repair for broken files\n"
        "- Dynamic resource parsing from topology files\n"
        "- Nokia SROS lifecycle component support\n"
        "- Cost optimization with spot instances\n"
        "- Multiple deployment options (standard/custom, on-demand/spot)\n"
        "- Ready-to-use gcloud CLI commands\n\n"
        "Always provide comprehensive analysis, clear explanations of the multi-agent process, "
        "and actionable deployment recommendations with cost breakdowns."
    ),
    tools=[
        analyze_and_repair_topology,
        analyze_resources_and_optimize,
        complete_topology_analysis,
        get_deployment_recommendations,
        generate_deployment_commands
    ],
)
