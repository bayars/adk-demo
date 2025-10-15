#!/usr/bin/env python3
"""
Resource Optimization Agent - Specialized agent for GCP deployment optimization
Part of the multi-agent system for ContainerLab to GCP deployment
"""

import yaml
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

# Google ADK imports
from google.adk.agents import Agent


@dataclass
class NodeResourceRequirements:
    """Represents resource requirements for a single node"""
    name: str
    kind: str
    cpu_cores: int
    memory_gb: int
    estimated_cpu_cores: int
    estimated_memory_gb: int
    components: List[Dict] = field(default_factory=list)
    custom_resources: Optional[Dict] = None


@dataclass
class VMConfiguration:
    """Represents a VM configuration"""
    machine_type: str
    cpu_cores: int
    memory_gb: int
    count: int
    hourly_cost: float
    monthly_cost: float
    is_custom: bool = False


@dataclass
class DeploymentPlan:
    """Represents the complete deployment plan"""
    total_cpu_cores: int
    total_memory_gb: int
    vm_configurations: List[VMConfiguration]
    total_hourly_cost: float
    total_monthly_cost: float
    region: str
    optimization_notes: List[str]
    spot_savings: Optional[float] = None


class ContainerLabResourceParser:
    """Parses ContainerLab topology files and extracts resource requirements"""
    
    def __init__(self):
        # Base resource mapping for different node kinds (fallback)
        self.NODE_RESOURCE_MAPPING = {
            'nokia_srlinux': {
                'default': {'cpu': 2, 'memory': 4},
                'ixrd3': {'cpu': 4, 'memory': 8},
            },
            'nokia_sros': {
                'default': {'cpu': 4, 'memory': 8},
                'cpm': {'cpu': 2, 'memory': 4},
                'linecard': {'cpu': 1, 'memory': 2},
            },
            'linux': {'cpu': 1, 'memory': 2},
            'cisco_iosxe': {'cpu': 2, 'memory': 4},
            'cisco_iosxr': {'cpu': 2, 'memory': 4},
            'juniper_vmx': {'cpu': 2, 'memory': 4},
            'arista_ceos': {'cpu': 2, 'memory': 4},
            'sonic': {'cpu': 2, 'memory': 4},
            'frr': {'cpu': 1, 'memory': 2},
            'quagga': {'cpu': 1, 'memory': 2},
        }
        
        # SROS lifecycle component mappings
        self.SROS_COMPONENT_MAPPING = {
            'cpm': {'cpu': 2, 'memory': 4},
            'cpm2': {'cpu': 2, 'memory': 4},
            'cpm3': {'cpu': 2, 'memory': 4},
            'cpm4': {'cpu': 2, 'memory': 4},
            'linecard': {'cpu': 1, 'memory': 2},
            'mda': {'cpu': 1, 'memory': 2},
            'iom': {'cpu': 1, 'memory': 2},
            'sfm': {'cpu': 1, 'memory': 2},
        }
    
    def parse_topology_file(self, file_path: str) -> Tuple[List[NodeResourceRequirements], Dict]:
        """Parse ContainerLab topology file and extract resource requirements"""
        try:
            with open(file_path, 'r') as file:
                topology_data = yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f"Failed to parse topology file {file_path}: {e}")
        
        topology = topology_data.get('topology', {})
        if 'nodes' not in topology:
            raise ValueError("Invalid ContainerLab topology file: missing 'nodes' section")
        
        nodes = []
        for node_name, node_config in topology['nodes'].items():
            node_req = self._extract_node_requirements(node_name, node_config)
            nodes.append(node_req)
        
        return nodes, topology_data
    
    def _extract_node_requirements(self, name: str, config: Dict) -> NodeResourceRequirements:
        """Extract resource requirements for a single node"""
        kind = config.get('kind', 'linux')
        node_type = config.get('type', 'default')
        
        # Check for custom resource specifications in the topology
        custom_resources = self._extract_custom_resources(config)
        
        # Handle SROS lifecycle components
        components = self._extract_sros_components(config)
        
        # Calculate base requirements
        if custom_resources:
            base_req = custom_resources
        elif components:
            base_req = self._calculate_sros_resources(components)
        else:
            base_req = self._get_standard_resources(kind, node_type)
        
        # Calculate estimated requirements (add overhead for containerization)
        estimated_cpu = base_req['cpu'] + 1
        estimated_memory = base_req['memory'] + 2
        
        return NodeResourceRequirements(
            name=name,
            kind=kind,
            cpu_cores=base_req['cpu'],
            memory_gb=base_req['memory'],
            estimated_cpu_cores=estimated_cpu,
            estimated_memory_gb=estimated_memory,
            components=components,
            custom_resources=custom_resources
        )
    
    def _extract_custom_resources(self, config: Dict) -> Optional[Dict]:
        """Extract custom resource specifications from node config"""
        resource_keys = ['resources', 'resource', 'cpu', 'memory', 'ram']
        
        for key in resource_keys:
            if key in config:
                resource_config = config[key]
                if isinstance(resource_config, dict):
                    cpu = resource_config.get('cpu', resource_config.get('cores', 0))
                    memory = resource_config.get('memory', resource_config.get('ram', 0))
                    if cpu > 0 and memory > 0:
                        return {'cpu': cpu, 'memory': memory}
                elif isinstance(resource_config, str):
                    try:
                        parts = resource_config.lower().replace(' ', '').split(',')
                        cpu = memory = 0
                        for part in parts:
                            if 'cpu' in part:
                                cpu = int(part.replace('cpu', ''))
                            elif 'gb' in part or 'memory' in part:
                                memory = int(part.replace('gb', '').replace('memory', ''))
                        if cpu > 0 and memory > 0:
                            return {'cpu': cpu, 'memory': memory}
                    except ValueError:
                        pass
        
        return None
    
    def _extract_sros_components(self, config: Dict) -> List[Dict]:
        """Extract SROS lifecycle components from node config"""
        components = []
        
        sros_configs = ['sros', 'components', 'lifecycle', 'modules']
        
        for config_key in sros_configs:
            if config_key in config:
                component_config = config[config_key]
                if isinstance(component_config, dict):
                    for comp_name, comp_config in component_config.items():
                        if isinstance(comp_config, dict):
                            count = comp_config.get('count', 1)
                            comp_type = comp_config.get('type', comp_name)
                            components.append({
                                'name': comp_name,
                                'type': comp_type,
                                'count': count
                            })
                elif isinstance(component_config, list):
                    for comp in component_config:
                        if isinstance(comp, dict):
                            components.append(comp)
                        elif isinstance(comp, str):
                            components.append({'name': comp, 'type': comp, 'count': 1})
        
        # Also check for direct component specifications
        for comp_name in self.SROS_COMPONENT_MAPPING.keys():
            if comp_name in config:
                count = config[comp_name] if isinstance(config[comp_name], int) else 1
                components.append({
                    'name': comp_name,
                    'type': comp_name,
                    'count': count
                })
        
        return components
    
    def _calculate_sros_resources(self, components: List[Dict]) -> Dict:
        """Calculate total resources for SROS components"""
        total_cpu = 0
        total_memory = 0
        
        for component in components:
            comp_type = component.get('type', component.get('name', ''))
            count = component.get('count', 1)
            
            if comp_type in self.SROS_COMPONENT_MAPPING:
                req = self.SROS_COMPONENT_MAPPING[comp_type]
                total_cpu += req['cpu'] * count
                total_memory += req['memory'] * count
        
        # Ensure minimum resources
        total_cpu = max(total_cpu, 2)
        total_memory = max(total_memory, 4)
        
        return {'cpu': total_cpu, 'memory': total_memory}
    
    def _get_standard_resources(self, kind: str, node_type: str) -> Dict:
        """Get standard resource requirements for a node kind/type"""
        if kind in self.NODE_RESOURCE_MAPPING:
            if isinstance(self.NODE_RESOURCE_MAPPING[kind], dict):
                if node_type in self.NODE_RESOURCE_MAPPING[kind]:
                    return self.NODE_RESOURCE_MAPPING[kind][node_type]
                else:
                    return self.NODE_RESOURCE_MAPPING[kind].get('default', {'cpu': 2, 'memory': 4})
            else:
                return self.NODE_RESOURCE_MAPPING[kind]
        else:
            return {'cpu': 2, 'memory': 4}
    
    def get_total_requirements(self, nodes: List[NodeResourceRequirements]) -> Tuple[int, int]:
        """Get total resource requirements across all nodes"""
        total_cpu = sum(node.estimated_cpu_cores for node in nodes)
        total_memory = sum(node.estimated_memory_gb for node in nodes)
        return total_cpu, total_memory


