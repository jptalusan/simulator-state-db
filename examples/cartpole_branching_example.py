"""
CartPole Branching Example - Demonstrates Git-Tree Simulation Structure

This example shows how to:
1. Run a CartPole simulation with a DQN agent
2. Pause at a specific state (step N)
3. Branch into a new simulation with modified learning rate
4. Continue both branches independently
5. Compare results across branches

The database structure mirrors git:
- Simulation ~= repository configuration
- SimulationRun ~= branch
- State ~= commit

You can branch at any state and create alternative timelines.
"""

import os
import sys
import gymnasium as gym
import numpy as np
from typing import Dict, Any, Optional

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation_db.database import SessionLocal, init_db
from simulation_db.managers.simulation_manager import SimulationManager
from simulation_db.managers.state_manager import StateManager
from simulation_db.models import Simulation, SimulationRun, State


class SimpleDQNAgent:
    """Simplified DQN agent for demonstration.
    
    In production, you'd use a proper RL library like stable-baselines3.
    This is just for showing the branching concept.
    """
    
    def __init__(self, observation_space, action_space, learning_rate: float = 0.001):
        self.observation_space = observation_space
        self.action_space = action_space
        self.learning_rate = learning_rate
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        
        # Simple linear model weights (observation_dim -> action_dim)
        obs_dim = observation_space.shape[0]
        act_dim = action_space.n
        self.weights = np.random.randn(obs_dim, act_dim) * 0.1
        
        print(f"  Agent initialized with learning_rate={learning_rate}")
    
    def predict(self, observation: np.ndarray) -> int:
        """Select action using epsilon-greedy."""
        if np.random.random() < self.epsilon:
            return self.action_space.sample()
        
        # Compute Q-values
        q_values = observation @ self.weights
        return int(np.argmax(q_values))
    
    def update(self, observation: np.ndarray, action: int, reward: float, next_obs: np.ndarray, done: bool):
        """Simplified Q-learning update."""
        # Compute target
        if done:
            target = reward
        else:
            next_q = np.max(next_obs @ self.weights)
            target = reward + 0.99 * next_q
        
        # Current Q-value
        current_q = (observation @ self.weights)[action]
        
        # Gradient update
        td_error = target - current_q
        self.weights[:, action] += self.learning_rate * td_error * observation
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


def run_simulation_episode(
    env: gym.Env,
    agent: SimpleDQNAgent,
    session,
    run: SimulationRun,
    state_manager: StateManager,
    sim_manager: SimulationManager,
    max_steps: int = 500,
    start_from_state: Optional[State] = None,
    branch_at_step: Optional[int] = None,
) -> tuple[SimulationRun, State, bool]:
    """Run one episode of the simulation.
    
    Returns:
        (run, final_state, reached_branch_point)
    """
    if start_from_state:
        # Restore environment to the branching state
        print(f"  Starting from existing state (step {start_from_state.step_number})")
        # Reset first to initialize the environment
        env.reset()
        # Then restore the exact internal state
        if start_from_state.info and 'env_state' in start_from_state.info:
            env.unwrapped.state = np.array(start_from_state.info['env_state'])
        observation = np.array(start_from_state.observation)
        step_count = start_from_state.step_number
        parent_state = start_from_state
    else:
        # Fresh start
        observation, info = env.reset()
        step_count = 0
        
        # Create root state
        # Save the full environment state for potential restoration
        info['env_state'] = env.unwrapped.state.tolist()
        parent_state = state_manager.create_state(
            observation=observation.tolist(),
            step_number=step_count,
            parent_state_id=None,
            info=info
        )
        
        # Add to run
        sim_manager.add_state_to_run(run, parent_state)
    
    total_reward = 0.0
    reached_branch_point = False
    
    print(f"  Running episode for run '{run.name}'...")
    
    for step in range(max_steps):
        # Check if we should stop for branching
        if branch_at_step is not None and step_count >= branch_at_step:
            print(f"  Reached branch point at step {step_count}")
            reached_branch_point = True
            break
        
        # Agent selects action
        action = agent.predict(observation)
        
        # Environment step
        next_observation, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        total_reward += reward
        
        # Update agent
        agent.update(observation, action, reward, next_observation, done)
        
        # Create new state in the tree
        step_count += 1
        # Save the full environment state for potential restoration
        info['env_state'] = env.unwrapped.state.tolist()
        new_state = state_manager.create_state(
            observation=next_observation.tolist(),
            action=int(action),
            reward=float(reward),
            done=done,
            truncated=truncated,
            step_number=step_count,
            parent_state_id=parent_state.id,
            info=info,
            extra_metadata={
                'epsilon': agent.epsilon,
                'learning_rate': agent.learning_rate,
            }
        )
        
        # Add to run sequence
        sim_manager.add_state_to_run(run, new_state)
        
        # Progress
        if (step + 1) % 100 == 0:
            print(f"    Step {step_count}, Total reward: {total_reward:.2f}, Epsilon: {agent.epsilon:.3f}")
        
        observation = next_observation
        parent_state = new_state
        
        if done:
            print(f"  Episode finished at step {step_count}, Total reward: {total_reward:.2f}")
            break
    
    # Update run status
    if not reached_branch_point:
        sim_manager.complete_run(run, total_reward=total_reward)
    else:
        sim_manager.pause_run(run)
    
    return run, parent_state, reached_branch_point


