#!/usr/bin/env python3
"""
Simplified test script for the Multi-Agent ContainerLab to GCP System
Tests the coordinated multi-agent system functionality without file dependencies
"""

import unittest
import os
import sys
import tempfile
import yaml

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the multi-agent system
from multi_agent_system.topology_repair_agent import (
    topology_repair_agent, validate_topology, repair_topology_file, analyze_topology_structure
)
from multi_agent_system.resource_optimization_agent import (
    resource_optimization_agent, analyze_topology_resources, optimize_deployment_configuration,
    get_gcp_pricing_information, compare_deployment_options
)
from multi_agent_system.coordinator_agent import (
    coordinator_agent, analyze_and_repair_topology, analyze_resources_and_optimize,
    complete_topology_analysis, get_deployment_recommendations, generate_deployment_commands
)


class TestMultiAgentSystem(unittest.TestCase):
    """Test suite for the Multi-Agent ContainerLab System"""

    def test_topology_repair_agent(self):
        """Test Topology Repair Agent functionality"""
        print("\n🧪 Testing Topology Repair Agent...")
        
        # Create a test topology file
        test_topology = {
            'name': 'test_topology',
            'topology': {
                'nodes': {
                    'router1': {
                        'kind': 'nokia_sros',
                        'image': 'ghcr.io/nokia/sros',
                        'sros': {
                            'cpm': {'count': 2},
                            'linecard': {'count': 4}
                        }
                    },
                    'server1': {
                        'kind': 'linux',
                        'image': 'ghcr.io/hellt/network-multitool',
                        'resources': {
                            'cpu': 2,
                            'memory': 4
                        }
                    }
                },
                'links': [
                    {
                        'endpoints': ['router1:eth1', 'server1:eth1']
                    }
                ]
            }
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.clab.yml', delete=False) as f:
            yaml.dump(test_topology, f, default_flow_style=False)
            temp_file = f.name
        
        try:
            # Test validation
            result = validate_topology(temp_file)
            self.assertEqual(result['status'], 'success')
            self.assertTrue(result['is_valid'])
            print("✅ Topology validation works correctly")
            
            # Test structure analysis
            result = analyze_topology_structure(temp_file)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['node_count'], 2)
            self.assertEqual(result['link_count'], 1)
            print("✅ Topology structure analysis works correctly")
            
        finally:
            os.unlink(temp_file)

    def test_resource_optimization_agent(self):
        """Test Resource Optimization Agent functionality"""
        print("\n🧪 Testing Resource Optimization Agent...")
        
        # Test deployment optimization
        result = optimize_deployment_configuration(16, 32, 'us-east4', 5, False)
        self.assertEqual(result['status'], 'success')
        self.assertIn('deployment_plan', result)
        self.assertGreater(result['deployment_plan']['total_monthly_cost'], 0)
        print(f"✅ Deployment optimization works correctly: ${result['deployment_plan']['total_monthly_cost']:.2f}/month")
        
        # Test pricing information
        result = get_gcp_pricing_information('us-east4')
        self.assertEqual(result['status'], 'success')
        self.assertIn('available_machine_types', result)
        print("✅ Pricing information works correctly")
        
        # Test cost comparison
        result = compare_deployment_options(16, 32, 'us-east4')
        self.assertEqual(result['status'], 'success')
        self.assertIn('comparison', result)
        self.assertGreater(result['comparison']['spot_savings'], 0)
        print(f"✅ Cost comparison works correctly: ${result['comparison']['spot_savings']:.2f} spot savings")

    def test_coordinator_agent(self):
        """Test Main Coordinator Agent functionality"""
        print("\n🧪 Testing Main Coordinator Agent...")
        
        # Create a test topology file
        test_topology = {
            'name': 'test_topology',
            'topology': {
                'nodes': {
                    'router1': {
                        'kind': 'nokia_sros',
                        'image': 'ghcr.io/nokia/sros',
                        'sros': {
                            'cpm': {'count': 2},
                            'linecard': {'count': 4}
                        }
                    },
                    'server1': {
                        'kind': 'linux',
                        'image': 'ghcr.io/hellt/network-multitool',
                        'resources': {
                            'cpu': 2,
                            'memory': 4
                        }
                    }
                }
            }
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.clab.yml', delete=False) as f:
            yaml.dump(test_topology, f, default_flow_style=False)
            temp_file = f.name
        
        try:
            # Test analyze resources and optimize
            result = analyze_resources_and_optimize(temp_file, 'us-east4', 5, False)
            self.assertEqual(result['status'], 'success')
            self.assertIn('resource_analysis', result)
            self.assertIn('deployment_optimization', result)
            print("✅ Analyze resources and optimize works correctly")
            
            # Test deployment recommendations
            result = get_deployment_recommendations(temp_file, 'us-east4', None, 'balanced')
            self.assertEqual(result['status'], 'success')
            self.assertIn('recommendations', result)
            self.assertIn('all_options', result['recommendations'])
            self.assertIn('recommended_option', result['recommendations'])
            print("✅ Deployment recommendations work correctly")
            
        finally:
            os.unlink(temp_file)

    def test_multi_agent_coordination(self):
        """Test multi-agent coordination"""
        print("\n🧪 Testing Multi-Agent Coordination...")
        
        # Create a test topology file
        test_topology = {
            'name': 'test_topology',
            'topology': {
                'nodes': {
                    'router1': {
                        'kind': 'nokia_sros',
                        'image': 'ghcr.io/nokia/sros',
                        'sros': {
                            'cpm': {'count': 2},
                            'linecard': {'count': 4}
                        }
                    },
                    'server1': {
                        'kind': 'linux',
                        'image': 'ghcr.io/hellt/network-multitool',
                        'resources': {
                            'cpu': 2,
                            'memory': 4
                        }
                    }
                }
            }
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.clab.yml', delete=False) as f:
            yaml.dump(test_topology, f, default_flow_style=False)
            temp_file = f.name
        
        try:
            # Test complete topology analysis
            result = complete_topology_analysis(temp_file, 'us-east4', True, 5, False)
            self.assertEqual(result['status'], 'success')
            self.assertIn('complete_analysis', result)
            self.assertIn('topology_repair', result['complete_analysis'])
            self.assertIn('resource_analysis', result['complete_analysis'])
            self.assertIn('deployment_optimization', result['complete_analysis'])
            print("✅ Complete topology analysis works correctly")
            
        finally:
            os.unlink(temp_file)

    def test_agent_specialization(self):
        """Test that each agent has specialized functionality"""
        print("\n🧪 Testing Agent Specialization...")
        
        # Test Topology Repair Agent specialization
        topology_tools = [tool.__name__ for tool in topology_repair_agent.tools]
        expected_topology_tools = ['validate_topology', 'repair_topology_file', 'analyze_topology_structure']
        for tool in expected_topology_tools:
            self.assertIn(tool, topology_tools)
        print("✅ Topology Repair Agent has specialized topology tools")
        
        # Test Resource Optimization Agent specialization
        resource_tools = [tool.__name__ for tool in resource_optimization_agent.tools]
        expected_resource_tools = ['analyze_topology_resources', 'optimize_deployment_configuration', 
                                 'get_gcp_pricing_information', 'compare_deployment_options']
        for tool in expected_resource_tools:
            self.assertIn(tool, resource_tools)
        print("✅ Resource Optimization Agent has specialized resource tools")
        
        # Test Coordinator Agent specialization
        coordinator_tools = [tool.__name__ for tool in coordinator_agent.tools]
        expected_coordinator_tools = ['analyze_and_repair_topology', 'analyze_resources_and_optimize',
                                     'complete_topology_analysis', 'get_deployment_recommendations',
                                     'generate_deployment_commands']
        for tool in expected_coordinator_tools:
            self.assertIn(tool, coordinator_tools)
        print("✅ Coordinator Agent has specialized coordination tools")

    def test_error_handling(self):
        """Test error handling across agents"""
        print("\n🧪 Testing Error Handling...")
        
        # Test with non-existent file
        result = validate_topology("non_existent_file.yml")
        self.assertEqual(result['status'], 'error')
        print("✅ Topology Repair Agent handles missing files correctly")
        
        result = analyze_topology_resources("non_existent_file.yml")
        self.assertEqual(result['status'], 'error')
        print("✅ Resource Optimization Agent handles missing files correctly")
        
        result = complete_topology_analysis("non_existent_file.yml")
        self.assertEqual(result['status'], 'error')
        print("✅ Coordinator Agent handles missing files correctly")

    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        print("\n🧪 Testing End-to-End Workflow...")
        
        # Create a test topology file
        test_topology = {
            'name': 'test_topology',
            'topology': {
                'nodes': {
                    'router1': {
                        'kind': 'nokia_sros',
                        'image': 'ghcr.io/nokia/sros',
                        'sros': {
                            'cpm': {'count': 2},
                            'linecard': {'count': 4}
                        }
                    },
                    'server1': {
                        'kind': 'linux',
                        'image': 'ghcr.io/hellt/network-multitool',
                        'resources': {
                            'cpu': 2,
                            'memory': 4
                        }
                    }
                }
            }
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.clab.yml', delete=False) as f:
            yaml.dump(test_topology, f, default_flow_style=False)
            temp_file = f.name
        
        try:
            # Step 1: Complete analysis
            result = complete_topology_analysis(temp_file, 'us-east4', True, 5, False)
            self.assertEqual(result['status'], 'success')
            
            # Step 2: Get recommendations
            recommendations = get_deployment_recommendations(temp_file, 'us-east4', None, 'balanced')
            self.assertEqual(recommendations['status'], 'success')
            
            # Step 3: Generate deployment commands
            commands = generate_deployment_commands(temp_file, 'us-east4', 'spot_standard')
            self.assertEqual(commands['status'], 'success')
            
            # Verify workflow completeness
            self.assertIn('complete_analysis', result)
            self.assertIn('recommendations', recommendations)
            self.assertIn('deployment_commands', commands)
            
            print("✅ End-to-end workflow works correctly")
            print("✅ Complete analysis → Recommendations → Deployment commands")
            
        finally:
            os.unlink(temp_file)

    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🚀 Starting Multi-Agent ContainerLab System Test Suite")
        print("=" * 70)
        
        test_methods = [
            self.test_topology_repair_agent,
            self.test_resource_optimization_agent,
            self.test_coordinator_agent,
            self.test_multi_agent_coordination,
            self.test_agent_specialization,
            self.test_error_handling,
            self.test_end_to_end_workflow,
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                test_method()
                passed_tests += 1
            except Exception as e:
                print(f"❌ {test_method.__name__} failed: {e}")
        
        print("\n" + "=" * 70)
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Multi-Agent ContainerLab System is working correctly.")
        else:
            print(f"⚠️ {total_tests - passed_tests} tests failed. Please check the implementation.")
        
        return passed_tests == total_tests


def main():
    """Main test runner"""
    test_suite = TestMultiAgentSystem()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n✅ Multi-Agent ContainerLab System is ready for deployment!")
        print("\nTo use the multi-agent system:")
        print("1. Set up your Google API key in multi_agent_system/.env")
        print("2. Run: adk web (for dev UI)")
        print("3. Select 'containerlab_gcp_coordinator' from the dropdown")
        print("4. Chat with the coordinator agent for complete analysis")
        print("\nAvailable agents:")
        print("- Topology Repair Agent: Validates and repairs topology files")
        print("- Resource Optimization Agent: Analyzes resources and optimizes deployments")
        print("- Coordinator Agent: Orchestrates the complete workflow")
    else:
        print("\n❌ Some tests failed. Please fix the issues before deployment.")
        sys.exit(1)


if __name__ == '__main__':
    main()
