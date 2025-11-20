"""High-level simulation management API (create runs, list runs, branch, etc.)."""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

from ..models import Simulation, SimulationRun, State, run_state_sequence


class SimulationManager:
    """Manager for creating and managing simulations and their runs."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_simulation(
        self,
        name: str,
        environment_name: str,
        agent_type: str,
        agent_config: Dict[str, Any],
        description: Optional[str] = None,
        environment_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Simulation:
        """Create a new simulation configuration."""
        sim = Simulation(
            name=name,
            description=description,
            environment_name=environment_name,
            environment_config=environment_config or {},
            agent_type=agent_type,
            agent_config=agent_config,
            **kwargs
        )
        self.session.add(sim)
        self.session.commit()
        self.session.refresh(sim)
        return sim
    
    def create_run(
        self,
        simulation_id: str,
        name: str,
        root_state: State,
        description: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None,
        branch_point_state_id: Optional[str] = None,
    ) -> SimulationRun:
        """Create a new simulation run."""
        run = SimulationRun(
            simulation_id=simulation_id,
            name=name,
            description=description,
            root_state_id=root_state.id,
            current_state_id=root_state.id,
            config_overrides=config_overrides or {},
            parent_run_id=parent_run_id,
            branch_point_state_id=branch_point_state_id,
            status='active',
            started_at=datetime.utcnow()
        )
        self.session.add(run)
        self.session.flush()
        
        # Add root state to the run sequence
        self._add_state_to_run(run.id, root_state.id, sequence_order=0)
        
        self.session.commit()
        self.session.refresh(run)
        return run
    
    def branch_from_state(
        self,
        parent_run: SimulationRun,
        branch_point_state: State,
        new_run_name: str,
        config_overrides: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> SimulationRun:
        """Create a new run that branches from an existing state.
        
        This is the key operation for git-like branching. The new run
        will start from the branch_point_state and can have different
        configuration (e.g., learning rate).
        """
        # Merge parent config with new overrides
        merged_config = {**(parent_run.config_overrides or {}), **(config_overrides or {})}
        
        # Create the branched run
        new_run = SimulationRun(
            simulation_id=parent_run.simulation_id,
            name=new_run_name,
            description=description or f"Branched from {parent_run.name} at step {branch_point_state.step_number}",
            root_state_id=branch_point_state.id,
            current_state_id=branch_point_state.id,
            config_overrides=merged_config,
            parent_run_id=parent_run.id,
            branch_point_state_id=branch_point_state.id,
            status='active',
            started_at=datetime.utcnow()
        )
        self.session.add(new_run)
        self.session.flush()
        
        # Copy all states from parent run up to branch point
        parent_sequence = self._get_run_states_until(parent_run.id, branch_point_state.id)
        for idx, state_id in enumerate(parent_sequence):
            self._add_state_to_run(new_run.id, state_id, sequence_order=idx)
        
        self.session.commit()
        self.session.refresh(new_run)
        return new_run
    
    def add_state_to_run(
        self,
        run: SimulationRun,
        state: State
    ):
        """Add a new state to a run's sequence."""
        # Get current max sequence order for this run
        from sqlalchemy import select, func
        stmt = (
            select(func.coalesce(func.max(run_state_sequence.c.sequence_order), -1))
            .where(run_state_sequence.c.run_id == run.id)
        )
        max_order = self.session.execute(stmt).scalar()
        
        self._add_state_to_run(run.id, state.id, sequence_order=max_order + 1)
        
        # Update run metadata
        run.current_state_id = state.id
        run.total_steps += 1
        
        self.session.commit()
    
    def _add_state_to_run(self, run_id: str, state_id: str, sequence_order: int):
        """Internal method to add state to run sequence."""
        from sqlalchemy import insert
        stmt = insert(run_state_sequence).values(
            run_id=run_id,
            state_id=state_id,
            sequence_order=sequence_order
        )
        self.session.execute(stmt)
    
    def _get_run_states_until(self, run_id: str, until_state_id: str) -> List[str]:
        """Get ordered list of state IDs from a run up to (and including) a specific state."""
        from sqlalchemy import select
        stmt = (
            select(run_state_sequence.c.state_id, run_state_sequence.c.sequence_order)
            .where(run_state_sequence.c.run_id == run_id)
            .order_by(run_state_sequence.c.sequence_order)
        )
        results = self.session.execute(stmt).fetchall()
        
        state_ids = []
        for state_id, _ in results:
            state_ids.append(state_id)
            if state_id == until_state_id:
                break
        
        return state_ids
    
    def complete_run(self, run: SimulationRun, total_reward: Optional[float] = None):
        """Mark a run as completed."""
        run.status = 'completed'
        run.completed_at = datetime.utcnow()
        if total_reward is not None:
            run.total_reward = total_reward
        self.session.commit()
    
    def pause_run(self, run: SimulationRun):
        """Pause a run (allows for later resumption or branching)."""
        run.status = 'paused'
        self.session.commit()
    
    def get_run_tree(self, simulation_id: str) -> List[Dict[str, Any]]:
        """Get tree structure of all runs for a simulation."""
        runs = self.session.query(SimulationRun).filter(
            SimulationRun.simulation_id == simulation_id
        ).all()
        
        # Build tree structure
        tree = []
        run_map = {r.id: r for r in runs}
        
        for run in runs:
            if run.parent_run_id is None:
                tree.append(self._build_run_subtree(run, run_map))
        
        return tree
    
    def _build_run_subtree(self, run: SimulationRun, run_map: Dict[str, SimulationRun]) -> Dict[str, Any]:
        """Recursively build run tree."""
        children = [
            self._build_run_subtree(run_map[child.id], run_map)
            for child in run.child_runs
        ]
        
        return {
            'id': run.id,
            'name': run.name,
            'status': run.status,
            'total_steps': run.total_steps,
            'branch_point': run.branch_point_state_id,
            'children': children
        }
