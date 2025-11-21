# Git-Tree Simulation Database - Design Documentation

## Overview

This database structure implements a git-like branching system for reinforcement learning simulations. The key insight is treating simulations as branches and states as commits, allowing you to:

1. **Run a simulation** and save every state
2. **Branch from any state** to explore alternative trajectories  
3. **Compare outcomes** across different configurations
4. **Navigate the state tree** to analyze decision paths

## Key Concepts

### The Git Analogy

| Git Concept | Simulation DB | Purpose |
|------------|---------------|---------|
| Repository | `Simulation` | Configuration/template for experiments |
| Branch | `SimulationRun` | Actual execution path through states |
| Commit | `State` | Single MDP state with observation/action/reward |
| Branching | `branch_from_state()` | Create new run from existing state |
| Tree | State DAG | Complete history with all branches |

## Database Schema

### Summary
```
Simulation (PK: id)
    ↓ 1:many
SimulationRun (PK: id)
    ├── FK: simulation_id → Simulation.id
    ├── FK: parent_run_id → SimulationRun.id (self-referential for branching)
    ├── FK: root_state_id → State.id (where this run starts)
    ├── FK: current_state_id → State.id (latest state)
    └── FK: branch_point_state_id → State.id (where branch occurred)
    
State (PK: id)
    ├── FK: parent_state_id → State.id (self-referential for state tree)
    └── many:many with SimulationRun through run_state_sequence
    
run_state_sequence (association table)
    ├── FK: run_id → SimulationRun.id
    ├── FK: state_id → State.id
    └── sequence_order (ordering within run)
```

### 1. State Table (The Core)

```python
class State(Base):
    """A single state in the MDP - analogous to a git commit."""
    
    id = String (UUID)
    parent_state_id = String (FK -> states.id)  # Tree structure
    
    # MDP data
    observation = JSON      # Environment observation
    action = JSON          # Action taken to reach this state
    reward = Float         # Reward received
    done = Boolean         # Terminal state flag
    truncated = Boolean    # Gym truncation flag
    step_number = Integer  # Position in original sequence
    
    # Metadata
    info = JSON           # Extra data from env.step()
    metadata = JSON       # Custom analysis data (Q-values, etc.)
    created_at = DateTime
```

**Key Features:**
- **Tree structure** via `parent_state_id` enables branching
- Each state is immutable (like git commits)
- States can have multiple children (branches diverge)
- Full MDP tuple: (observation, action, reward, done)

**Improvements from original design:**
- ✅ Renamed `state_data` → `observation` (clearer naming)
- ✅ Added `truncated` for modern Gym API
- ✅ Separated `info` and `metadata` for clarity
- ✅ Added indexes on `parent_state_id` and `step_number`
- ✅ Added helper methods: `get_lineage()`, `get_depth()`

### 2. Simulation Table (Configuration)

```python
class Simulation(Base):
    """Simulation configuration - analogous to a git repository."""
    
    id = String (UUID)
    name = String
    description = Text
    
    # Configuration
    environment_name = String      # e.g., "CartPole-v1"
    environment_config = JSON      # Env-specific params
    agent_type = String           # e.g., "DQN", "PPO"
    agent_config = JSON           # Agent hyperparameters
    
    # Metadata
    max_steps = JSON
    seed = JSON
    tags = JSON
    created_at = DateTime
```

**Key Features:**
- Separates configuration from execution
- Multiple runs can share same config
- Easy to compare different agent types

**Improvements from original design:**
- ✅ Split `environment_config` into `environment_name` + `environment_config`
- ✅ Added `agent_type` field for filtering/querying
- ✅ Added `tags` for organization
- ✅ Added indexes on common query patterns

### 3. SimulationRun Table (Branches)

```python
class SimulationRun(Base):
    """An execution path - analogous to a git branch."""
    
    id = String (UUID)
    simulation_id = String (FK)
    
    # Branch identity
    name = String                    # e.g., "main", "lr-0.01"
    description = Text
    
    # State references
    root_state_id = String (FK)      # First state in this run
    current_state_id = String (FK)   # Latest state
    
    # Branching metadata
    parent_run_id = String (FK)           # Parent branch
    branch_point_state_id = String (FK)   # Where branch occurred
    config_overrides = JSON               # Modified config for this run
    
    # Status tracking
    status = String                  # active, paused, completed, failed
    total_steps = Integer
    total_reward = JSON
    
    # Timestamps
    created_at = DateTime
    started_at = DateTime
    completed_at = DateTime
```

