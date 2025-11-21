# Simulator State Database

A **git-like branching database** for reinforcement learning simulations. Store, branch, and analyze your RL experiments with the same flexibility as version control.

This initial boilerplate uses [CartPoleV1](https://gymnasium.farama.org/environments/classic_control/cart_pole/) for demonstration. Code is located in `examples/`.

## Features

- 🌳 **Git-tree structure**: Branch from any state to explore alternative trajectories
- 💾 **Complete history**: Every state saved with observation, action, reward
- 🔀 **Easy branching**: Test different hyperparameters from the same starting point
- 📊 **Analysis tools**: Compare runs, visualize trees, query state lineage
- 🏃 **Production-ready**: Proper indexing, transactions, and cascade operations

## Quick Start

```bash
# Clone and setup
git clone <your-repo>
cd simulation-db

# Install dependencies
uv sync --extra dev

# 2. Configure database
cp .env.example .env
# Edit .env with your DATABASE_URL

# 1. Start Postgres database (make sure your port is unique, you might have another instance of postgres already running at the same port)
docker compose --env-file .env -f docker/docker-compose.yml up -d

# 3. Initialize schema
uv run python scripts/init_db.py

# 4. Run the branching example
uv run python examples/cartpole_branching_example.py

# 5. Run tests
uv run pytest
```

## The Git Analogy

| Git | Simulation DB | Purpose |
|-----|---------------|---------|
| Repository | `Simulation` | Configuration/template |
| Branch | `SimulationRun` | Execution path |
| Commit | `State` | MDP state snapshot |
| Branching | `branch_from_state()` | Create alternative timeline |

## Example: Branching with Different Learning Rates

```python
from simulation_db.database import SessionLocal, init_db
from simulation_db.managers.simulation_manager import SimulationManager

# Setup
init_db()
session = SessionLocal()
sim_manager = SimulationManager(session)

# Run with lr=0.001 for 200 steps
main_run = create_run(name="main", config={"lr": 0.001})
run_until_step(main_run, step=200)

# Branch with lr=0.01 from step 200
branch = sim_manager.branch_from_state(
    parent_run=main_run,
    branch_point_state=state_200,
    new_run_name="high-lr-experiment",
    config_overrides={"lr": 0.01}
)

# Continue both branches independently
# They share history up to step 200, then diverge!
```

## Documentation

- **[Git-Tree Design](docs/GIT_TREE_DESIGN.md)** - Complete design documentation and API reference
- **[Visual Guide](docs/VISUAL_GUIDE.md)** - Diagrams, examples, and common patterns
- **[API Docs](docs/api.md)** - FastAPI endpoints
- **[Examples](examples/)** - Working code samples

## Database Schema

### Core Models

**State** - Single MDP state (analogous to git commit)
- Stores: observation, action, reward, done, metadata
- Links: parent_state_id (forms tree structure)

**SimulationRun** - Execution path (analogous to git branch)  
- Tracks: sequence of states, current position, status
- Branching: parent_run_id, branch_point_state_id, config_overrides

**Simulation** - Configuration template (analogous to git repository)
- Defines: environment, agent type, hyperparameters

See [GIT_TREE_DESIGN.md](docs/GIT_TREE_DESIGN.md) for detailed schema.

## Running with Docker

### Docker Compose (Database only)

Start the Postgres database:

```bash
cp .env.example .env
# Edit .env to set POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB

docker compose -f docker/docker-compose.yml up -d
```

This runs a Postgres container. Run the app locally (see below) or build the app image.

<!-- ### Build Application Docker Image

```bash
docker build -t simulation-db -f docker/Dockerfile .

# Run the container
docker run --rm -p 8050:8050 \
  --env-file .env \
  simulation-db
``` -->

## Running Locally (Recommended for Development)

```bash
# Install dependencies
uv sync --extra dev

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Initialize database
python scripts/init_db.py

# With hot reload using uvicorn
uvicorn simulation_db.api.app:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
simulation_db/
├── models/          # SQLAlchemy ORM models
│   ├── state.py     # State (commit)
│   ├── simulation.py # Simulation (repo)
│   └── run.py       # SimulationRun (branch)
├── managers/        # Business logic
│   ├── simulation_manager.py  # Run creation, branching
│   └── state_manager.py       # State operations
├── api/             # FastAPI endpoints
└── database.py      # DB connection setup

examples/
├── cartpole_branching_example.py  # Full branching demo
└── basic_simulation.py

docs/
├── GIT_TREE_DESIGN.md   # Complete design docs
└── VISUAL_GUIDE.md      # Diagrams and examples
```

## Key Improvements Over Basic Design

✅ **Proper association table** - Added primary key and sequence_order  
✅ **Config overrides** - Branch with modified hyperparameters  
✅ **Comprehensive indexing** - Fast queries on common patterns  
✅ **Manager classes** - Clean API for operations  
✅ **Helper methods** - get_lineage(), get_state_sequence(), etc.  
✅ **Modern Gym support** - Handles truncated flag  
✅ **Status tracking** - active, paused, completed, failed  

## Use Cases

1. **Hyperparameter tuning**: Branch at convergence, test different LRs
2. **Policy comparison**: Start from same state, run different algorithms
3. **Intervention testing**: Branch to test counterfactuals
4. **Curriculum learning**: Branch to different difficulty levels
5. **Exploration strategies**: Compare epsilon-greedy variants

## API Endpoints

FastAPI server provides:
- `GET /health` - Health check
- `GET /simulations` - List simulations
- `POST /simulations` - Create simulation
- More endpoints in `simulation_db/api/app.py`

Access API docs at: `http://localhost:8000/docs`

## Visualizing postgres db using pgAdmin
1. Navigate to local [pgAdmin](http://localhost:8082/browser/)
2. Add a new server pointing to `db`.
3. Add needed credentials.

## Testing

```bash
# Quick test with SQLite (no database setup needed)
python test_branching.py

# Run pytest suite
pytest tests/

# Full example with Postgres (requires docker compose up first)
docker compose -f docker/docker-compose.yml up -d
python scripts/init_db.py
python examples/cartpole_branching_example.py
```

## Development (for other env)
You only need to modify:

1. 📝 Simulation configuration (environment name, agent type)
2. 📝 How you serialize observations/actions to JSON
3. 📝 (Optional) How you save/restore environment internal state
**Everything else works automatically** because the design uses flexible JSON storage and environment-agnostic abstractions!

## Performance Tips

- Use pagination for large result sets
- Index on frequently queried fields (already done)
- Consider materialized paths for deep trees
- Implement state compression for large observations
- Use connection pooling in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file

<!-- ## Citation

If you use this in research, please cite:

```bibtex
@software{simulation_db,
  title={Simulation-DB: Git-like Branching for RL Experiments},
  author={Your Name},
  year={2025},
  url={https://github.com/jptalusan/simulator-state-db}
}
``` -->

## Support

- 📖 [Documentation](docs/)
- 💬 [Issues](https://github.com/jptalusan/simulator-state-db/issues)
- 📧 Email: your.email@example.com

---

**Built with:** SQLAlchemy, PostgreSQL, FastAPI, Gymnasium
