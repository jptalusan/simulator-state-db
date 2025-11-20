# Quick Reference - Git-Tree Simulation DB

## Setup (One-time)

```bash
# Install
uv sync --dev

# Configure
cp .env.example .env
# Edit .env: Set DATABASE_URL

# Initialize
python scripts/init_db.py
```

## Core Operations

### Create Simulation

```python
from simulation_db.database import SessionLocal, init_db
from simulation_db.managers.simulation_manager import SimulationManager
from simulation_db.managers.state_manager import StateManager

session = SessionLocal()
sim_manager = SimulationManager(session)
state_manager = StateManager(session)

simulation = sim_manager.create_simulation(
    name="CartPole-DQN",
    environment_name="CartPole-v1",
    agent_type="DQN",
    agent_config={"learning_rate": 0.001, "epsilon": 1.0}
)
```

### Start Run

```python
# Create root state
root = state_manager.create_state(
    observation=[0.0, 0.0, 0.0, 0.0],
    step_number=0
)

# Create run
run = sim_manager.create_run(
    simulation_id=simulation.id,
    name="main",
    root_state=root
)
```

### Add States

```python
# In your training loop
for step in range(max_steps):
    action = agent.predict(obs)
    next_obs, reward, done, truncated, info = env.step(action)
    
    # Save state
    new_state = state_manager.create_state(
        observation=next_obs.tolist(),
        action=int(action),
        reward=float(reward),
        done=done,
        truncated=truncated,
        step_number=step + 1,
        parent_state_id=current_state.id,
        info=info,
        metadata={"epsilon": agent.epsilon}
    )
    
    # Add to run
    sim_manager.add_state_to_run(run, new_state)
    
    current_state = new_state
    obs = next_obs
    
    if done or truncated:
        break

# Complete run
sim_manager.complete_run(run, total_reward=cumulative_reward)
```

### Branch from State

```python
# Pause main run
sim_manager.pause_run(main_run)

# Get branch point (e.g., step 200)
branch_state = session.query(State).filter(
    State.id == main_run.current_state_id
).first()

# Create branch with modified config
branch_run = sim_manager.branch_from_state(
    parent_run=main_run,
    branch_point_state=branch_state,
    new_run_name="high-lr-experiment",
    config_overrides={"learning_rate": 0.01},
    description="Testing 10x higher learning rate"
)

# Continue from branch_state with new agent config
agent.learning_rate = 0.01
continue_training(env, agent, branch_run, start_state=branch_state)
```

### Query Operations

```python
# Get all states for a run (ordered)
states = run.get_state_sequence(session)

# Get state lineage (root to current)
lineage = state_manager.get_state_path(current_state)

# Get children of a state (branches)
children = state_manager.get_children(branch_point)

# Get run tree visualization
tree = sim_manager.get_run_tree(simulation.id)

# Get all terminal states
terminals = state_manager.get_terminal_states()
```

## Common Patterns

### Pattern 1: Hyperparameter Grid Search

```python
base_config = {"epsilon": 1.0, "gamma": 0.99}
learning_rates = [0.0001, 0.001, 0.01]

# Run to convergence with base LR
main_run = create_and_run(config={**base_config, "lr": 0.001})

# Get convergence state
conv_state = main_run.current_state

# Branch for each LR
for lr in learning_rates:
    branch = sim_manager.branch_from_state(
        parent_run=main_run,
        branch_point_state=conv_state,
        new_run_name=f"lr-{lr}",
        config_overrides={"learning_rate": lr}
    )
    continue_training(branch, start_state=conv_state)
```

### Pattern 2: A/B Testing Policies

```python
# Train to 10k steps
shared_run = train_until_step(10000)
checkpoint = shared_run.current_state

# Test different policies from same state
for policy in ["epsilon-greedy", "boltzmann", "ucb"]:
    branch = sim_manager.branch_from_state(
        parent_run=shared_run,
        branch_point_state=checkpoint,
        new_run_name=f"policy-{policy}",
        config_overrides={"exploration": policy}
    )
    evaluate(branch, checkpoint)
```

### Pattern 3: Intervention Testing

```python
# Run until failure
main_run = run_until_failure()
failure_state = main_run.current_state

# Test with intervention
intervention_run = sim_manager.branch_from_state(
    parent_run=main_run,
    branch_point_state=failure_state,
    new_run_name="with-intervention",
    config_overrides={"intervention": "manual_correction"}
)

# Apply fix and continue
apply_intervention(failure_state)
continue_training(intervention_run, failure_state)
```

## Database Queries

### Raw SQL Examples