class GCPPricingProvider:
    """Provides Google Cloud Platform pricing information"""
    
    # N2 machine type pricing for us-east4 region (as of 2024)
    N2_PRICING = {
        'n2-standard-2': {'cpu': 2, 'memory': 8, 'hourly': 0.097, 'monthly': 65.28},
        'n2-standard-4': {'cpu': 4, 'memory': 16, 'hourly': 0.194, 'monthly': 130.56},
        'n2-standard-8': {'cpu': 8, 'memory': 32, 'hourly': 0.388, 'monthly': 261.12},
        'n2-standard-16': {'cpu': 16, 'memory': 64, 'hourly': 0.774, 'monthly': 520.92},
        'n2-standard-32': {'cpu': 32, 'memory': 128, 'hourly': 1.548, 'monthly': 1041.84},
        'n2-standard-48': {'cpu': 48, 'memory': 192, 'hourly': 2.322, 'monthly': 1562.76},
        'n2-standard-64': {'cpu': 64, 'memory': 256, 'hourly': 3.096, 'monthly': 2083.68},
        'n2-standard-80': {'cpu': 80, 'memory': 320, 'hourly': 3.870, 'monthly': 2604.60},
        'n2-standard-96': {'cpu': 96, 'memory': 384, 'hourly': 4.644, 'monthly': 3125.52},
        'n2-standard-128': {'cpu': 128, 'memory': 512, 'hourly': 6.192, 'monthly': 4167.36},
    }
    
    # Spot pricing (approximately 70% discount)
    SPOT_DISCOUNT = 0.7
    
    def __init__(self, region: str = 'us-east4'):
        self.region = region
    
    def get_machine_pricing(self, machine_type: str, spot: bool = False) -> Dict:
        """Get pricing for a specific machine type"""
        if machine_type not in self.N2_PRICING:
            raise ValueError(f"Unknown machine type: {machine_type}")
        
        pricing = self.N2_PRICING[machine_type].copy()
        
        if spot:
            pricing['hourly'] *= self.SPOT_DISCOUNT
            pricing['monthly'] *= self.SPOT_DISCOUNT
        
        return pricing
    
    def calculate_custom_machine_pricing(self, cpu_cores: int, memory_gb: int, spot: bool = False) -> Dict:
        """Calculate pricing for custom machine type"""
        cpu_price_per_hour = 0.0485
        memory_price_per_gb_hour = 0.0065
        
        hourly_cost = (cpu_cores * cpu_price_per_hour) + (memory_gb * memory_price_per_gb_hour)
        monthly_cost = hourly_cost * 24 * 30.44
        
        if spot:
            hourly_cost *= self.SPOT_DISCOUNT
            monthly_cost *= self.SPOT_DISCOUNT
        
        return {
            'cpu': cpu_cores,
            'memory': memory_gb,
            'hourly': hourly_cost,
            'monthly': monthly_cost
        }


