"""Pydantic schemas for simulation API responses."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SimulationBase(BaseModel):
    """Base schema for simulation."""
    name: str
    description: Optional[str] = None
    environment_name: str
    agent_type: str
    agent_config: dict


class SimulationCreate(SimulationBase):
    """Schema for creating a new simulation."""
    environment_config: Optional[dict] = None
    max_steps: Optional[dict] = None
    seed: Optional[dict] = None
    tags: Optional[dict] = None


class SimulationResponse(SimulationBase):
    """Schema for simulation API response."""
    id: str
    created_at: datetime
    run_count: int
    
    model_config = ConfigDict(from_attributes=True)


class RunResponse(BaseModel):
    """Schema for run API response."""
    id: str
    name: str
    status: str
    total_steps: int
    total_reward: Optional[float] = None
    created_at: datetime
    parent_run_id: Optional[str] = None
    branch_point_state_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
