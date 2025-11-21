"""Pydantic schemas for state API."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class StateCreate(BaseModel):
    """Schema for creating a new state."""
    observation: list = Field(..., description="Environment observation")
    step_number: int = Field(..., description="Step number in the episode")
    action: Optional[Any] = Field(None, description="Action taken")
    reward: Optional[float] = Field(None, description="Reward received")
    done: bool = Field(False, description="Whether episode is done")
    truncated: bool = Field(False, description="Whether episode was truncated")
    parent_state_id: Optional[str] = Field(None, description="Parent state ID")
    info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional environment info")
    extra_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")


class StateResponse(BaseModel):
    """Schema for state API response."""
    id: str
    step_number: int
    observation: list
    action: Optional[Any] = None
    reward: Optional[float] = None
    done: bool
    truncated: bool
    parent_state_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