**Key Features:**
- Tracks a specific path through the state tree
- Can branch from any existing state
- Inherits parent config with optional overrides
- Status management for pausing/resuming

**Improvements from original design:**
- ✅ Added `config_overrides` for per-run modifications
- ✅ Added `started_at` timestamp (separate from `created_at`)
- ✅ Changed `total_reward` to JSON (supports complex rewards)
- ✅ Added comprehensive indexes
- ✅ Added `get_state_sequence()` helper method

### 4. Association Table (run_state_sequence)

```python
run_state_sequence = Table(
    'run_state_sequence',
    Column('id', String, primary_key=True),
    Column('run_id', String, FK),
    Column('state_id', String, FK),
    Column('sequence_order', Integer),  # NEW: Order within run
    Column('created_at', DateTime),     # NEW: Timestamp
)
```

**Critical Improvements:**
- ✅ **Added `id` primary key** (was missing - would cause issues!)
- ✅ **Added `sequence_order`** to maintain state order within runs
- ✅ **Added `created_at`** for temporal queries
- ✅ Added indexes: `(run_id, sequence_order)` and `(state_id, run_id)`
- ✅ Changed from many-to-many to proper junction table

**Why this matters:** Without `sequence_order`, you can't reconstruct the exact path a run took through the state tree. This is essential for:
- Replaying episodes
- Analyzing trajectories
- Computing cumulative rewards

## Usage Examples

### Example 1: Basic Simulation Run

```python
from simulation_db.database import SessionLocal, init_db
from simulation_db.managers.simulation_manager import SimulationManager
from simulation_db.managers.state_manager import StateManager

# Setup
init_db()
session = SessionLocal()
sim_manager = SimulationManager(session)
state_manager = StateManager(session)

# Create simulation config
simulation = sim_manager.create_simulation(
    name="CartPole-DQN",
    environment_name="CartPole-v1",
    agent_type="DQN",
    agent_config={"learning_rate": 0.001, "epsilon": 1.0}
)

# Create initial state
root_state = state_manager.create_state(
    observation=[0.0, 0.0, 0.0, 0.0],
    step_number=0
)

# Create run
run = sim_manager.create_run(
    simulation_id=simulation.id,
    name="main",
    root_state=root_state
)

# Add states as simulation progresses
for step in range(100):
    new_state = state_manager.create_state(
        observation=next_obs,
        action=action,
        reward=reward,
        done=done,
        step_number=step + 1,
        parent_state_id=current_state.id
    )
    sim_manager.add_state_to_run(run, new_state)
    current_state = new_state
```

### Example 2: Branching from a State

```python
# Pause main run at step 200
sim_manager.pause_run(main_run)

# Get the state at step 200
branch_state = session.query(State).filter(
    State.id == main_run.current_state_id
).first()

# Create branched run with higher learning rate
branch_run = sim_manager.branch_from_state(
    parent_run=main_run,
    branch_point_state=branch_state,
    new_run_name="high-lr-experiment",
    config_overrides={"learning_rate": 0.01}  # 10x higher
)

# branch_run now has:
# - All states from main_run up to step 200
# - root_state_id = branch_state.id
# - parent_run_id = main_run.id
# - branch_point_state_id = branch_state.id

# Continue both branches independently
# They will diverge in the state tree!
```

### Example 3: Analyzing the Tree

```python
# Get all branches for a simulation
tree = sim_manager.get_run_tree(simulation.id)
# Returns nested structure showing parent-child relationships

# Get state path for a specific run
lineage = state_manager.get_state_path(final_state)
# Returns list from root to final_state

# Find where branches diverged
children = state_manager.get_children(branch_state)
# Returns all states that branched from this point
```

## Manager Classes

### SimulationManager

Handles high-level simulation operations:
- `create_simulation()` - Create configuration
- `create_run()` - Start new run
- `branch_from_state()` - **Key method for branching**
- `add_state_to_run()` - Add state to run sequence
- `pause_run()` / `complete_run()` - Status management
- `get_run_tree()` - Visualize branch structure

### StateManager  

Handles state-level operations:
- `create_state()` - Create new state in tree
- `get_state_path()` - Get lineage from root
- `get_children()` - Find branches from a state
- `get_terminal_states()` - Find all episode endings

## Key Design Decisions

### 1. Why separate State from SimulationRun?

**States are shared across branches.** When you branch at step 200:
- Steps 0-200 are the same in both branches
- Only one copy of those states exists in the DB
- Both runs reference the same states via `run_state_sequence`

