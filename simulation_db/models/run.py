"""SimulationRun model - represents an actual execution (equivalent to a git branch).

A SimulationRun tracks a specific path through the state tree, and can branch
from any existing state in the tree.
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    JSON, Text, Index, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from simulation_db.models import State, Base


# Association table for many-to-many between SimulationRun and State
# This tracks which states belong to which run in sequence order
run_state_sequence = Table(
    'run_state_sequence',
    Base.metadata,
    Column('id', String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column('run_id', String, ForeignKey('simulation_runs.id', ondelete='CASCADE'), nullable=False),
    Column('state_id', String, ForeignKey('states.id', ondelete='CASCADE'), nullable=False),
    Column('sequence_order', Integer, nullable=False),  # Order within this run
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
    Index('ix_run_sequence', 'run_id', 'sequence_order'),
    Index('ix_state_run', 'state_id', 'run_id'),
)


class SimulationRun(Base):
    """
    An actual execution of a simulation - analogous to a git branch.
    
    A run represents a path through the state DAG. It can:
    - Start from scratch (root_state_id = first state created)
    - Branch from an existing state (branch_point_state_id set)
    - Track its current position (current_state_id)
    - Have its own modified configuration (config_overrides)
    """
    __tablename__ = 'simulation_runs'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Links to Simulation configuration
    simulation_id = Column(String, ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Branch identification
    name = Column(String, nullable=False, index=True)  # e.g., "main", "lr-0.01-experiment"
    description = Column(Text, nullable=True)
    
    # State references
    root_state_id = Column(String, ForeignKey('states.id'), nullable=False)  # First state in this run
    current_state_id = Column(String, ForeignKey('states.id'), nullable=True)  # Latest state
    
    # Branching metadata
    parent_run_id = Column(String, ForeignKey('simulation_runs.id'), nullable=True, index=True)
    branch_point_state_id = Column(String, ForeignKey('states.id'), nullable=True)  # State where branch occurred
    
    # Configuration overrides for this run (e.g., different learning rate)
    config_overrides = Column(JSON, nullable=True)
    
    # Run status
    status = Column(String, default='active', nullable=False, index=True)  # active, paused, completed, failed
    
    # Statistics
    total_steps = Column(Integer, default=0, nullable=False)
    total_reward = Column(JSON, nullable=True)  # Can be scalar or complex
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)  # Additional run-specific data
    
    # Relationships
    simulation = relationship("Simulation", back_populates="runs")
    root_state = relationship("State", foreign_keys=[root_state_id])
    current_state = relationship("State", foreign_keys=[current_state_id])
    branch_point = relationship("State", foreign_keys=[branch_point_state_id])
    
    parent_run = relationship(
        "SimulationRun",
        remote_side=[id],
        backref="child_runs",
        foreign_keys=[parent_run_id]
    )
    
    # States in this run (ordered by sequence)
    states = relationship(
        "State",
        secondary=run_state_sequence,
        back_populates="runs",
        lazy="dynamic",
        order_by="run_state_sequence.c.sequence_order"
    )
    
    __table_args__ = (
        Index('ix_sim_status', 'simulation_id', 'status'),
        Index('ix_parent_branch', 'parent_run_id', 'branch_point_state_id'),
    )
    
    def __repr__(self):
        return f"<SimulationRun(id={self.id[:8]}, name='{self.name}', status='{self.status}')>"
    
    def get_state_sequence(self, session):
        """Return ordered list of states for this run."""
        stmt = (
            select(State, run_state_sequence.c.sequence_order)
            .join(run_state_sequence, State.id == run_state_sequence.c.state_id)
            .where(run_state_sequence.c.run_id == self.id)
            .order_by(run_state_sequence.c.sequence_order)
        )
        return [row[0] for row in session.execute(stmt)]
