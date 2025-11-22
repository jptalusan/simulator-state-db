"""
CartPole Branching Example - Using API Endpoints

This example demonstrates the same branching functionality as cartpole_branching_example.py
but uses REST API endpoints instead of direct database access.

This shows how to:
1. Create simulations via API
2. Create runs via API
3. Add states to runs via API
4. Branch runs via API
5. Query results via API
"""

import requests
import gymnasium as gym
import numpy as np
from typing import Dict, Optional

# API base URL
API_BASE_URL = "http://localhost:8000"


class SimpleDQNAgent:
    """Simplified DQN agent for demonstration."""
    
    def __init__(self, observation_space, action_space, learning_rate: float = 0.001):
        self.observation_space = observation_space
        self.action_space = action_space
        self.learning_rate = learning_rate
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        
        obs_dim = observation_space.shape[0]
        act_dim = action_space.n
        self.weights = np.random.randn(obs_dim, act_dim) * 0.1
        
        print(f"  Agent initialized with learning_rate={learning_rate}")
    
    def predict(self, observation: np.ndarray) -> int:
        if np.random.random() < self.epsilon:
            return self.action_space.sample()
        q_values = observation @ self.weights
        return int(np.argmax(q_values))
    
    def update(self, observation: np.ndarray, action: int, reward: float, next_obs: np.ndarray, done: bool):
        if done:
            target = reward
        else:
            next_q = np.max(next_obs @ self.weights)
            target = reward + 0.99 * next_q
        
        current_q = (observation @ self.weights)[action]
        td_error = target - current_q
        self.weights[:, action] += self.learning_rate * td_error * observation
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


