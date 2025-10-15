#!/usr/bin/env python3
"""
Main root agent for the Multi-Agent ContainerLab to GCP System
Exposes the coordinator agent as the main root_agent for ADK
"""

# Import the coordinator agent as the main root agent
from .coordinator_agent import coordinator_agent

# Expose the coordinator agent as the root_agent for ADK
root_agent = coordinator_agent
