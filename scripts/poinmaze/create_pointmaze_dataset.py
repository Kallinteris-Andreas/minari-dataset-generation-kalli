
import gymnasium as gym
from controller import WaypointController
from minari import DataCollectorV0, StepPreProcessor
import minari
import numpy as np
import argparse

 
class PointMazeStepPreprocessor(StepPreProcessor):
    def __call__(self, env, obs, info, action=None, rew=None, terminated=None, truncated=None):
        qpos = obs['observation'][:2]
        qvel = obs['observation'][2:]
        goal = obs['desired_goal']
        
        step_data = super().__call__(env, obs, info, action, rew, terminated, truncated)
    
        if step_data['infos']['success']:
            step_data['truncations'] = True
           
        step_data['infos']['qpos'] = qpos
        step_data['infos']['qvel'] = qvel
        step_data['infos']['goal'] = goal
        
        return step_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=str, default="PointMaze_UMaze-v3", help="environment id to collect data from")
    parser.add_argument("--maze-solver", type=str, default="QIteration", help="algorithm to solve the maze and generate waypoints, can ve DFS or QIteration")
    parser.add_argument("--dataset-name", type=str, default="pointmaze-umaze-v0", help="name of the Minari dataset")
    parser.add_argument("--author", type=str, help="name of the author of the dataset")
    parser.add_argument("--author-email", type=str, help="email of the author of the dataset")
    parser.add_argument("--upload-dataset", type=bool, default=False, help="upload dataset to Farama server after collecting the data")
    parser.add_argument("--path_to_private_key", type=str, help="path to the private key to upload datset to the Farama GCP server")
    args = parser.parse_args()
    
    # Check if dataset already exist and load to add more data
    if args.dataset_name in minari.list_local_datasets(verbose=False):
        dataset = minari.load_dataset(args.dataset_name)
    else:
        dataset = None
        
    env = gym.make(args.env, continuing_task=True, max_episode_steps=1e6)   
    collector_env = DataCollectorV0(env, step_preprocessor=PointMazeStepPreprocessor, record_infos=True, max_steps_buffer=100000)

    obs, _ = collector_env.reset(seed=123)

    waypoint_controller = WaypointController(maze=env.maze)

    for n_step in range(1, int(1e6)+1):
        action = waypoint_controller.compute_action(obs)
        action += np.random.randn(*action.shape)*0.5

        obs, rew, terminated, truncated, info = collector_env.step(action)  

        if n_step % 200000 == 0:
            print('STEPS RECORDED:')
            print(n_step)
            if args.dataset_name not in minari.list_local_datasets(verbose=False):
                dataset = minari.create_dataset_from_collector_env(collector_env=collector_env, dataset_name=args.dataset_name, algorithm_name=args.maze_solver, code_permalink=None, author=args.author, author_email=args.author_email)
            else:
                # Update local Minari dataset every 200000 steps.
                # This works as a checkpoint to not lose the already colleced data
                dataset.update_dataset_from_collector_env(collector_env)
    
    if args.upload_dataset:
        minari.upload_dataset(dataset_name=args.dataset_name, path_to_private_key=args.path_to_private_key)