class DeploymentOptimizer:
    """Optimizes deployment configuration for cost and performance"""
    
    def __init__(self, pricing_provider: GCPPricingProvider):
        self.pricing_provider = pricing_provider
    
    def optimize_deployment(self, total_cpu: int, total_memory: int, 
                          max_vms: int = 10, prefer_spot: bool = False) -> DeploymentPlan:
        """Find the optimal deployment configuration"""
        
        optimization_notes = []
        
        # Strategy 1: Try to fit in standard machine types
        standard_configs = self._find_standard_configurations(total_cpu, total_memory, max_vms, prefer_spot)
        
        # Strategy 2: Use custom machine types for better resource utilization
        custom_configs = self._find_custom_configurations(total_cpu, total_memory, max_vms, prefer_spot)
        
        # Choose the most cost-effective option
        if standard_configs and custom_configs:
            if standard_configs['total_monthly_cost'] <= custom_configs['total_monthly_cost']:
                best_config = standard_configs
                optimization_notes.append("Using standard machine types for better reliability")
            else:
                best_config = custom_configs
                optimization_notes.append("Using custom machine types for better resource utilization")
        elif standard_configs:
            best_config = standard_configs
            optimization_notes.append("Using standard machine types")
        elif custom_configs:
            best_config = custom_configs
            optimization_notes.append("Using custom machine types")
        else:
            raise ValueError("Unable to find suitable configuration")
        
        if prefer_spot:
            optimization_notes.append("Using spot instances for cost savings (may be preempted)")
        
        # Calculate spot savings
        spot_savings = None
        if not prefer_spot:
            spot_config = self._find_standard_configurations(total_cpu, total_memory, max_vms, True)
            if spot_config:
                spot_savings = best_config['total_monthly_cost'] - spot_config['total_monthly_cost']
        
        return DeploymentPlan(
            total_cpu_cores=total_cpu,
            total_memory_gb=total_memory,
            vm_configurations=best_config['vm_configs'],
            total_hourly_cost=best_config['total_hourly_cost'],
            total_monthly_cost=best_config['total_monthly_cost'],
            region=self.pricing_provider.region,
            optimization_notes=optimization_notes,
            spot_savings=spot_savings
        )
    
    def _find_standard_configurations(self, total_cpu: int, total_memory: int, 
                                    max_vms: int, prefer_spot: bool) -> Optional[Dict]:
        """Find configurations using standard machine types"""
        best_config = None
        best_cost = float('inf')
        
        for num_vms in range(1, min(max_vms + 1, 6)):
            cpu_per_vm = total_cpu / num_vms
            memory_per_vm = total_memory / num_vms
            
            suitable_machine_type = self._find_suitable_standard_machine_type(cpu_per_vm, memory_per_vm)
            
            if suitable_machine_type:
                pricing = self.pricing_provider.get_machine_pricing(suitable_machine_type, prefer_spot)
                
                vm_config = VMConfiguration(
                    machine_type=suitable_machine_type,
                    cpu_cores=pricing['cpu'],
                    memory_gb=pricing['memory'],
                    count=num_vms,
                    hourly_cost=pricing['hourly'],
                    monthly_cost=pricing['monthly']
                )
                
                total_cost = pricing['monthly'] * num_vms
                
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_config = {
                        'vm_configs': [vm_config],
                        'total_hourly_cost': pricing['hourly'] * num_vms,
                        'total_monthly_cost': total_cost
                    }
        
        return best_config
    
    def _find_custom_configurations(self, total_cpu: int, total_memory: int, 
                                  max_vms: int, prefer_spot: bool) -> Optional[Dict]:
        """Find configurations using custom machine types"""
        best_config = None
        best_cost = float('inf')
        
        for num_vms in range(1, min(max_vms + 1, 6)):
            cpu_per_vm = total_cpu / num_vms
            memory_per_vm = total_memory / num_vms
            
            cpu_per_vm = int(cpu_per_vm) + (1 if cpu_per_vm % 1 > 0 else 0)
            memory_per_vm = int(memory_per_vm) + (1 if memory_per_vm % 1 > 0 else 0)
            
            cpu_per_vm = max(cpu_per_vm, 1)
            memory_per_vm = max(memory_per_vm, 1)
            
            pricing = self.pricing_provider.calculate_custom_machine_pricing(
                cpu_per_vm, memory_per_vm, prefer_spot
            )
            
            vm_config = VMConfiguration(
                machine_type=f"custom-{cpu_per_vm}-{memory_per_vm}",
                cpu_cores=cpu_per_vm,
                memory_gb=memory_per_vm,
                count=num_vms,
                hourly_cost=pricing['hourly'],
                monthly_cost=pricing['monthly'],
                is_custom=True
            )
            
            total_cost = pricing['monthly'] * num_vms
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_config = {
                    'vm_configs': [vm_config],
                    'total_hourly_cost': pricing['hourly'] * num_vms,
                    'total_monthly_cost': total_cost
                }
        
        return best_config
    
    def _find_suitable_standard_machine_type(self, cpu_per_vm: float, memory_per_vm: float) -> Optional[str]:
        """Find the smallest standard machine type that meets requirements"""
        suitable_types = []
        
        for machine_type, specs in self.pricing_provider.N2_PRICING.items():
            if specs['cpu'] >= cpu_per_vm and specs['memory'] >= memory_per_vm:
                suitable_types.append((machine_type, specs['cpu'] * specs['memory']))
        
        if suitable_types:
            suitable_types.sort(key=lambda x: x[1])
            return suitable_types[0][0]
        
        return None