This saves storage and makes it clear where branches diverge.

### 2. Why config_overrides instead of full config?

**Inheritance with changes.** When branching:
```python
parent_config = {"learning_rate": 0.001, "epsilon": 0.1, "gamma": 0.99}
branch_overrides = {"learning_rate": 0.01}

# Effective config for branch:
# {"learning_rate": 0.01, "epsilon": 0.1, "gamma": 0.99}
```

This makes it easy to see what changed between branches.

### 3. Why both root_state_id and branch_point_state_id?

- `root_state_id`: First state in this run (might be inherited)
- `branch_point_state_id`: State where this run diverged from parent

For the main branch: `branch_point_state_id = None` (no parent)  
For branched runs: `branch_point_state_id` shows the fork point

### 4. Why sequence_order in the association table?

The state tree is a DAG, but each run follows a specific linear path. `sequence_order` preserves that ordering:

```
State tree:        Run "main":         Run "branch":
    1                 [1,2,3,4,5]         [1,2,3,6,7]
   / \
  2   6
  |   |
  3   7
  |
  4
  |
  5
```

Without `sequence_order`, you'd lose the path information!

## CartPole Branching Example

See `examples/cartpole_branching_example.py` for a complete working example that:

1. ✅ Creates a DQN agent with learning_rate=0.001
2. ✅ Runs CartPole for 200 steps (main branch)
3. ✅ Pauses at step 200
4. ✅ Creates a branch with learning_rate=0.01 (10x higher)
5. ✅ Continues both branches independently
6. ✅ Compares results and shows the tree structure

Run it with:
```bash
# Setup database
cp .env.example .env
# Edit .env with your DATABASE_URL

# Initialize schema
python scripts/init_db.py

# Run example
python examples/cartpole_branching_example.py
```

Or test with SQLite:
```bash
python test_branching.py
```

## Performance Considerations

### Indexes Added

```sql
-- States table
CREATE INDEX ix_parent_step ON states(parent_state_id, step_number);
CREATE INDEX ix_done_created ON states(done, created_at);

-- SimulationRuns table  
CREATE INDEX ix_sim_status ON simulation_runs(simulation_id, status);
CREATE INDEX ix_parent_branch ON simulation_runs(parent_run_id, branch_point_state_id);

-- Association table
CREATE INDEX ix_run_sequence ON run_state_sequence(run_id, sequence_order);
CREATE INDEX ix_state_run ON run_state_sequence(state_id, run_id);
```

### Query Patterns

**Fast queries:**
- ✅ Get all states for a run: Use `run_state_sequence` with `sequence_order`
- ✅ Find children of a state: Indexed on `parent_state_id`
- ✅ Get all runs for a simulation: Indexed on `simulation_id`

**Potentially slow queries:**
- ⚠️ Deep lineage traversal (recursive parent lookups)
- ⚠️ Finding all descendants of a state (requires graph traversal)

For large trees, consider adding:
- Materialized path (store full path as string)
- Nested sets (left/right values for subtree queries)
- Closure table (explicit ancestor-descendant pairs)

## Future Enhancements

1. **State compression**: Store deltas instead of full observations
2. **Lazy loading**: Only load states on demand
3. **Checkpointing**: Mark certain states as "important" for faster access
4. **Merge operations**: Combine insights from multiple branches
5. **Pruning**: Remove old branches while preserving main paths
6. **Visualization**: Generate git-style branch diagrams

## Summary of Improvements

### Original Design Issues Fixed

1. ❌ **Association table had no primary key** → ✅ Added `id` column
2. ❌ **No sequence tracking** → ✅ Added `sequence_order` 
3. ❌ **Poor indexing** → ✅ Added 8+ strategic indexes
4. ❌ **No config override mechanism** → ✅ Added `config_overrides`
5. ❌ **Unclear naming** (`state_data`) → ✅ Renamed to `observation`
6. ❌ **Missing Gym v0.26+ support** → ✅ Added `truncated` field
7. ❌ **No helper methods** → ✅ Added lineage, depth, sequence methods
8. ❌ **No manager classes** → ✅ Added SimulationManager and StateManager

### Result

A production-ready, git-like simulation database that:
- ✅ Enables branching from any state
- ✅ Preserves complete history
- ✅ Supports configuration experiments
- ✅ Scales to thousands of states per run
- ✅ Provides intuitive query interface
- ✅ Works with modern RL frameworks (Gymnasium, etc.)
