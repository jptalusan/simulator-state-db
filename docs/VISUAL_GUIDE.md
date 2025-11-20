# Git-Tree Simulation: Visual Guide

## State Tree Structure

```
                    State Tree (Shared across all runs)
                    
                            S0 (root)
                            |
                            S1
                            |
                            S2
                            |
                            S3
                           / \
                          /   \
                         /     \
                       S4       S4' (branched: higher LR)
                       |        |
                       S5       S5'
                       |        |
                       S6       S6'
                     (done)   (done)
                     
                     
    Run "main"                Run "high-lr-experiment"
    ──────────                ─────────────────────────
    States: [S0, S1, S2,      States: [S0, S1, S2, S3, S4', S5', S6']
             S3, S4, S5, S6]  
    Config: lr=0.001          Config: lr=0.01 (override)
    Branch point: None        Branch point: S3
    Parent run: None          Parent run: "main"
```

## Database Structure Diagram

```
┌──────────────────┐
│   Simulation     │  
│  (Repository)    │  Configuration template
├──────────────────┤
│ id               │
│ name             │  
│ environment_name │  "CartPole-v1"
│ agent_type       │  "DQN"
│ agent_config     │  {"learning_rate": 0.001, ...}
└────────┬─────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────────────┐           ┌──────────────────┐
│    SimulationRun         │   N:M     │      State       │
│      (Branch)            │◄─────────►│    (Commit)      │
├──────────────────────────┤ via       ├──────────────────┤
│ id                       │ run_state │ id               │
│ simulation_id (FK)       │ sequence  │ parent_state_id  │◄┐
│ name                     │           │ observation      │ │
│ root_state_id (FK)       ├──────────►│ action           │ │ Tree
│ current_state_id (FK)    │           │ reward           │ │ structure
│ parent_run_id (FK)       │◄┐         │ done             │ │
│ branch_point_state_id(FK)│ │         │ step_number      │ │
│ config_overrides         │ │         │ metadata         │─┘
│ status                   │ │         └──────────────────┘
│ total_steps              │ │
│ total_reward             │ │ Branching
└──────────────────────────┘ │ (self-referential)
          ▲                  │
          └──────────────────┘

┌────────────────────────────────┐
│   run_state_sequence           │  Junction table
│   (Association)                │  
├────────────────────────────────┤
│ id (PK)                        │  ← CRITICAL: Primary key
│ run_id (FK → simulation_runs)  │
│ state_id (FK → states)         │
│ sequence_order                 │  ← CRITICAL: Maintains order
│ created_at                     │
└────────────────────────────────┘
```

## Example Timeline: Branching in Action

```
Time  →

t0: Create simulation "CartPole-DQN"
    Config: {lr: 0.001, epsilon: 1.0, ...}

t1: Start run "main"
    ┌────────┐
    │ main   │  Status: active
    └────────┘
    States: [S0]

t2: Run for 200 steps
    ┌────────┐
    │ main   │  Status: active
    └────────┘
    States: [S0, S1, S2, ..., S200]

t3: Branch at S200 with higher LR
    ┌────────┐              ┌──────────────┐
    │ main   │  Status:     │ high-lr-exp  │
    └────────┘  paused      └──────────────┘
                            Status: active
                            Branch point: S200
                            Override: {lr: 0.01}
    
    States shared: [S0 → S200]

t4: Continue branch for 300 steps
    ┌────────┐              ┌──────────────┐
    │ main   │              │ high-lr-exp  │
    └────────┘              └──────────────┘
    States: [S0..S200]      States: [S0..S200, S201', S202', ..., S500']
                                            ↑
                                    New branch states

t5: Resume main for 300 steps
    ┌────────┐              ┌──────────────┐
    │ main   │              │ high-lr-exp  │
    └────────┘              └──────────────┘
    States: [S0..S200,      States: [S0..S200, S201', S202', ..., S500']
             S201, S202,
             ..., S500]

Final state tree:
                S0 → ... → S200
                            / \
                           /   \
                          /     \
                    S201...S500  S201'...S500'
                    (main cont)  (high-lr branch)
```

## Query Examples

### 1. Get all states for a run (in order)

```sql
SELECT s.*
FROM states s
JOIN run_state_sequence rss ON s.id = rss.state_id
WHERE rss.run_id = 'main-run-id'
ORDER BY rss.sequence_order;
```

Returns: `[S0, S1, S2, ..., S200, S201, S202, ..., S500]`

### 2. Find where branches diverged

```sql
SELECT sr.name, sr.branch_point_state_id, s.step_number
FROM simulation_runs sr
JOIN states s ON sr.branch_point_state_id = s.id
WHERE sr.parent_run_id = 'main-run-id';
```

Returns:
```
name             branch_point          step_number
high-lr-exp      S200                  200
```

### 3. Get all children of a state (branches)

```sql
SELECT *
FROM states
WHERE parent_state_id = 'S200';
```

Returns: `[S201, S201']` (both branches from S200)

### 4. Reconstruct episode trajectory

