"""State storage and retrieval helpers."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..models import State


class StateManager:
    """Manager for creating and querying states."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_state(
        self,
        observation: Any,
        step_number: int,
        parent_state_id: Optional[str] = None,
        action: Optional[Any] = None,
        reward: Optional[float] = None,
        done: bool = False,
        truncated: bool = False,
        info: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> State:
        """Create a new state in the tree."""
        state = State(
            parent_state_id=parent_state_id,
            observation=observation,
            action=action,
            reward=reward,
            done=done,
            truncated=truncated,
            step_number=step_number,
            info=info,
            extra_metadata=extra_metadata,
        )
        self.session.add(state)
        self.session.commit()
        self.session.refresh(state)
        return state
    
    def get_state(self, state_id: str) -> Optional[State]:
        """Retrieve a state by ID."""
        return self.session.query(State).filter(State.id == state_id).first()
    
    def get_state_path(self, state: State) -> list[State]:
        """Get the full path from root to this state."""
        return state.get_lineage(self.session)
    
    def get_children(self, state: State) -> list[State]:
        """Get all child states (branches from this state)."""
        return self.session.query(State).filter(State.parent_state_id == state.id).all()
    
    def get_terminal_states(self) -> list[State]:
        """Get all terminal states (done=True)."""
        return self.session.query(State).filter(State.done == True).all()
    
    def compare_runs(self, run1, run2) -> dict:
        """Compare two runs and return shared and divergent states.
        
        Returns a dict with:
        - shared: list of states common to both runs (up to branch point)
        - run1_only: list of states unique to run1 (after branch point)
        - run2_only: list of states unique to run2 (after branch point)
        - divergence_point: the state where they diverged (branch point)
        """
        from sqlalchemy import select
        from ..models import run_state_sequence
        
        # Get ordered states for each run
        stmt1 = (
            select(run_state_sequence.c.state_id)
            .where(run_state_sequence.c.run_id == run1.id)
            .order_by(run_state_sequence.c.sequence_order)
        )
        run1_state_ids = [row[0] for row in self.session.execute(stmt1).fetchall()]
        
        stmt2 = (
            select(run_state_sequence.c.state_id)
            .where(run_state_sequence.c.run_id == run2.id)
            .order_by(run_state_sequence.c.sequence_order)
        )
        run2_state_ids = [row[0] for row in self.session.execute(stmt2).fetchall()]
        
        # Find shared prefix
        shared_ids = []
        divergence_idx = 0
        for i, (s1, s2) in enumerate(zip(run1_state_ids, run2_state_ids)):
            if s1 == s2:
                shared_ids.append(s1)
                divergence_idx = i + 1
            else:
                break
        
        # Get the actual State objects
        shared_states = [self.get_state(sid) for sid in shared_ids]
        run1_only_states = [self.get_state(sid) for sid in run1_state_ids[divergence_idx:]]
        run2_only_states = [self.get_state(sid) for sid in run2_state_ids[divergence_idx:]]
        
        divergence_state = shared_states[-1] if shared_states else None
        
        return {
            'shared': shared_states,
            'run1_only': run1_only_states,
            'run2_only': run2_only_states,
            'divergence_point': divergence_state
        }
