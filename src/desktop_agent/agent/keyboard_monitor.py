# -*- coding: utf-8 -*-
"""Keyboard monitor module."""

class KeyboardMonitor:
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        
    def start(self):
        print("Starting keyboard monitor...") 