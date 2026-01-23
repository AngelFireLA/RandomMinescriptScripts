import math
import random
from math import floor

import gymnasium as gym
import numpy as np
from gymnasium import spaces

import minescript as m
from ml.player import Player

import time
def wait_game_ticks(n: int, timeout_s: float = 200.0):
    start = m.world_info().game_ticks
    target = start + n
    while True:
        now = m.world_info().game_ticks
        if now >= target:
            return
        m.flush()
        time.sleep(0.001)

def _overlaps_block_xz(px: float, pz: float, bx: int, bz: int) -> bool:
    half = 0.4 # Player radius
    margin = 0.03
    return (
        (px + half) > (bx + margin) and (px - half) < (bx + 1 - margin) and
        (pz + half) > (bz + margin) and (pz - half) < (bz + 1 - margin)
    )

one_hot = False
class ParkourEnvironment(gym.Env):
    metadata = {"render_modes": ["human"], "render_fps": 20}

    def __init__(self, checkpoints, max_steps=300, action_repeat=3, yaw_bins=11, render_mode=None):
        self.player = Player()
        super().__init__()
        self.checkpoints = checkpoints
        self.max_steps = int(max_steps)
        self.action_repeat = int(action_repeat)
        self.yaw_bins = int(yaw_bins)
        self.render_mode = render_mode

        # ----- Action space -----
        # [forward, , jump, sprint yaw_bin]
        self.action_space = spaces.MultiDiscrete([2, 2, 2, self.yaw_bins])
        #self.action_space = spaces.MultiDiscrete([2, 2, 2, 2, 2, self.yaw_bins])

        # ----- Observation space -----
        # You decide obs_dim after you finalize your feature vector length.
        # Example placeholders:
        obs_dim = self._compute_obs_dim()
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # internal state
        self.step_count = 0
        self.current_cp_index = 0
        self.prev_dist = None



    def _compute_obs_dim(self):
        total = 0
        total += len(["forward dist", "strafe dist", "vertical dist"])
        total += len(["forward vel", "strafe vel", "vertical vel"])
        total += len(["sin yaw", "cos_yaw"])
        total += len(["dist xz", "standing block category"])
        total += len(["is grounded", "time since last jump"])
        total += len(self.player.last_action)
        region = self.player.region_around
        region_size = (region[0]+region[1]+1)*(region[2]*2+1)*(region[3]+region[4]+1)
        if one_hot:
            region_size *= 9
        total += region_size
        return total

    def _decode_action(self, action):
        forward, jump, sprint, yaw_bin = action


        center = (self.yaw_bins - 1) / 2.0
        yaw_delta_deg = (yaw_bin - center)

        return {
            "forward": bool(forward),
            "jump": bool(jump),
            "sprint": bool(sprint),
            "yaw_delta_deg": float(yaw_delta_deg),
        }

    def _get_goal_checkpoint(self):
        # next checkpoint as goal (clamp at end)
        goal_i = min(self.current_cp_index + 1, len(self.checkpoints) - 1)
        return self.checkpoints[goal_i]

    def _get_info(self) -> dict:
        goal = self._get_goal_checkpoint()
        return {
            "cp_index": int(self.current_cp_index),
            "goal": tuple(goal),
            "dist_xz": float(self.player.dist_xz),
            "on_ground": bool(self.player.is_grounded),
            "standing_cat": int(self.player.standing_block_category),
            # useful for eval callbacks:
            "is_success": False,
        }

    def _get_obs(self) -> np.ndarray:
        # --- Update player snapshot ---
        self.player.update_yaw_pitch()
        self.player.update_velocity()
        self.player.update_standing_block()

        # grounded
        self.player.is_grounded = self.player.is_on_ground()

        # Distances to goal (in player frame)
        goal = self._get_goal_checkpoint()
        self.player.recalc_coords(goal)

        # Region one-hot (fetch region once, then sample)
        region = self.player.get_region_around()
        self.player.data_region_around = self.player.convert_region_to_data(region=region, one_hot=one_hot,
                                                                            num_categories=9)

        # --- Build feature vector in the SAME order as _compute_obs_dim() ---
        feats = []

        # (1) distances (3)
        feats.append(float(self.player.forward_dist/10))
        feats.append(float(self.player.strafe_dist/10))
        feats.append(float(self.player.vertical_dist/10))

        # (2) velocities (3)
        feats.append(float(self.player.vel_forward))
        feats.append(float(self.player.vel_strafe))
        feats.append(float(self.player.vel_vertical))

        # (3) yaw trig (2)
        # self.player.yaw = (sin_yaw, cos_yaw)
        sin_yaw, cos_yaw = self.player.yaw
        feats.append(float(sin_yaw))
        feats.append(float(cos_yaw))

        # (4) dist_xz + standing block category (2)
        feats.append(float(self.player.dist_xz))
        feats.append(float(self.player.standing_block_category))  # scalar (0..8)

        # (5) grounded + ticks_since_jump (2)
        feats.append(1.0 if self.player.is_grounded else 0.0)
        feats.append(float(self.player.ticks_since_jump))

        # (6) last actions (6 bools -> floats)
        feats.extend([1.0 if b else 0.0 for b in self.player.last_action])

        # (7) region one-hot
        feats.extend(self.player.data_region_around)

        obs = np.asarray(feats, dtype=np.float32)

        return obs

    def low_point(self):
        # get min of y of current checkpoint, one after and one before
        indices = [self.current_cp_index]

        if self.current_cp_index > 0:
            indices.append(self.current_cp_index - 1)
        if self.current_cp_index < len(self.checkpoints) - 1:
            indices.append(self.current_cp_index + 1)
        min_y = min([self.checkpoints[i][1] for i in indices])
        return min_y - 2

    def _release_all_controls(self):
        m.player_press_forward(False)
        m.player_press_jump(False)
        m.player_press_sprint(False)
        m.player_press_sneak(False)

    import math

    def calculate_yaw_to_target(self, player_x, player_z, target_x, target_z):
        dx = target_x - player_x
        dz = target_z - player_z
        # atan2 gives angle from +X axis, Minecraft yaw is from +Z axis
        yaw = -math.degrees(math.atan2(dx, dz))
        return yaw

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.step_count = 0
        self._release_all_controls()
        self.step_count = 0
        self.prev_dist = None
        self.player.ticks_since_jump = 999
        self.player.last_action = [False] * 3 #sneak
        #self.player.last_action = [False] * 5
        # choose start checkpoint (randomize during training, etc.)
        self.current_cp_index = int(self.np_random.integers(0, len(self.checkpoints) - 1))
        checkpoint = self.checkpoints[self.current_cp_index]
        x, y, z = checkpoint
        m.execute(f"tp {x} {y} {z}")
        goal = self._get_goal_checkpoint()
        yaw = self.calculate_yaw_to_target(x, z, goal[0], goal[2])

        m.player_set_orientation(yaw, 0)
        m.flush()  # important
        obs = self._get_obs()
        self.prev_dist = float(self.player.dist_xz)
        info = self._get_info()
        return obs, info


    def has_reached_goal(self):
        return self.current_cp_index == len(self.checkpoints) - 1

    def has_reached_checkpoint(self):
        cp_x, cp_y, cp_z = self._get_goal_checkpoint()
        x, y, z = m.player_position()

        bx = floor(cp_x)
        bz = floor(cp_z)

        y_ok = abs(y - cp_y) < 0.65

        xz_ok = _overlaps_block_xz(x, z, bx, bz)
        #print(xz_ok, y_ok, self.player.is_grounded)
        return bool(xz_ok and y_ok and self.player.is_grounded)

    def _compute_reward_and_done(self, actions):
        """
        Return: reward, terminated, truncated
        """
        terminated = False
        truncated = False
        reward = 0.0

        # Example termination logic:
        # - success: reached final checkpoint -> terminated True, big reward
        # - fail: fell below some Y -> terminated True, big penalty
        # - timeout: step_count >= max_steps -> truncated True

        if self.step_count >= self.max_steps:
            print("Too slow")
            truncated = True
            reward -= 1

        y = m.player_position()[1]
        if y <= self.low_point():
            terminated = True
            reward -= 2

        #time penalty
        reward -= 0.01

        # distance based reward
        if self.prev_dist is None:
            self.prev_dist = float(self.player.dist_xz)

        curr_dist = float(self.player.dist_xz)
        delta = self.prev_dist - curr_dist

        # clip to avoid huge spikes
        delta = float(np.clip(delta, -0.2, 0.2))
        reward += 0.2 * delta

        self.prev_dist = curr_dist

        if self.has_reached_checkpoint():
            print("Has reached checkpoint", self.current_cp_index)
            reward += 3
            self.current_cp_index += 1
            new_goal = self._get_goal_checkpoint()
            self.player.recalc_coords(new_goal)
            self.prev_dist = float(self.player.dist_xz)

            if self.has_reached_goal():
                print("reached end goal")
                reward += 10
                terminated = True



        return float(reward), bool(terminated), bool(truncated)

    def _apply_controls(self, a: dict):
        # yaw update (instant)
        yaw, pitch = m.player_orientation()
        m.player_press_sprint(a["sprint"])
        m.flush()
        m.player_press_forward(a["forward"])
        m.player_set_orientation(yaw + a["yaw_delta_deg"], pitch)
        m.flush()

    def _advance(self, ticks: int, jump: bool):
        if ticks <= 0:
            return

        if jump:
            m.player_press_jump(True)
            wait_game_ticks(1)
            m.player_press_jump(False)
            if ticks > 1:
                wait_game_ticks(ticks - 1)
            self.player.ticks_since_jump = 1
        else:
            self.player.ticks_since_jump += ticks
            wait_game_ticks(ticks)



    def step(self, action):
        self.step_count += 1
        action = np.array(action, dtype=np.int64)
        a = self._decode_action(action)
        self.player.last_action = [
            a["forward"],
            a["sprint"],
            a["jump"],
        ]
        # do the actions
        self._apply_controls(a)
        self._advance(self.action_repeat, jump=a["jump"])

        obs = self._get_obs()
        reward, terminated, truncated = self._compute_reward_and_done(a)
        info = self._get_info()

        if (terminated or truncated):
            self._release_all_controls()

        if terminated and self.has_reached_goal():
            info["is_success"] = True
        return obs, reward, terminated, truncated, info
