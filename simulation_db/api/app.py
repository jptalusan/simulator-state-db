"""FastAPI application for simulation-db API."""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from simulation_db.database import get_db
from simulation_db.models import Simulation, SimulationRun, State, run_state_sequence
from simulation_db.managers.simulation_manager import SimulationManager
from simulation_db.managers.state_manager import StateManager
from simulation_db.schemas import (
    SimulationCreate,
    RunCreate,
    BranchCreate,
    StateCreate
)

app = FastAPI(
    title="simulation-db API",
    description="Git-like branching database for RL simulations",
    version="0.1.0"
)


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/simulations", tags=["simulations"])
def list_simulations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all simulation configurations.

    Args:
        skip (int): Number of records to skip. Defaults to 0.
        limit (int): Maximum number of records to return. Defaults to 100.
        db (Session): SQLAlchemy database session (injected via Depends).

    Returns:
        List[Dict[str, Any]]: A list of simulation dictionaries, each containing
        `id`, `name`, `description`, `environment_name`, `agent_type`,
        `created_at`, and `run_count`.
    """
    simulations = db.query(Simulation).offset(skip).limit(limit).all()
    return [
        {
            "id": sim.id,
            "name": sim.name,
            "description": sim.description,
            "environment_name": sim.environment_name,
            "agent_type": sim.agent_type,
            "created_at": sim.created_at.isoformat(),
            "run_count": len(sim.runs)
        }
        for sim in simulations
    ]


@app.get("/simulations/{simulation_id}/runs", tags=["simulations"])
def list_runs(simulation_id: str, db: Session = Depends(get_db)):
    """List all runs for a simulation."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return [
        {
            "id": run.id,
            "name": run.name,
            "status": run.status,
            "total_steps": run.total_steps,
            "total_reward": run.total_reward,
            "created_at": run.created_at.isoformat(),
            "parent_run_id": run.parent_run_id,
            "branch_point_state_id": run.branch_point_state_id
        }
        for run in simulation.runs
    ]


@app.get("/simulations/{simulation_id}/tree", tags=["simulations"])
def get_run_tree(simulation_id: str, db: Session = Depends(get_db)):
    """Get the tree structure of all runs for a simulation."""
    sim_manager = SimulationManager(db)
    tree = sim_manager.get_run_tree(simulation_id)
    return {"simulation_id": simulation_id, "tree": tree}


@app.get("/runs", tags=["runs"])
def list_all_runs(db: Session = Depends(get_db)):
    """
    List all simulation runs across all simulations.
    
    Returns:
        List[Dict[str, Any]]: A list of all simulation run IDs and metadata.
    """
    runs = db.query(SimulationRun).all()
    return [
        {
            "id": run.id,
            "name": run.name,
            "simulation_id": run.simulation_id,
            "status": run.status,
            "total_steps": run.total_steps,
            "total_reward": run.total_reward,
            "parent_run_id": run.parent_run_id,
            "branch_point_state_id": run.branch_point_state_id,
            "created_at": run.created_at.isoformat() if run.created_at else None
        }
        for run in runs
    ]


@app.get("/runs/{run_id}/states", tags=["runs"])
def get_run_states(run_id: str, db: Session = Depends(get_db)):
    """
    Get all states for a specific run in sequence order.
    
    Args:
        run_id (str): The ID of the simulation run.
        db (Session): SQLAlchemy database session (injected via Depends).
    
    Returns:
        Dict: Run metadata and list of states in order.
    """
    # Check if run exists
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get states in sequence order
    stmt = (
        select(State, run_state_sequence.c.sequence_order)
        .join(run_state_sequence, State.id == run_state_sequence.c.state_id)
        .where(run_state_sequence.c.run_id == run_id)
        .order_by(run_state_sequence.c.sequence_order)
    )
    
    results = db.execute(stmt).all()
    
    states = [
        {
            "id": state.id,
            "step_number": state.step_number,
            "sequence_order": seq_order,
            "observation": state.observation,
            "action": state.action,
            "reward": state.reward,
            "done": state.done,
            "truncated": state.truncated,
            "parent_state_id": state.parent_state_id,
            "created_at": state.created_at.isoformat() if state.created_at else None
        }
        for state, seq_order in results
    ]
    
    return {
        "run_id": run_id,
        "run_name": run.name,
        "total_states": len(states),
        "states": states
    }