```python
# Using the manager
lineage = state_manager.get_state_path(final_state)

# Returns:
# [S0, S1, S2, S3, ... S200, S201', S202', ..., S500']
#                          ↑ 
#                    Branch point visible in parent_state_id
```

## Branching Scenarios

### Scenario 1: Hyperparameter Tuning

```
                    main (lr=0.001)
                    S0 → S1 → ... → S100
                                    / | \
                                   /  |  \
                    lr=0.01 ──────/   |   \────── lr=0.0001
                    S101' → ...       |
                                      |
                             lr=0.005 |
                             S101'' → ...
```

**Use case:** Test different learning rates from the same starting point

### Scenario 2: Policy Comparison

```
                    S0 (initial state)
                    |
                    S1 (train for 1000 steps)
                   / \
                  /   \
           DQN trained  A2C trained
           S2 → S3...   S2' → S3'...
```

**Use case:** Compare different algorithms from same initialization

### Scenario 3: Intervention Testing

```
                    S0 → S1 → ... → S50 (agent fails)
                                    |
                                    S51 (manual intervention)
                                   / \
                                  /   \
                    No help ─────/     \───── With hint
                    S52 → ...          S52' → ...
```

**Use case:** Test counterfactuals or human interventions

## Storage Efficiency

### Without branching (naive approach)

```
Run 1: [S0, S1, S2, ..., S500]  → 500 states
Run 2: [S0, S1, S2, ..., S500']  → 500 states (duplicate S0-S200!)
Run 3: [S0, S1, S2, ..., S500''] → 500 states (duplicate S0-S200!)

Total: 1,500 states
```

### With git-tree structure

```
Shared: [S0, S1, S2, ..., S200]  → 200 states
Run 1:  [S201, ..., S500]         → 300 states
Run 2:  [S201', ..., S500']       → 300 states  
Run 3:  [S201'', ..., S500'']     → 300 states

Total: 1,100 states (27% reduction!)
```

The more branches you have, the more you save!

## Implementation Checklist

When implementing this structure in your own code:

### Database Setup
- [ ] Create all tables with proper foreign keys
- [ ] Add all indexes (especially on `parent_state_id` and `sequence_order`)
- [ ] Test cascade deletes
- [ ] Verify unique constraints

### State Management
- [ ] Create states with proper parent relationships
- [ ] Store full observation (or implement compression)
- [ ] Include all MDP components (obs, action, reward, done)
- [ ] Add meaningful metadata (epsilon, Q-values, etc.)

### Run Management  
- [ ] Initialize root state before creating run
- [ ] Add states to run via association table with sequence_order
- [ ] Update current_state_id as simulation progresses
- [ ] Track total_steps and total_reward

### Branching
- [ ] Copy all states from parent run up to branch point
- [ ] Merge config_overrides with parent config
- [ ] Set parent_run_id and branch_point_state_id
- [ ] Reinitialize agent with new config at branch point

### Querying
- [ ] Use sequence_order for ordered state retrieval
- [ ] Implement lineage queries for full paths
- [ ] Build tree visualization from parent_run_id relationships
- [ ] Add pagination for large result sets

## Common Pitfalls

1. **Forgetting sequence_order**: States need ordering within runs!
2. **Missing primary key on junction table**: Causes duplicate issues
3. **Not using transactions**: Partial state additions can corrupt runs
4. **Loading too many states at once**: Use pagination or lazy loading
5. **Not handling circular references**: Validate parent_state_id doesn't create cycles
6. **Forgetting cascade deletes**: Orphaned states waste space

## Testing Your Implementation

```python
# Test 1: Basic run creation
def test_create_run():
    run = create_run(...)
    assert run.status == 'active'
    assert run.total_steps == 0

# Test 2: State addition maintains order
def test_state_order():
    states = get_run_states(run_id)
    for i, state in enumerate(states):
        assert state.step_number == i

# Test 3: Branching preserves history
def test_branching():
    branch = branch_from_state(parent_run, state_200)
    parent_states = get_run_states(parent_run.id)[:201]
    branch_states = get_run_states(branch.id)[:201]
    assert parent_states == branch_states  # Same history

# Test 4: Tree structure is valid
def test_tree_validity():
    states = get_all_states()
    for state in states:
        if state.parent_state_id:
            parent = get_state(state.parent_state_id)
            assert parent is not None  # No orphans
            assert parent.step_number < state.step_number  # No cycles
```

## Next Steps

1. **Run the example**: `python examples/cartpole_branching_example.py`
2. **Read the design doc**: `docs/GIT_TREE_DESIGN.md`
3. **Explore the database**: Use a SQL client to inspect tables
4. **Build your own**: Adapt for your specific RL environment
5. **Optimize**: Add compression, caching, or specialized indexes

## Resources

- SQLAlchemy docs: https://docs.sqlalchemy.org/
- Gymnasium docs: https://gymnasium.farama.org/
- RL algorithms: https://stable-baselines3.readthedocs.io/
- Graph databases: Consider Neo4j for very large trees
