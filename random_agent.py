"""
Random Agent for Zombie Game

Simple baseline that randomly selects legal actions
"""

import random
from typing import Optional
from Zombie_env import ZombieEnv, Action, Player


class RandomAgent:
    """Agent that randomly selects legal actions"""
    
    def __init__(self, player: Player):
        """
        Initialize Random Agent
        
        Args:
            player: The player this agent controls (RED or BLUE)
        """
        self.player = player
    
    def get_action(self, env: ZombieEnv) -> Optional[Action]:
        """
        Get random legal action
        
        Args:
            env: ZombieEnv instance
        
        Returns:
            Random legal action or None if no legal actions
        """
        legal_actions = env.get_legal_actions()
        
        if not legal_actions:
            return None
        
        # Select random action
        action = random.choice(legal_actions)
        
        return action
