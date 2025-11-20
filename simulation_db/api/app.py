"""FastAPI application for simulation-db API."""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from simulation_db.database import get_db
from simulation_db.models import Simulation
from simulation_db.managers.simulation_manager import SimulationManager

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
    from simulation_db.models import SimulationRun
    
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
    from simulation_db.models import SimulationRun, State, run_state_sequence
    from sqlalchemy import select
    
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