def run_simulation_episode(
    env: gym.Env,
    agent: SimpleDQNAgent,
    run_id: str,
    max_steps: int = 500,
    start_from_state: Optional[Dict] = None,
    branch_at_step: Optional[int] = None,
) -> tuple[str, Dict, bool]:
    """Run one episode using API endpoints.
    
    Returns:
        (run_id, final_state, reached_branch_point)
    """
    if start_from_state:
        print(f"  Starting from existing state (step {start_from_state['step_number']})")
        env.reset()
        if start_from_state.get('info') and 'env_state' in start_from_state['info']:
            env.unwrapped.state = np.array(start_from_state['info']['env_state'])
        observation = np.array(start_from_state['observation'])
        step_count = start_from_state['step_number']
        parent_state_id = start_from_state['id']
    else:
        observation, info = env.reset()
        step_count = 0
        parent_state_id = None
    
    total_reward = 0.0
    reached_branch_point = False
    final_state = None
    
    print(f"  Running episode for run ID '{run_id}'...")
    
    for step in range(max_steps):
        if branch_at_step is not None and step_count >= branch_at_step:
            print(f"  Reached branch point at step {step_count}")
            reached_branch_point = True
            break
        
        action = agent.predict(observation)
        next_observation, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        total_reward += reward
        
        agent.update(observation, action, reward, next_observation, done)
        
        step_count += 1
        info['env_state'] = env.unwrapped.state.tolist()
        
        # Create state via API
        state_payload = {
            "observation": next_observation.tolist(),
            "action": int(action),
            "reward": float(reward),
            "done": done,
            "truncated": truncated,
            "step_number": step_count,
            "parent_state_id": parent_state_id,
            "info": info,
            "extra_metadata": {
                "epsilon": agent.epsilon,
                "learning_rate": agent.learning_rate,
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/runs/{run_id}/states",
            json=state_payload
        )
        response.raise_for_status()
        final_state = response.json()
        parent_state_id = final_state['id']
        
        if (step + 1) % 100 == 0:
            print(f"    Step {step_count}, Total reward: {total_reward:.2f}, Epsilon: {agent.epsilon:.3f}")
        
        observation = next_observation
        
        if done:
            print(f"  Episode finished at step {step_count}, Total reward: {total_reward:.2f}")
            break
    
    return run_id, final_state, reached_branch_point


def main():
    """Main branching demonstration using API."""
    print("=" * 80)
    print("CartPole Branching Example - Using REST API")
    print("=" * 80)
    
    # 1. Create simulation via API
    print("\n1. Creating simulation via API...")
    sim_payload = {
        "name": "CartPole-DQN-Branching-Demo-API",
        "description": "Demonstrates branching with different learning rates via API",
        "environment_name": "CartPole-v1",
        "agent_type": "SimpleDQN",
        "agent_config": {
            "learning_rate": 0.001,
            "epsilon_start": 1.0,
            "epsilon_decay": 0.995,
            "epsilon_min": 0.01,
        },
        "environment_config": {}
    }
    
    response = requests.post(f"{API_BASE_URL}/simulations", json=sim_payload)
    response.raise_for_status()
    simulation = response.json()
    simulation_id = simulation['id']
    print(f"  Created simulation: {simulation['name']} (ID: {simulation_id})")
    
    # 2. Create environment and agent for main branch
    print("\n2. Starting main branch...")
    env = gym.make("CartPole-v1")
    agent_main = SimpleDQNAgent(
        env.observation_space,
        env.action_space,
        learning_rate=0.001
    )
    
    # 3. Create root state via API
    print("  Creating root state via API...")
    dummy_obs, info = env.reset()
    info['env_state'] = env.unwrapped.state.tolist()
    
    root_state_payload = {
        "observation": dummy_obs.tolist(),
        "step_number": 0,
        "parent_state_id": None,
        "info": info
    }
    
    response = requests.post(f"{API_BASE_URL}/states", json=root_state_payload)
    response.raise_for_status()
    root_state = response.json()
    root_state_id = root_state['id']
    print(f"  Created root state (ID: {root_state_id})")
    
    # 4. Create main run via API
    print("  Creating 'main' run via API...")
    run_payload = {
        "name": "main",
        "root_state_id": root_state_id,
        "description": "Main branch with lr=0.001"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/simulations/{simulation_id}/runs",
        json=run_payload
    )
    response.raise_for_status()
    main_run = response.json()
    main_run_id = main_run['id']
    print(f"  Created run: {main_run['name']} (ID: {main_run_id})")
    
    # 5. Run main branch until branch point
    BRANCH_AT_STEP = 6
    print(f"\n3. Running main branch until step {BRANCH_AT_STEP}...")
    
    # Fetch root state details for starting
    response = requests.get(f"{API_BASE_URL}/runs/{main_run_id}/states")
    response.raise_for_status()
    states_data = response.json()
    root_state_full = states_data['states'][0] if states_data['states'] else None
    
    main_run_id, branch_state, reached_branch = run_simulation_episode(
        env=env,
        agent=agent_main,
        run_id=main_run_id,
        max_steps=500,
        start_from_state=root_state_full,
        branch_at_step=BRANCH_AT_STEP,
    )
    
    if not reached_branch:
        print("  Main branch completed before reaching branch point!")
        return
    
    # 6. Create branch via API
    print("\n4. Creating branch with higher learning rate via API...")
    branch_payload = {
        "parent_run_id": main_run_id,
        "branch_point_state_id": branch_state['id'],
        "new_run_name": "high-lr-experiment",
        "config_overrides": {"learning_rate": 0.01},
        "description": "Branched from main with lr=0.01 (10x higher)"
    }
    
    response = requests.post(f"{API_BASE_URL}/runs/branch", json=branch_payload)
    response.raise_for_status()
    branch_run = response.json()
    branch_run_id = branch_run['id']
    print(f"  Created branch: {branch_run['name']} (ID: {branch_run_id})")
    
    # 7. Create new agent and continue branch
    env_branch = gym.make("CartPole-v1")
    agent_branch = SimpleDQNAgent(
        env_branch.observation_space,
        env_branch.action_space,
        learning_rate=0.01
    )
    
    agent_branch.weights = agent_main.weights.copy()
    agent_branch.epsilon = agent_main.epsilon
    
    print(f"  Continuing branch run from step {BRANCH_AT_STEP}...")
    branch_run_id, final_branch_state, _ = run_simulation_episode(
        env=env_branch,
        agent=agent_branch,
        run_id=branch_run_id,
        max_steps=300,
        start_from_state=branch_state,
        branch_at_step=None,
    )
    
    # 8. Resume main branch
    print(f"\n5. Resuming main branch from step {BRANCH_AT_STEP}...")
    main_run_id, final_main_state, _ = run_simulation_episode(
        env=env,
        agent=agent_main,
        run_id=main_run_id,
        max_steps=300,
        start_from_state=branch_state,
        branch_at_step=None,
    )
    
    # 9. Show results via API
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    # Get all runs
    response = requests.get(f"{API_BASE_URL}/simulations/{simulation_id}/runs")
    response.raise_for_status()
    runs = response.json()
    
    for run in runs:
        print(f"\n{run['name']} (ID: {run['id']}):")
        print(f"  Total steps: {run['total_steps']}")
        print(f"  Total reward: {run['total_reward']}")
        print(f"  Status: {run['status']}")
        if run['parent_run_id']:
            print(f"  Parent run: {run['parent_run_id']}")
            print(f"  Branched at state: {run['branch_point_state_id']}")
    
    # 10. Show tree structure
    print("\n" + "=" * 80)
    print("SIMULATION TREE STRUCTURE")
    print("=" * 80)
    
    response = requests.get(f"{API_BASE_URL}/simulations/{simulation_id}/tree")
    response.raise_for_status()
    tree_data = response.json()
    print_tree(tree_data['tree'])
    
    # 11. Show divergence analysis
    print("\n" + "=" * 80)
    print("STATE TRAVERSAL - SHOWING DIVERGENCE")
    print("=" * 80)
    
    response = requests.get(f"{API_BASE_URL}/runs/{main_run_id}/compare/{branch_run_id}")
    response.raise_for_status()
    comparison = response.json()
    
    # Calculate rewards for each segment
    shared_reward = sum(s['reward'] or 0 for s in comparison['shared'])
    main_divergent_reward = sum(s['reward'] or 0 for s in comparison['run1_only']) if comparison['run1_only'] else 0
    branch_divergent_reward = sum(s['reward'] or 0 for s in comparison['run2_only']) if comparison['run2_only'] else 0
    
    print("\nShared history (both runs follow identical path):")
    print(f"  Total shared states: {comparison['shared_count']}")
    print(f"  Total reward (shared segment): {shared_reward:.2f}")
    if comparison['shared_count'] >= 5:
        print("  Last 5 states before divergence:")
        for state in comparison['shared'][-5:]:
            obs_preview = state['observation'][:2] if state['observation'] else []
            print(f"    Step {state['step_number']}: reward={state['reward']}, obs={obs_preview}, done={state['done']}")
    elif comparison['shared']:
        print("  All shared states:")
        for state in comparison['shared']:
            obs_preview = state['observation'][:2] if state['observation'] else []
            print(f"    Step {state['step_number']}: reward={state['reward']}, obs={obs_preview}, done={state['done']}")
    
    if comparison['divergence_point']:
        print(f"\n  >>> DIVERGENCE POINT: Step {comparison['divergence_point']['step_number']} <<<")
    
    print("\nMain branch continuation (lr=0.001):")
    print(f"  States after divergence: {comparison['run1_unique_count']}")
    if comparison['run1_only']:
        print(f"  Steps {comparison['run1_only'][0]['step_number']} to {comparison['run1_only'][-1]['step_number']}")
        print(f"  Total reward (divergent segment): {main_divergent_reward:.2f}")
        print(f"  Total reward (shared + divergent): {shared_reward + main_divergent_reward:.2f}")
        if comparison['run1_unique_count'] >= 5:
            print("  Last 5 states:")
            for state in comparison['run1_only'][-5:]:
                obs_preview = state['observation'][:2] if state['observation'] else []
                print(f"    Step {state['step_number']}: reward={state['reward']}, obs={obs_preview}, done={state['done']}")
        else:
            for state in comparison['run1_only']:
                obs_preview = state['observation'][:2] if state['observation'] else []
                print(f"    Step {state['step_number']}: reward={state['reward']}, obs={obs_preview}, done={state['done']}")
    
    print("\nDivergent branch continuation (lr=0.01, 10x higher):")
    print(f"  States after divergence: {comparison['run2_unique_count']}")
    if comparison['run2_only']:
        print(f"  Steps {comparison['run2_only'][0]['step_number']} to {comparison['run2_only'][-1]['step_number']}")
        print(f"  Total reward (divergent segment): {branch_divergent_reward:.2f}")
        print(f"  Total reward (shared + divergent): {shared_reward + branch_divergent_reward:.2f}")
        if comparison['run2_unique_count'] >= 5:
            print("  Last 5 states:")
            for state in comparison['run2_only'][-5:]:
                obs_preview = state['observation'][:2] if state['observation'] else []
                print(f"    Step {state['step_number']}: reward={state['reward']}, obs={obs_preview}, done={state['done']}")
        else:
            for state in comparison['run2_only']:
                obs_preview = state['observation'][:2] if state['observation'] else []
                print(f"    Step {state['step_number']}: reward={state['reward']}, obs={obs_preview}, done={state['done']}")
    
    print("\nTotal states in database:")
    print(f"  Main branch: {runs[0]['total_steps']} states")
    print(f"  Divergent branch: {runs[1]['total_steps']} states")
    print(f"  Unique states (counting shared once): {comparison['shared_count'] + comparison['run1_unique_count'] + comparison['run2_unique_count']}")
    
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
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server!")
        print("Make sure the API is running:")
        print("  uvicorn simulation_db.api.app:app --reload --host 0.0.0.0 --port 8000")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ API Error: {e}")
        print(f"Response: {e.response.text}")
