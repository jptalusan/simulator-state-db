"""Pydantic schemas for simulation API."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SimulationCreate(BaseModel):
    """Schema for creating a new simulation."""
    name: str = Field(..., description="Name of the simulation")
    environment_name: str = Field(..., description="Gym environment name")
    agent_type: str = Field(..., description="Type of agent (e.g., DQN, PPO)")
    agent_config: Dict[str, Any] = Field(..., description="Agent hyperparameters")
    description: Optional[str] = Field(None, description="Optional description")
    environment_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Environment configuration")


class SimulationResponse(BaseModel):
    """Schema for simulation API response."""
    id: str
    name: str
    description: Optional[str]
    environment_name: str
    agent_type: str
    created_at: datetime
    run_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class RunCreate(BaseModel):
    """Schema for creating a new run."""
    name: str = Field(..., description="Name of the run")
    root_state_id: str = Field(..., description="ID of the root state")
    description: Optional[str] = Field(None, description="Optional description")
    config_overrides: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuration overrides")


class RunResponse(BaseModel):
    """Schema for run API response."""
    id: str
    name: str
    simulation_id: str
    status: str
    total_steps: int
    total_reward: Optional[float] = None
    created_at: datetime
    parent_run_id: Optional[str] = None
    branch_point_state_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class BranchCreate(BaseModel):
    """Schema for creating a branch."""
    parent_run_id: str = Field(..., description="ID of the parent run to branch from")
    branch_point_state_id: str = Field(..., description="State ID where branch occurs")
    new_run_name: str = Field(..., description="Name for the new branch")
    config_overrides: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuration changes")
    description: Optional[str] = Field(None, description="Optional description")