```sql
-- Get all states for a run (ordered)
SELECT s.*
FROM states s
JOIN run_state_sequence rss ON s.id = rss.state_id
WHERE rss.run_id = 'run-id-here'
ORDER BY rss.sequence_order;

-- Find branch points
SELECT sr.name, s.step_number, sr.created_at
FROM simulation_runs sr
JOIN states s ON sr.branch_point_state_id = s.id
WHERE sr.simulation_id = 'sim-id-here';

-- Get children of a state
SELECT * FROM states WHERE parent_state_id = 'state-id-here';

-- Count states per run
SELECT sr.name, COUNT(*) as state_count
FROM simulation_runs sr
JOIN run_state_sequence rss ON sr.id = rss.run_id
GROUP BY sr.id, sr.name;
```

### SQLAlchemy Examples

```python
from sqlalchemy import select, func

# Get runs by status
active_runs = session.query(SimulationRun).filter(
    SimulationRun.status == 'active'
).all()

# Get states with reward > threshold
high_reward = session.query(State).filter(
    State.reward > 10.0
).all()

# Count states per simulation
stmt = (
    select(Simulation.name, func.count(State.id))
    .join(SimulationRun)
    .join(run_state_sequence)
    .join(State)
    .group_by(Simulation.id, Simulation.name)
)
results = session.execute(stmt).all()
```

## Debugging

### Check Database State

```python
# List all simulations
sims = session.query(Simulation).all()
for sim in sims:
    print(f"{sim.name}: {len(sim.runs)} runs")

# Check run status
runs = session.query(SimulationRun).all()
for run in runs:
    print(f"{run.name}: {run.status}, {run.total_steps} steps")

# Find orphaned states
orphans = session.query(State).filter(
    State.parent_state_id.isnot(None),
    ~State.parent_state_id.in_(session.query(State.id))
).all()
```

### Validate Tree Structure

```python
def validate_tree():
    """Check for cycles and orphans."""
    states = session.query(State).all()
    
    for state in states:
        # Check for cycles
        visited = set()
        current = state
        while current.parent_state_id:
            if current.id in visited:
                print(f"Cycle detected at {current.id}")
                break
            visited.add(current.id)
            current = current.parent
        
        # Check parent exists
        if state.parent_state_id:
            parent = session.query(State).get(state.parent_state_id)
            if not parent:
                print(f"Orphan state: {state.id}")
```

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/db_name

# Optional
POSTGRES_USER=simulation_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=simulation_db
POSTGRES_PORT=5432

# For SQLite testing
DATABASE_URL=sqlite:///./test.db
```

## Docker Commands

```bash
# Start database only
docker compose -f docker/docker-compose.yml up -d

# Build app image
docker build -t simulation-db -f docker/Dockerfile .

# Run app container
docker run --rm -p 8050:8050 --env-file .env simulation-db

# Stop all
docker compose -f docker/docker-compose.yml down
```

## Testing Commands

```bash
# Quick test with SQLite
python test_branching.py

# Run full test suite
pytest tests/

# Run specific example
python examples/cartpole_branching_example.py

# Initialize database
python scripts/init_db.py
```

## API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List simulations
curl http://localhost:8000/simulations

# Create simulation
curl -X POST http://localhost:8000/simulations \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "environment_name": "CartPole-v1", ...}'

# API docs
open http://localhost:8000/docs
```

## Tips & Tricks

1. **Always use transactions** for multi-step operations
2. **Commit after state creation** to get the ID
3. **Use sequence_order** when querying run states
4. **Index custom queries** if filtering on metadata
5. **Batch insert** for large simulations
6. **Use lazy loading** for relationships when possible
7. **Profile queries** with EXPLAIN ANALYZE
8. **Backup database** before pruning operations

## Common Errors

### "No module named 'simulation_db'"
```bash
# Solution: Add to PYTHONPATH
export PYTHONPATH=/path/to/state-db-boilerplate:$PYTHONPATH
```

### "DATABASE_URL not set"
```bash
# Solution: Set environment variable
export DATABASE_URL="postgresql://user:pass@localhost/db"
# Or create .env file
```

### "Table does not exist"
```bash
# Solution: Initialize database
python scripts/init_db.py
```

### Circular import error
```python
# Solution: Import models in __init__.py, not in database.py
```

## Performance Tuning

```python
# Use bulk operations
session.bulk_insert_mappings(State, state_dicts)

# Limit eager loading
session.query(State).options(lazyload('*')).all()

# Use pagination
states = session.query(State).limit(100).offset(page * 100).all()

# Add custom indexes
from sqlalchemy import Index
Index('ix_custom', State.reward, State.step_number)
```

## Resources

- Full docs: `docs/GIT_TREE_DESIGN.md`
- Visual guide: `docs/VISUAL_GUIDE.md`
- Examples: `examples/`
- SQLAlchemy: https://docs.sqlalchemy.org/
- Gymnasium: https://gymnasium.farama.org/