def main():
    """Main branching demonstration."""
    print("=" * 80)
    print("CartPole Branching Example - Git-Tree Simulation Structure")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    session = SessionLocal()
    
    sim_manager = SimulationManager(session)
    state_manager = StateManager(session)
    
    # Create simulation configuration
    print("\n2. Creating simulation configuration...")
    simulation = sim_manager.create_simulation(
        name="CartPole-DQN-Branching-Demo",
        description="Demonstrates branching with different learning rates",
        environment_name="CartPole-v1",
        agent_type="SimpleDQN",
        agent_config={
            "learning_rate": 0.001,
            "epsilon_start": 1.0,
            "epsilon_decay": 0.995,
            "epsilon_min": 0.01,
        },
        environment_config={},
    )
    print(f"  Created simulation: {simulation}")
    
    # Create environment and agent for main branch
    print("\n3. Starting main branch...")
    env = gym.make("CartPole-v1")
    agent_main = SimpleDQNAgent(
        env.observation_space,
        env.action_space,
        learning_rate=0.001
    )
    
    # Create main run
    print("  Creating 'main' run...")
    # Create root state with environment state saved
    dummy_obs, info = env.reset()
    info['env_state'] = env.unwrapped.state.tolist()
    root_state = state_manager.create_state(
        observation=dummy_obs.tolist(),
        step_number=0,
        parent_state_id=None,
        info=info
    )
    
    main_run = sim_manager.create_run(
        simulation_id=simulation.id,
        name="main",
        root_state=root_state,
        description="Main branch with lr=0.001",
    )
    
    # Run main branch until step 200 (our branch point)
    # Start from root_state to avoid creating duplicate step 0
    BRANCH_AT_STEP = 6
    print(f"  Running main branch until step {BRANCH_AT_STEP}...")
    main_run, branch_state, reached_branch = run_simulation_episode(
        env=env,
        agent=agent_main,
        session=session,
        run=main_run,
        state_manager=state_manager,
        sim_manager=sim_manager,
        max_steps=500,
        start_from_state=root_state,
        branch_at_step=BRANCH_AT_STEP,
    )
    
    if not reached_branch:
        print("  Main branch completed before reaching branch point!")
        session.close()
        return
    
    print(f"\n4. Creating branch with higher learning rate at step {BRANCH_AT_STEP}...")
    
    # Create branched run with different learning rate
    branch_run = sim_manager.branch_from_state(
        parent_run=main_run,
        branch_point_state=branch_state,
        new_run_name="high-lr-experiment",
        config_overrides={"learning_rate": 0.01},  # 10x higher
        description="Branched from main with lr=0.01 (10x higher)",
    )
    print(f"  Created branch: {branch_run}")
    
    # Create new agent with higher learning rate for branch
    env_branch = gym.make("CartPole-v1")
    agent_branch = SimpleDQNAgent(
        env_branch.observation_space,
        env_branch.action_space,
        learning_rate=0.01  # 10x higher
    )
    
    # Copy the main agent's weights to the branch agent (they share history)
    agent_branch.weights = agent_main.weights.copy()
    agent_branch.epsilon = agent_main.epsilon
    
    # Continue branch run
    print(f"  Continuing branch run from step {BRANCH_AT_STEP}...")
    branch_run, final_branch_state, _ = run_simulation_episode(
        env=env_branch,
        agent=agent_branch,
        session=session,
        run=branch_run,
        state_manager=state_manager,
        sim_manager=sim_manager,
        max_steps=300,  # Run for 300 more steps
        start_from_state=branch_state,
        branch_at_step=None,
    )
    
    # Continue main branch as well
    print(f"\n5. Resuming main branch from step {BRANCH_AT_STEP}...")
    main_run.status = 'active'
    session.commit()
    
    main_run, final_main_state, _ = run_simulation_episode(
        env=env,
        agent=agent_main,
        session=session,
        run=main_run,
        state_manager=state_manager,
        sim_manager=sim_manager,
        max_steps=300,
        start_from_state=branch_state,
        branch_at_step=None,
    )
    
    # Show results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    session.refresh(main_run)
    session.refresh(branch_run)
    
    print("\nMain Branch (lr=0.001):")
    print(f"  Total steps: {main_run.total_steps}")
    print(f"  Total reward: {main_run.total_reward}")
    print(f"  Status: {main_run.status}")
    
    print("\nBranch (lr=0.01, 10x higher):")
    print(f"  Total steps: {branch_run.total_steps}")
    print(f"  Total reward: {branch_run.total_reward}")
    print(f"  Status: {branch_run.status}")
    print(f"  Branched at step: {branch_state.step_number}")
    
    # Show tree structure
    print("\n" + "=" * 80)
    print("SIMULATION TREE STRUCTURE")
    print("=" * 80)
    tree = sim_manager.get_run_tree(simulation.id)
    print_tree(tree)
    
    # Demonstrate state traversal showing divergence
    print("\n" + "=" * 80)
    print("STATE TRAVERSAL - SHOWING DIVERGENCE")
    print("=" * 80)
    
    # Get comparison to show both paths
    comparison = state_manager.compare_runs(main_run, branch_run)
    
    print("\nShared history (both runs follow identical path):")
    print(f"  Total shared states: {len(comparison['shared'])}")
    if len(comparison['shared']) >= 5:
        print("  Last 5 states before divergence:")
        for state in comparison['shared'][-5:]:
            print(f"    Step {state.step_number}: reward={state.reward}, obs={state.observation[:2]}, done={state.done}")
    else:
        print("  All shared states:")
        for state in comparison['shared']:
            print(f"    Step {state.step_number}: reward={state.reward}, obs={state.observation[:2]}, done={state.done}")
    
    print(f"\n  >>> DIVERGENCE POINT: Step {comparison['divergence_point'].step_number} <<<")
    
    print("\nMain branch continuation (lr=0.001):")
    print(f"  States after divergence: {len(comparison['run1_only'])}")
    if comparison['run1_only']:
        main_divergent_reward = sum(s.reward or 0 for s in comparison['run1_only'])
        print(f"  Steps {comparison['run1_only'][0].step_number} to {comparison['run1_only'][-1].step_number}")
        print(f"  Total reward (divergent segment): {main_divergent_reward:.2f}")
        if len(comparison['run1_only']) >= 5:
            print("  Last 5 states:")
            for state in comparison['run1_only'][-5:]:
                print(f"    Step {state.step_number}: reward={state.reward}, obs={state.observation[:2]}, done={state.done}")
        else:
            for state in comparison['run1_only']:
                print(f"    Step {state.step_number}: reward={state.reward}, obs={state.observation[:2]}, done={state.done}")
    
    print("\nDivergent branch continuation (lr=0.01, 10x higher):")
    print(f"  States after divergence: {len(comparison['run2_only'])}")
    if comparison['run2_only']:
        branch_divergent_reward = sum(s.reward or 0 for s in comparison['run2_only'])
        print(f"  Steps {comparison['run2_only'][0].step_number} to {comparison['run2_only'][-1].step_number}")
        print(f"  Total reward (divergent segment): {branch_divergent_reward:.2f}")
        if len(comparison['run2_only']) >= 5:
            print("  Last 5 states:")
            for state in comparison['run2_only'][-5:]:
                print(f"    Step {state.step_number}: reward={state.reward}, obs={state.observation[:2]}, done={state.done}")
        else:
            for state in comparison['run2_only']:
                print(f"    Step {state.step_number}: reward={state.reward}, obs={state.observation[:2]}, done={state.done}")
    
    print("\nTotal states in database:")
    print(f"  Main branch: {main_run.total_steps} states")
    print(f"  Divergent branch: {branch_run.total_steps} states")
    print(f"  Unique states (counting shared once): {len(comparison['shared']) + len(comparison['run1_only']) + len(comparison['run2_only'])}")
    
    session.close()
    env.close()
    env_branch.close()
    
    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


def print_tree(tree, indent=0):
    """Recursively print the run tree."""
    for node in tree:
        prefix = "  " * indent + "├─ "
        print(f"{prefix}Run: {node['name']} (steps={node['total_steps']}, status={node['status']})")
        if node.get('branch_point'):
            print(f"{prefix}   └─ branched at state: {node['branch_point'][:8]}")
        if node['children']:
            print_tree(node['children'], indent + 1)


if __name__ == "__main__":
    main()
