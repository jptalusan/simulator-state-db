"""State model - represents a single state in the MDP (equivalent to a git commit).

States form a directed acyclic graph (DAG) where each state can have multiple 
children (branches). This allows for branching simulations at any point.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class State(Base):
    """
    A single state in the simulation - analogous to a git commit.
    
    Each state captures:
    - The environment's observation at that point
    - The action that was taken (if not root state)
    - The reward received
    - Whether this is a terminal state
    - Arbitrary metadata for analysis
    
    States form a tree structure through parent_state_id, enabling branching.
    """
    __tablename__ = 'states'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Tree structure - enables branching at any point
    parent_state_id = Column(String, ForeignKey('states.id'), nullable=True, index=True)
    
    # Core MDP data
    observation = Column(JSON, nullable=False)  # Environment observation/state
    action = Column(JSON, nullable=True)  # Action taken to reach this state (null for root)
    reward = Column(Float, nullable=True)  # Reward received from taking the action
    done = Column(Boolean, default=False, nullable=False)  # Terminal state flag
    truncated = Column(Boolean, default=False, nullable=False)  # Gym truncation flag
    
    # Sequencing within original trajectory
    step_number = Column(Integer, nullable=False, default=0, index=True)
    
    # Additional info from environment
    info = Column(JSON, nullable=True)  # Extra data from env.step()
    
    # Analysis metadata
    extra_metadata = Column(JSON, nullable=True)  # Custom metadata (e.g., Q-values, policy info)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    parent = relationship("State", remote_side=[id], backref="children", lazy="joined")
    
    # Many-to-many with SimulationRun through association table
    runs = relationship(
        "SimulationRun",
        secondary="run_state_sequence",
        back_populates="states",
        lazy="dynamic"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_parent_step', 'parent_state_id', 'step_number'),
        Index('ix_done_created', 'done', 'created_at'),
    )
    
    def __repr__(self):
        return f"<State(id={self.id[:8]}, step={self.step_number}, done={self.done})>"
    
    def get_lineage(self, session):
        """Return list of states from root to this state."""
        lineage = []
        current = self
        while current:
            lineage.insert(0, current)
            if current.parent_state_id:
                current = session.query(State).get(current.parent_state_id)
            else:
                break
        return lineage
    
    def get_depth(self):
        """Calculate depth in the tree (root = 0)."""
        depth = 0
        current = self
        while current.parent:
            depth += 1
            current = current.parent
        return depth
