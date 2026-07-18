# --- MUST be first: Minescript may run Python without a HOME ---
import os
from pathlib import Path

def fix_home_and_matplotlib():
    # Pick a writable "home" directory
    if os.name == "nt":
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        if not home:
            # Derive C:\Users\<name> from APPDATA if available
            appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
            if appdata:
                # e.g. C:\Users\marie\AppData\Roaming -> C:\Users\marie
                home = str(Path(appdata).parents[1])
            else:
                home = os.getcwd()

        os.environ.setdefault("USERPROFILE", home)
        os.environ.setdefault("HOME", home)

        # These help expanduser('~') on Windows
        p = Path(home)
        os.environ.setdefault("HOMEDRIVE", p.drive)               # "C:"
        os.environ.setdefault("HOMEPATH", "\\" + "\\".join(p.parts[1:]))  # "\Users\marie"

    # Keep matplotlib from touching ~/.matplotlib at all
    mpl_dir = os.path.join(os.getcwd(), "_mplconfig")
    os.makedirs(mpl_dir, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", mpl_dir)

fix_home_and_matplotlib()
import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor

from parkour_environment import ParkourEnvironment

file_path = r"/ml/parkour_courses/basic_5.txt"

def load_checkpoints():
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            row = [float(val) for val in line.strip().split(',')]
            data.append(row)
    return data

def make_env(checkpoints):
    def _init():
        env = ParkourEnvironment(
            checkpoints=checkpoints,
            max_steps=200,
            action_repeat=1,
            yaw_bins=21,
            curriculum_start=0,
            curriculum_end=len(checkpoints) - 1,  # eval uses full course
        )
        env = Monitor(env)
        return env
    return _init

def run_eval(model_path: str, vecnorm_path: str, n_episodes: int = 10, deterministic: bool = True):
    checkpoints = load_checkpoints()

    env = DummyVecEnv([make_env(checkpoints)])
    env = VecNormalize.load(vecnorm_path, env)
    env.training = False
    env.norm_reward = False

    model = PPO.load(model_path, env=env, device="auto")

    successes = 0
    ep_rewards = []
    ep_lengths = []

    for ep in range(n_episodes):
        obs = env.reset()
        done = False
        total_r = 0.0
        steps = 0

        while not done:
            action, _ = model.predict(obs, deterministic=deterministic)
            obs, reward, done, info = env.step(action)

            total_r += float(reward)
            steps += 1

            # info est une liste (vec env)
            if done:
                is_success = bool(info[0].get("is_success", False))
                successes += int(is_success)

        ep_rewards.append(total_r)
        ep_lengths.append(steps)
        print(f"Episode {ep+1}/{n_episodes} | reward={total_r:.3f} | steps={steps} | success={is_success}")

    print("\n=== Summary ===")
    print(f"Success rate: {successes}/{n_episodes} = {successes/n_episodes:.2%}")
    print(f"Avg reward:   {sum(ep_rewards)/len(ep_rewards):.3f}")
    print(f"Avg length:   {sum(ep_lengths)/len(ep_lengths):.1f}")

if __name__ == "__main__":
    # Exemple: tester le best
    run_eval(
        model_path="models/best/best_model.zip",
        vecnorm_path="models/best/vecnormalize_best.pkl",
        n_episodes=5,
        deterministic=True,
    )
