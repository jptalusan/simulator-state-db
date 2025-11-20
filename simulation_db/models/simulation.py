"""Simulation model - represents a simulation configuration/template.

A Simulation defines the environment, agent, and hyperparameters.
Multiple SimulationRuns can reference the same Simulation configuration.
"""

from sqlalchemy import Column, String, DateTime, JSON, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class Simulation(Base):
    """
    Simulation configuration/template.
    
    This is analogous to a git repository configuration - it defines the 
    "project" but doesn't represent a specific execution. Multiple runs
    can share the same simulation configuration.
    """
    __tablename__ = 'simulations'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Identification
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Configuration
    environment_name = Column(String, nullable=False)  # e.g., "CartPole-v1"
    environment_config = Column(JSON, nullable=True)  # Env-specific params
    agent_type = Column(String, nullable=False)  # e.g., "DQN", "PPO", "Random"
    agent_config = Column(JSON, nullable=False)  # Agent hyperparameters
    
    # Additional parameters
    max_steps = Column(JSON, nullable=True)  # Max steps per episode/run
    seed = Column(JSON, nullable=True)  # Random seed for reproducibility
    tags = Column(JSON, nullable=True)  # Tags for organization/filtering
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    runs = relationship("SimulationRun", back_populates="simulation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_name_created', 'name', 'created_at'),
        Index('ix_env_agent', 'environment_name', 'agent_type'),
    )
    
    def __repr__(self):
        return f"<Simulation(id={self.id[:8]}, name='{self.name}', env='{self.environment_name}')>"
