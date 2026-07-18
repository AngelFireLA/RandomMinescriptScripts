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

        # Fix for getpass.getuser() failing inside torch
        os.environ.setdefault("USERNAME", os.path.basename(home))
        os.environ.setdefault("USER", os.path.basename(home))
        os.environ.setdefault("LOGNAME", os.path.basename(home))

    # Keep matplotlib from touching ~/.matplotlib at all
    mpl_dir = os.path.join(os.getcwd(), "_mplconfig")
    os.makedirs(mpl_dir, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", mpl_dir)

fix_home_and_matplotlib()

# ---------------------- training script ----------------------
import glob
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback

from parkour_environment import ParkourEnvironment  # your file


# ==========================
# RESUME SETTINGS (edit here)
# ==========================
RESUME = False                # <-- old model incompatible with new action/obs space
RESUME_FROM = "best"          # "best" (recommended) or "latest"
TOTAL_TIMESTEPS = 10_000_000  # total target timesteps for the whole run
MODELS_DIR = "models"


# --------- your checkpoints file ----------
file_path = r"C:\Users\marie\Desktop\MultiMC\instances\1.21.10 minescripts\.minecraft\minescript\ml\parkour_courses"
file_path += r"\gauntlet.txt"

def load_checkpoints():
    data = []
    with open(file_path, "r") as f:
        for line in f:
            row = [float(val) for val in line.strip().split(",")]
            data.append(row)
    return data

def make_env(checkpoints, curriculum_start=0, curriculum_end=None):
    def _init():
        env = ParkourEnvironment(
            checkpoints=checkpoints,
            max_steps=200,
            action_repeat=1,
            yaw_bins=21,
            curriculum_start=curriculum_start,
            curriculum_end=curriculum_end,
        )
        return Monitor(env)
    return _init


# ---------------- callbacks ----------------
class EntCoefAnnealCallback(BaseCallback):
    def __init__(self, start: float, end: float, total_timesteps: int):
        super().__init__()
        self.start = float(start)
        self.end = float(end)
        self.total = int(total_timesteps)

    def _on_step(self) -> bool:
        # self.num_timesteps continues correctly when reset_num_timesteps=False
        progress = min(1.0, self.num_timesteps / max(1, self.total))
        self.model.ent_coef = self.start + (self.end - self.start) * progress
        return True

class EvalSaveBestWithVecNormalize(EvalCallback):
    def __init__(self, *args, best_vecnormalize_path: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.best_vecnormalize_path = best_vecnormalize_path

    def _on_step(self) -> bool:
        prev_best = self.best_mean_reward
        ok = super()._on_step()

        # If a new best is found, EvalCallback already saved best_model.zip.
        if self.best_mean_reward > prev_best and self.best_vecnormalize_path:
            venv = self.model.get_env()
            if isinstance(venv, VecNormalize):
                venv.save(self.best_vecnormalize_path)

        return ok


class CurriculumCallback(BaseCallback):
    """
    Monitors checkpoint success and progressively expands the curriculum window.
    When the agent reaches a checkpoint with high enough frequency, we extend
    the curriculum_end to include more checkpoints.
    """
    def __init__(self, expand_every: int = 25_000, expand_by: int = 3,
                 success_threshold: float = 0.3, verbose: int = 0):
        super().__init__(verbose)
        self.expand_every = expand_every  # check every N timesteps
        self.expand_by = expand_by        # how many checkpoints to add
        self.success_threshold = success_threshold
        self.last_check = 0
        self.checkpoint_successes = 0
        self.checkpoint_attempts = 0

    def _on_step(self) -> bool:
        # Count episodes via the Monitor wrapper info
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                self.checkpoint_attempts += 1
                # Consider it a success if the agent reached at least one checkpoint
                if info.get("cp_index", 0) > 0 or info.get("is_success", False):
                    self.checkpoint_successes += 1

        # Periodically check if we should expand
        if self.num_timesteps - self.last_check >= self.expand_every:
            self.last_check = self.num_timesteps

            if self.checkpoint_attempts > 0:
                rate = self.checkpoint_successes / self.checkpoint_attempts
                print(f"[Curriculum] Timestep {self.num_timesteps}: "
                      f"success rate = {rate:.2%} ({self.checkpoint_successes}/{self.checkpoint_attempts})")

                if rate >= self.success_threshold:
                    # Expand curriculum in all training envs
                    venv = self.model.get_env()
                    # Unwrap through VecNormalize if present
                    base_env = venv
                    while hasattr(base_env, 'venv'):
                        base_env = base_env.venv

                    for env in base_env.envs:
                        inner = env
                        # Unwrap Monitor
                        while hasattr(inner, 'env'):
                            inner = inner.env
                        if hasattr(inner, 'curriculum_end'):
                            old_end = inner.curriculum_end
                            max_end = len(inner.checkpoints) - 1
                            new_end = min(old_end + self.expand_by, max_end)
                            if new_end > old_end:
                                inner.curriculum_end = new_end
                                print(f"[Curriculum] Expanded window: {old_end} -> {new_end} "
                                      f"(of {max_end} total checkpoints)")
                            else:
                                print(f"[Curriculum] Already at max ({max_end})")

            # Reset counters for next window
            self.checkpoint_successes = 0
            self.checkpoint_attempts = 0

        return True


# ---------------- resume helpers ----------------
def _latest_file(pattern: str) -> str | None:
    files = glob.glob(pattern)
    if not files:
        return None
    # pick most recently modified
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]

def pick_resume_paths(models_dir: str, mode: str) -> tuple[str | None, str | None]:
    """
    Returns (model_zip_path, vecnormalize_pkl_path) or (None, None) if nothing found.
    mode="best" uses models/best/best_model.zip (+ vecnormalize_best.pkl if present).
    mode="latest" uses newest checkpoint zip in models/ plus matching/latest vecnormalize pkl.
    """
    models_dir = os.path.abspath(models_dir)

    best_model = os.path.join(models_dir, "best", "best_model.zip")
    best_vec   = os.path.join(models_dir, "best", "vecnormalize_best.pkl")

    if mode.lower() == "best":
        model_path = best_model if os.path.exists(best_model) else None
        vec_path = best_vec if os.path.exists(best_vec) else None

        # Fallback: if best model exists but vec doesn't, try to grab latest vecnormalize in models/
        if model_path and not vec_path:
            vec_path = _latest_file(os.path.join(models_dir, "**", "vecnormalize*.pkl"))
        return model_path, vec_path

    # mode == "latest"
    latest_zip = _latest_file(os.path.join(models_dir, "ppo_parkour_*_steps.zip"))
    if latest_zip is None:
        # fallback to ANY zip in models/
        latest_zip = _latest_file(os.path.join(models_dir, "**", "*.zip"))

    latest_vec = _latest_file(os.path.join(models_dir, "**", "vecnormalize*.pkl"))
    return latest_zip, latest_vec


def main():
    checkpoints = load_checkpoints()
    print("Loaded Checkpoints:", len(checkpoints))

    # Base training env (un-normalized)
    train_env = DummyVecEnv([make_env(checkpoints)])

    # Choose resume files (if enabled)
    resume_model_path = None
    resume_vec_path = None
    if RESUME:
        resume_model_path, resume_vec_path = pick_resume_paths(MODELS_DIR, RESUME_FROM)
        print("RESUME:", RESUME, "| RESUME_FROM:", RESUME_FROM)
        print("Resume model:", resume_model_path)
        print("Resume vecnorm:", resume_vec_path)

    # Build VecNormalize for training env
    if RESUME and resume_vec_path and os.path.exists(resume_vec_path):
        train_env = VecNormalize.load(resume_vec_path, train_env)
        train_env.training = True
        train_env.norm_reward = False
        print("Loaded VecNormalize stats for training.")
    else:
        train_env = VecNormalize(
            train_env,
            norm_obs=True,
            norm_reward=False,
            clip_obs=100.0,
        )
        print("Created fresh VecNormalize for training.")

    # Build eval env (use same normalization stats!)
    eval_env = DummyVecEnv([make_env(checkpoints)])
    if RESUME and resume_vec_path and os.path.exists(resume_vec_path):
        eval_env = VecNormalize.load(resume_vec_path, eval_env)
        print("Loaded VecNormalize stats for eval.")
    else:
        eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=100.0)
        print("Created fresh VecNormalize for eval.")

    eval_env.training = False
    eval_env.norm_reward = False

    print("Created Environments")

    # Either load existing model or create a new one
    policy_kwargs = dict(net_arch=[512, 256, 128])

    if RESUME and resume_model_path and os.path.exists(resume_model_path):
        model = PPO.load(resume_model_path, env=train_env, device="auto", verbose=1)
        print(f"Loaded model from: {resume_model_path}")
        print("Model timesteps already trained:", model.num_timesteps)
    else:
        model = PPO(
            "MlpPolicy",
            train_env,
            verbose=1,
            n_steps=2048,
            batch_size=256,
            gamma=0.995,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.02,
            learning_rate=3e-4,
            policy_kwargs=policy_kwargs,
            tensorboard_log="tb_parkour",
            device="auto",
        )
        print("Created new model from scratch.")

    os.makedirs(MODELS_DIR, exist_ok=True)

    checkpoint_cb = CheckpointCallback(
        save_freq=5_000,
        save_path=MODELS_DIR,
        name_prefix="ppo_parkour",
        save_replay_buffer=False,
        save_vecnormalize=True,
    )

    eval_cb = EvalSaveBestWithVecNormalize(
        eval_env,
        best_model_save_path=os.path.join(MODELS_DIR, "best"),
        log_path=os.path.join(MODELS_DIR, "eval"),
        eval_freq=25_000,
        n_eval_episodes=5,
        deterministic=True,
        render=False,
        best_vecnormalize_path=os.path.join(MODELS_DIR, "best", "vecnormalize_best.pkl"),
    )

    callbacks = [
        checkpoint_cb,
        EntCoefAnnealCallback(start=0.02, end=0.002, total_timesteps=TOTAL_TIMESTEPS),
        eval_cb,
        CurriculumCallback(expand_every=25_000, expand_by=3, success_threshold=0.3),
    ]

    # Compute remaining timesteps if resuming
    if RESUME and model.num_timesteps > 0:
        remaining = max(0, int(TOTAL_TIMESTEPS - model.num_timesteps))
        print(f"Resuming: {model.num_timesteps} done / {TOTAL_TIMESTEPS} total -> remaining {remaining}")
        if remaining > 0:
            model.learn(
                total_timesteps=remaining,
                callback=callbacks,
                reset_num_timesteps=False,   # IMPORTANT for true resume
            )
        else:
            print("Nothing to train: already reached TOTAL_TIMESTEPS.")
    else:
        print(f"Training from scratch to {TOTAL_TIMESTEPS} timesteps.")
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=callbacks,
            reset_num_timesteps=True,
        )

    # Save final artifacts
    model.save(os.path.join(MODELS_DIR, "ppo_parkour_final"))
    train_env.save(os.path.join(MODELS_DIR, "vecnormalize_final.pkl"))
    print("Saved final model + VecNormalize.")

if __name__ == "__main__":
    main()
