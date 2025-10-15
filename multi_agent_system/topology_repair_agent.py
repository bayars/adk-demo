#!/usr/bin/env python3
"""
Topology Repair Agent - Specialized agent for fixing broken ContainerLab topologies
Part of the multi-agent system for ContainerLab to GCP deployment
"""

import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# Google ADK imports
from google.adk.agents import Agent


@dataclass
class TopologyValidationResult:
    """Represents topology validation and repair results"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    repairs: List[str] = field(default_factory=list)
    repaired_topology: Optional[Dict] = None


class TopologyValidator(ABC):
    """Abstract base class for topology validation"""
    
    @abstractmethod
    def validate(self, topology_data: Dict) -> TopologyValidationResult:
        """Validate topology data"""
        pass


class ContainerLabTopologyValidator(TopologyValidator):
    """Validates ContainerLab topology files"""
    
    def __init__(self):
        self.required_sections = ['topology']
        self.required_topology_sections = ['nodes']
        self.valid_node_kinds = {
            'nokia_srlinux', 'nokia_sros', 'linux', 'cisco_iosxe', 
            'cisco_iosxr', 'juniper_vmx', 'arista_ceos', 'sonic', 
            'frr', 'quagga', 'ovs', 'bridge'
        }
    
    def validate(self, topology_data: Dict) -> TopologyValidationResult:
        """Validate ContainerLab topology data"""
        result = TopologyValidationResult(is_valid=True)
        
        # Check required sections
        if 'topology' not in topology_data:
            result.errors.append("Missing required 'topology' section")
            result.is_valid = False
        
        if not result.is_valid:
            return result
        
        topology = topology_data['topology']
        
        # Check topology sections
        if 'nodes' not in topology:
            result.errors.append("Missing required 'nodes' section in topology")
            result.is_valid = False
        
        if 'links' not in topology:
            result.warnings.append("Missing 'links' section - topology may be incomplete")
        
        # Validate nodes
        if 'nodes' in topology:
            node_validation = self._validate_nodes(topology['nodes'])
            result.errors.extend(node_validation['errors'])
            result.warnings.extend(node_validation['warnings'])
        
        # Validate links
        if 'links' in topology:
            link_validation = self._validate_links(topology['links'], topology.get('nodes', {}))
            result.errors.extend(link_validation['errors'])
            result.warnings.extend(link_validation['warnings'])
        
        return result
    
    def _validate_nodes(self, nodes: Dict) -> Dict[str, List[str]]:
        """Validate node definitions"""
        errors = []
        warnings = []
        
        for node_name, node_config in nodes.items():
            # Check required fields
            if 'kind' not in node_config:
                errors.append(f"Node '{node_name}' missing required 'kind' field")
                continue
            
            # Validate node kind
            if node_config['kind'] not in self.valid_node_kinds:
                warnings.append(f"Node '{node_name}' has unknown kind '{node_config['kind']}'")
            
            # Check for common issues
            if 'image' not in node_config:
                warnings.append(f"Node '{node_name}' missing 'image' field")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_links(self, links: List, nodes: Dict) -> Dict[str, List[str]]:
        """Validate link definitions"""
        errors = []
        warnings = []
        
        for i, link in enumerate(links):
            if 'endpoints' not in link:
                errors.append(f"Link {i} missing 'endpoints' field")
                continue
            
            endpoints = link['endpoints']
            if len(endpoints) != 2:
                errors.append(f"Link {i} must have exactly 2 endpoints")
                continue
            
            # Validate endpoint format
            for endpoint in endpoints:
                if ':' not in endpoint:
                    errors.append(f"Link {i} endpoint '{endpoint}' must be in format 'node:interface'")
                    continue
                
                node_name, interface = endpoint.split(':', 1)
                if node_name not in nodes:
                    errors.append(f"Link {i} references unknown node '{node_name}'")
        
        return {'errors': errors, 'warnings': warnings}


class TopologyRepairer:
    """Repairs broken topology files"""
    
    def __init__(self, validator: TopologyValidator):
        self.validator = validator
        self.default_images = {
            'nokia_srlinux': 'ghcr.io/nokia/srlinux',
            'nokia_sros': 'ghcr.io/nokia/sros',
            'linux': 'ghcr.io/hellt/network-multitool',
            'cisco_iosxe': 'ghcr.io/cisco/iosxe',
            'cisco_iosxr': 'ghcr.io/cisco/iosxr',
            'juniper_vmx': 'ghcr.io/juniper/vmx',
            'arista_ceos': 'ghcr.io/arista/ceos',
            'sonic': 'ghcr.io/opennetworking/sonic',
            'frr': 'ghcr.io/hellt/frr',
            'quagga': 'ghcr.io/hellt/quagga',
        }
    
    def repair_topology(self, topology_data: Dict) -> TopologyValidationResult:
        """Repair broken topology data"""
        result = self.validator.validate(topology_data)
        repairs = []
        
        if not result.is_valid:
            repaired_data = topology_data.copy()
            
            # Repair missing topology section
            if 'topology' not in repaired_data:
                repaired_data['topology'] = {'nodes': {}, 'links': []}
                repairs.append("Added missing 'topology' section")
            
            topology = repaired_data['topology']
            
            # Repair missing nodes section
            if 'nodes' not in topology:
                topology['nodes'] = {}
                repairs.append("Added missing 'nodes' section")
            
            # Repair missing links section
            if 'links' not in topology:
                topology['links'] = []
                repairs.append("Added missing 'links' section")
            
            # Repair nodes
            node_repairs = self._repair_nodes(topology['nodes'])
            repairs.extend(node_repairs)
            
            # Repair links
            link_repairs = self._repair_links(topology['links'], topology['nodes'])
            repairs.extend(link_repairs)
            
            result.repairs = repairs
            result.repaired_topology = repaired_data
            
            # Re-validate after repair
            result = self.validator.validate(repaired_data)
            result.repairs = repairs
            result.repaired_topology = repaired_data
        
        return result
    
    def _repair_nodes(self, nodes: Dict) -> List[str]:
        """Repair node definitions"""
        repairs = []
        
        for node_name, node_config in nodes.items():
            # Add missing kind
            if 'kind' not in node_config:
                node_config['kind'] = 'linux'  # Default to linux
                repairs.append(f"Added missing 'kind' field to node '{node_name}'")
            
            # Add missing image
            if 'image' not in node_config and node_config['kind'] in self.default_images:
                node_config['image'] = self.default_images[node_config['kind']]
                repairs.append(f"Added missing 'image' field to node '{node_name}'")
            
            # Add missing type
            if 'type' not in node_config:
                node_config['type'] = 'default'
                repairs.append(f"Added missing 'type' field to node '{node_name}'")
        
        return repairs
    
    def _repair_links(self, links: List, nodes: Dict) -> List[str]:
        """Repair link definitions"""
        repairs = []
        
        for i, link in enumerate(links):
            # Add missing endpoints
            if 'endpoints' not in link:
                link['endpoints'] = []
                repairs.append(f"Added missing 'endpoints' field to link {i}")
            
            # Validate and repair endpoints
            endpoints = link['endpoints']
            if len(endpoints) < 2:
                # Try to create valid endpoints
                if len(endpoints) == 1:
                    # Find a suitable second endpoint
                    endpoint = endpoints[0]
                    if ':' in endpoint:
                        node_name, interface = endpoint.split(':', 1)
                        if node_name in nodes:
                            # Find another node to connect to
                            for other_node in nodes:
                                if other_node != node_name:
                                    endpoints.append(f"{other_node}:eth1")
                                    repairs.append(f"Added second endpoint to link {i}")
                                    break
                elif len(endpoints) == 0:
                    # Create a basic link between first two nodes
                    node_names = list(nodes.keys())
                    if len(node_names) >= 2:
                        endpoints.extend([f"{node_names[0]}:eth1", f"{node_names[1]}:eth1"])
                        repairs.append(f"Created basic link {i} between first two nodes")
        
        return repairs


# ADK Tools for Topology Repair Agent
def validate_topology(topology_file: str) -> dict:
    """Validate ContainerLab topology file.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        
    Returns:
        dict: Validation results with errors, warnings, and status
    """
    try:
        with open(topology_file, 'r') as file:
            topology_data = yaml.safe_load(file)
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to parse topology file: {e}"
        }
    
    validator = ContainerLabTopologyValidator()
    result = validator.validate(topology_data)
    
    return {
        "status": "success",
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "file_path": topology_file
    }


def repair_topology_file(topology_file: str, output_file: Optional[str] = None) -> dict:
    """Repair broken ContainerLab topology file.
    
    Args:
        topology_file (str): Path to the broken topology file
        output_file (str): Optional output file for repaired topology
        
    Returns:
        dict: Repair results with details of fixes applied
    """
    try:
        with open(topology_file, 'r') as file:
            topology_data = yaml.safe_load(file)
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to parse topology file: {e}"
        }
    
    validator = ContainerLabTopologyValidator()
    repairer = TopologyRepairer(validator)
    result = repairer.repair_topology(topology_data)
    
    if result.repaired_topology and output_file:
        with open(output_file, 'w') as f:
            yaml.dump(result.repaired_topology, f, default_flow_style=False)
    
    return {
        "status": "success",
        "is_valid": result.is_valid,
        "repairs": result.repairs,
        "errors": result.errors,
        "warnings": result.warnings,
        "output_file": output_file,
        "repair_count": len(result.repairs)
    }


def analyze_topology_structure(topology_file: str) -> dict:
    """Analyze ContainerLab topology structure and identify issues.
    
    Args:
        topology_file (str): Path to the ContainerLab topology file
        
    Returns:
        dict: Detailed analysis of topology structure
    """
    try:
        with open(topology_file, 'r') as file:
            topology_data = yaml.safe_load(file)
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to parse topology file: {e}"
        }
    
    validator = ContainerLabTopologyValidator()
    result = validator.validate(topology_data)
    
    # Count nodes and links
    node_count = 0
    link_count = 0
    node_kinds = {}
    
    if 'topology' in topology_data:
        topology = topology_data['topology']
        if 'nodes' in topology:
            node_count = len(topology['nodes'])
            for node_name, node_config in topology['nodes'].items():
                kind = node_config.get('kind', 'unknown')
                node_kinds[kind] = node_kinds.get(kind, 0) + 1
        
        if 'links' in topology:
            link_count = len(topology['links'])
    
    return {
        "status": "success",
        "topology_name": topology_data.get('name', 'unnamed'),
        "node_count": node_count,
        "link_count": link_count,
        "node_kinds": node_kinds,
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "file_path": topology_file
    }


# ADK Agent for Topology Repair
topology_repair_agent = Agent(
    name="topology_repair_agent",
    model="gemini-2.0-flash",
    description=(
        "Specialized agent for validating and repairing ContainerLab topology files. "
        "This agent focuses exclusively on topology structure validation, error detection, "
        "and automatic repair of broken or incomplete ContainerLab configurations."
    ),
    instruction=(
        "You are a ContainerLab topology repair specialist agent. Your expertise includes:\n\n"
        "1. **Topology Validation**:\n"
        "   - Validate ContainerLab YAML structure\n"
        "   - Check for missing required sections (topology, nodes, links)\n"
        "   - Verify node configurations and link definitions\n"
        "   - Identify common configuration errors\n\n"
        "2. **Automatic Repair**:\n"
        "   - Fix missing topology sections\n"
        "   - Add missing node fields (kind, image, type)\n"
        "   - Repair broken link definitions\n"
        "   - Apply default configurations where appropriate\n\n"
        "3. **Structure Analysis**:\n"
        "   - Analyze topology structure and components\n"
        "   - Count nodes and links\n"
        "   - Identify node types and distributions\n"
        "   - Provide detailed structure reports\n\n"
        "When repairing topologies:\n"
        "- Always preserve existing valid configurations\n"
        "- Apply minimal necessary changes\n"
        "- Provide clear explanations of repairs made\n"
        "- Validate the repaired topology\n\n"
        "When analyzing structures:\n"
        "- Provide comprehensive analysis\n"
        "- Identify potential issues\n"
        "- Suggest improvements\n"
        "- Count and categorize components\n\n"
        "Always provide detailed feedback about what was found, what was repaired, "
        "and the current state of the topology."
    ),
    tools=[validate_topology, repair_topology_file, analyze_topology_structure],
)