# POST endpoints for creating resources

@app.post("/simulations", tags=["simulations"], status_code=201)
def create_simulation(payload: SimulationCreate, db: Session = Depends(get_db)):
    """
    Create a new simulation configuration.
    
    Args:
        payload (SimulationCreate): Simulation configuration data.
        db (Session): SQLAlchemy database session.
    
    Returns:
        Dict: Created simulation ID and metadata.
    """
    sim_manager = SimulationManager(db)
    
    try:
        simulation = sim_manager.create_simulation(
            name=payload.name,
            environment_name=payload.environment_name,
            agent_type=payload.agent_type,
            agent_config=payload.agent_config,
            description=payload.description,
            environment_config=payload.environment_config
        )
        
        return {
            "id": simulation.id,
            "name": simulation.name,
            "environment_name": simulation.environment_name,
            "agent_type": simulation.agent_type,
            "created_at": simulation.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create simulation: {str(e)}")


@app.post("/simulations/{simulation_id}/runs", tags=["simulations"], status_code=201)
def create_run(simulation_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    """
    Create a new run for a simulation.
    
    Args:
        simulation_id (str): ID of the simulation.
        payload (RunCreate): Run configuration data.
        db (Session): SQLAlchemy database session.
    
    Returns:
        Dict: Created run ID and metadata.
    """
    # Verify simulation exists
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Verify root state exists
    root_state = db.query(State).filter(State.id == payload.root_state_id).first()
    if not root_state:
        raise HTTPException(status_code=404, detail="Root state not found")
    
    sim_manager = SimulationManager(db)
    
    try:
        run = sim_manager.create_run(
            simulation_id=simulation_id,
            name=payload.name,
            root_state=root_state,
            description=payload.description,
            config_overrides=payload.config_overrides
        )
        
        return {
            "id": run.id,
            "name": run.name,
            "simulation_id": run.simulation_id,
            "root_state_id": run.root_state_id,
            "status": run.status,
            "created_at": run.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create run: {str(e)}")


@app.post("/states", tags=["states"], status_code=201)
def create_state(payload: StateCreate, db: Session = Depends(get_db)):
    """
    Create a new state.
    
    Args:
        payload (StateCreate): State data.
        db (Session): SQLAlchemy database session.
    
    Returns:
        Dict: Created state ID and metadata.
    """
    state_manager = StateManager(db)
    
    try:
        state = state_manager.create_state(
            observation=payload.observation,
            step_number=payload.step_number,
            action=payload.action,
            reward=payload.reward,
            done=payload.done,
            truncated=payload.truncated,
            parent_state_id=payload.parent_state_id,
            info=payload.info,
            extra_metadata=payload.extra_metadata
        )
        
        return {
            "id": state.id,
            "step_number": state.step_number,
            "observation": state.observation,
            "action": state.action,
            "reward": state.reward,
            "done": state.done,
            "truncated": state.truncated,
            "parent_state_id": state.parent_state_id,
            "info": state.info,
            "extra_metadata": state.extra_metadata,
            "created_at": state.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create state: {str(e)}")


@app.post("/runs/{run_id}/states", tags=["runs"], status_code=201)
def add_state_to_run(run_id: str, payload: StateCreate, db: Session = Depends(get_db)):
    """
    Create a new state and add it to a run's sequence.
    
    This is the most common operation - it creates a state and automatically
    adds it to the run_state_sequence table.
    
    Args:
        run_id (str): ID of the run.
        payload (StateCreate): State data.
        db (Session): SQLAlchemy database session.
    
    Returns:
        Dict: Created state ID and metadata.
    """
    # Verify run exists
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    state_manager = StateManager(db)
    sim_manager = SimulationManager(db)
    
    try:
        # Create the state
        state = state_manager.create_state(
            observation=payload.observation,
            step_number=payload.step_number,
            action=payload.action,
            reward=payload.reward,
            done=payload.done,
            truncated=payload.truncated,
            parent_state_id=payload.parent_state_id,
            info=payload.info,
            extra_metadata=payload.extra_metadata
        )
        
        # Add to run sequence
        sim_manager.add_state_to_run(run, state)
        
        return {
            "id": state.id,
            "step_number": state.step_number,
            "observation": state.observation,
            "action": state.action,
            "reward": state.reward,
            "done": state.done,
            "truncated": state.truncated,
            "parent_state_id": state.parent_state_id,
            "info": state.info,
            "extra_metadata": state.extra_metadata,
            "run_id": run_id,
            "created_at": state.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to add state to run: {str(e)}")


@app.get("/runs/{run1_id}/compare/{run2_id}", tags=["runs"])
def compare_runs(run1_id: str, run2_id: str, db: Session = Depends(get_db)):
    """
    Compare two runs to identify shared states and divergence points.
    
    Args:
        run1_id (str): ID of the first run.
        run2_id (str): ID of the second run.
        db (Session): SQLAlchemy database session.
    
    Returns:
        Dict: Comparison results with shared states, unique states, and divergence point.
    """
    # Verify both runs exist
    run1 = db.query(SimulationRun).filter(SimulationRun.id == run1_id).first()
    if not run1:
        raise HTTPException(status_code=404, detail="Run 1 not found")
    
    run2 = db.query(SimulationRun).filter(SimulationRun.id == run2_id).first()
    if not run2:
        raise HTTPException(status_code=404, detail="Run 2 not found")
    
    state_manager = StateManager(db)
    
    try:
        comparison = state_manager.compare_runs(run1, run2)
        
        def state_to_dict(state):
            return {
                "id": state.id,
                "step_number": state.step_number,
                "observation": state.observation,
                "action": state.action,
                "reward": state.reward,
                "done": state.done,
                "truncated": state.truncated,
            }
        
        return {
            "run1_id": run1_id,
            "run2_id": run2_id,
            "shared": [state_to_dict(s) for s in comparison['shared']],
            "run1_only": [state_to_dict(s) for s in comparison['run1_only']],
            "run2_only": [state_to_dict(s) for s in comparison['run2_only']],
            "divergence_point": state_to_dict(comparison['divergence_point']) if comparison['divergence_point'] else None,
            "shared_count": len(comparison['shared']),
            "run1_unique_count": len(comparison['run1_only']),
            "run2_unique_count": len(comparison['run2_only']),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to compare runs: {str(e)}")


@app.post("/runs/branch", tags=["runs"], status_code=201)
def create_branch(payload: BranchCreate, db: Session = Depends(get_db)):
    """
    Create a new branch from an existing run at a specific state.
    
    This creates a new run that shares history with the parent run up to
    the branch point, then can diverge with different configuration.
    
    Args:
        payload (BranchCreate): Branch configuration data.
        db (Session): SQLAlchemy database session.
    
    Returns:
        Dict: Created branch run ID and metadata.
    """
    # Verify parent run exists
    parent_run = db.query(SimulationRun).filter(SimulationRun.id == payload.parent_run_id).first()
    if not parent_run:
        raise HTTPException(status_code=404, detail="Parent run not found")
    
    # Verify branch point state exists
    branch_state = db.query(State).filter(State.id == payload.branch_point_state_id).first()
    if not branch_state:
        raise HTTPException(status_code=404, detail="Branch point state not found")
    
    sim_manager = SimulationManager(db)
    
    try:
        branch_run = sim_manager.branch_from_state(
            parent_run=parent_run,
            branch_point_state=branch_state,
            new_run_name=payload.new_run_name,
            config_overrides=payload.config_overrides,
            description=payload.description
        )
        
        return {
            "id": branch_run.id,
            "name": branch_run.name,
            "parent_run_id": branch_run.parent_run_id,
            "branch_point_state_id": branch_run.branch_point_state_id,
            "simulation_id": branch_run.simulation_id,
            "status": branch_run.status,
            "created_at": branch_run.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create branch: {str(e)}")