# ADK Tools for Resource Optimization Agent
def analyze_topology_resources(topology_file: str) -> dict:
    """Analyze ContainerLab topology file and extract resource requirements.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        
    Returns:
        dict: Analysis results with nodes, resources, and component details
    """
    try:
        parser = ContainerLabResourceParser()
        nodes, topology_data = parser.parse_topology_file(topology_file)
        total_cpu, total_memory = parser.get_total_requirements(nodes)
        
        return {
            "status": "success",
            "topology_name": topology_data.get('name', 'unnamed'),
            "nodes": [
                {
                    "name": node.name,
                    "kind": node.kind,
                    "cpu_cores": node.estimated_cpu_cores,
                    "memory_gb": node.estimated_memory_gb,
                    "components": node.components,
                    "custom_resources": node.custom_resources
                }
                for node in nodes
            ],
            "total_cpu": total_cpu,
            "total_memory": total_memory,
            "node_count": len(nodes)
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def optimize_deployment_configuration(total_cpu: int, total_memory: int, region: str = 'us-east4',
                                    max_vms: int = 10, prefer_spot: bool = False) -> dict:
    """Optimize Google Cloud Engine deployment configuration.
    
    Args:
        total_cpu (int): Total CPU cores required
        total_memory (int): Total memory in GB required
        region (str): Google Cloud region
        max_vms (int): Maximum number of VMs to consider
        prefer_spot (bool): Whether to prefer spot instances
        
    Returns:
        dict: Deployment optimization results
    """
    try:
        pricing_provider = GCPPricingProvider(region)
        optimizer = DeploymentOptimizer(pricing_provider)
        plan = optimizer.optimize_deployment(total_cpu, total_memory, max_vms, prefer_spot)
        
        return {
            "status": "success",
            "deployment_plan": {
                "total_cpu_cores": plan.total_cpu_cores,
                "total_memory_gb": plan.total_memory_gb,
                "vm_configurations": [
                    {
                        "machine_type": vm.machine_type,
                        "cpu_cores": vm.cpu_cores,
                        "memory_gb": vm.memory_gb,
                        "count": vm.count,
                        "hourly_cost": vm.hourly_cost,
                        "monthly_cost": vm.monthly_cost,
                        "is_custom": vm.is_custom
                    }
                    for vm in plan.vm_configurations
                ],
                "total_hourly_cost": plan.total_hourly_cost,
                "total_monthly_cost": plan.total_monthly_cost,
                "region": plan.region,
                "optimization_notes": plan.optimization_notes,
                "spot_savings": plan.spot_savings
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def get_gcp_pricing_information(region: str = 'us-east4', machine_type: Optional[str] = None) -> dict:
    """Get Google Cloud Platform pricing information.
    
    Args:
        region (str): Google Cloud region
        machine_type (str): Optional specific machine type to get pricing for
        
    Returns:
        dict: Pricing information for the region
    """
    try:
        pricing_provider = GCPPricingProvider(region)
        
        if machine_type:
            pricing = pricing_provider.get_machine_pricing(machine_type)
            return {
                "status": "success",
                "machine_type": machine_type,
                "region": region,
                "pricing": pricing
            }
        else:
            return {
                "status": "success",
                "region": region,
                "available_machine_types": list(pricing_provider.N2_PRICING.keys()),
                "spot_discount": pricing_provider.SPOT_DISCOUNT
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


def compare_deployment_options(total_cpu: int, total_memory: int, region: str = 'us-east4') -> dict:
    """Compare different deployment options (on-demand vs spot, standard vs custom).
    
    Args:
        total_cpu (int): Total CPU cores required
        total_memory (int): Total memory in GB required
        region (str): Google Cloud region
        
    Returns:
        dict: Comparison of different deployment options
    """
    try:
        pricing_provider = GCPPricingProvider(region)
        optimizer = DeploymentOptimizer(pricing_provider)
        
        # Get on-demand standard configuration
        ondemand_standard = optimizer.optimize_deployment(total_cpu, total_memory, 10, False)
        
        # Get spot standard configuration
        spot_standard = optimizer.optimize_deployment(total_cpu, total_memory, 10, True)
        
        return {
            "status": "success",
            "comparison": {
                "on_demand_standard": {
                    "total_monthly_cost": ondemand_standard.total_monthly_cost,
                    "vm_configurations": [
                        {
                            "machine_type": vm.machine_type,
                            "count": vm.count,
                            "monthly_cost": vm.monthly_cost
                        }
                        for vm in ondemand_standard.vm_configurations
                    ]
                },
                "spot_standard": {
                    "total_monthly_cost": spot_standard.total_monthly_cost,
                    "vm_configurations": [
                        {
                            "machine_type": vm.machine_type,
                            "count": vm.count,
                            "monthly_cost": vm.monthly_cost
                        }
                        for vm in spot_standard.vm_configurations
                    ]
                },
                "spot_savings": ondemand_standard.total_monthly_cost - spot_standard.total_monthly_cost,
                "spot_savings_percentage": ((ondemand_standard.total_monthly_cost - spot_standard.total_monthly_cost) / ondemand_standard.total_monthly_cost) * 100
            },
            "region": region
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }


# ADK Agent for Resource Optimization
resource_optimization_agent = Agent(
    name="resource_optimization_agent",
    model="gemini-2.0-flash",
    description=(
        "Specialized agent for analyzing ContainerLab resource requirements and "
        "providing optimized Google Cloud Engine deployment recommendations. "
        "This agent focuses on resource calculation, cost optimization, and "
        "deployment configuration for GCP environments."
    ),
    instruction=(
        "You are a Google Cloud Engine deployment optimization specialist agent. Your expertise includes:\n\n"
        "1. **Resource Analysis**:\n"
        "   - Parse ContainerLab topology files\n"
        "   - Extract CPU and memory requirements\n"
        "   - Handle Nokia SROS lifecycle components (CPM, line cards, MDA)\n"
        "   - Support custom resource specifications\n"
        "   - Calculate total resource requirements\n\n"
        "2. **Deployment Optimization**:\n"
        "   - Find optimal VM configurations\n"
        "   - Compare standard vs custom machine types\n"
        "   - Optimize for cost and performance\n"
        "   - Support spot instance optimization\n"
        "   - Provide scaling recommendations\n\n"
        "3. **Cost Analysis**:\n"
        "   - Provide detailed pricing information\n"
        "   - Compare on-demand vs spot pricing\n"
        "   - Calculate monthly and hourly costs\n"
        "   - Show cost savings opportunities\n\n"
        "4. **GCP Integration**:\n"
        "   - Support N2 machine types\n"
        "   - Handle multiple GCP regions\n"
        "   - Provide ready-to-use deployment commands\n"
        "   - Include spot instance considerations\n\n"
        "When analyzing resources:\n"
        "- Always consider containerization overhead\n"
        "- Handle SROS components accurately\n"
        "- Support custom resource specifications\n"
        "- Provide detailed breakdowns\n\n"
        "When optimizing deployments:\n"
        "- Consider both cost and performance\n"
        "- Provide multiple options (standard/custom, on-demand/spot)\n"
        "- Include cost comparisons\n"
        "- Suggest optimal scaling strategies\n\n"
        "Always provide comprehensive analysis with clear cost breakdowns and optimization recommendations."
    ),
    tools=[analyze_topology_resources, optimize_deployment_configuration, get_gcp_pricing_information, compare_deployment_options],
)
