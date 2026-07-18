import minescript as m
from minescript import EventQueue
import time
import math


# --- Helper Functions ---

def distance3d(p1, p2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))


def distance2d(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[2] - p2[2])


def aim_at_predicted(target_pos, target_vel, is_bow=False, dist=0.0):
    """Aims ahead of the target based on their velocity, with advanced projectile physics."""
    me = m.player()
    if not me:
        return

    # Cap erratic velocity spikes (e.g., from knockback)
    speed_sq = target_vel[0] ** 2 + target_vel[2] ** 2
    if speed_sq > 400:
        target_vel = [0, 0, 0]

    # Predict future position based on travel time
    projectile_speed = 53.0 if is_bow else 7.1  # Bow arrow vs max sprint-jump speed
    time_to_reach = min(dist / projectile_speed, 1.5)  # Cap prediction at 1.5s ahead

    pred_x = target_pos[0] + target_vel[0] * time_to_reach
    pred_z = target_pos[2] + target_vel[2] * time_to_reach

    my_pos = me.position
    dx = pred_x - my_pos[0]
    dy = (target_pos[1] + 1.62) - (my_pos[1] + 1.62)  # Eye height delta
    dz = pred_z - my_pos[2]

    horizontal_dist = math.hypot(dx, dz)

    if is_bow:
        # Advanced Quadratic Gravity & Drag Compensation for Minecraft Arrows
        # Fits the curve: steep drop at long ranges, mild at close range.
        arrow_drop = (0.03 * horizontal_dist) + (0.002 * horizontal_dist ** 2)
        dy += arrow_drop

    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, horizontal_dist))

    # Clamp pitch
    pitch = max(-90.0, min(90.0, pitch))
    m.player_set_orientation(yaw, pitch)


def dodge_logic():
    """Alternates strafing direction every 0.75 seconds to dodge close-range attacks."""
    t = time.time()
    if int(t / 0.75) % 2 == 0:
        m.player_press_left(True)
        m.player_press_right(False)
    else:
        m.player_press_left(False)
        m.player_press_right(True)


def release_all_keys():
    """Resets all simulated key presses."""
    m.player_press_forward(False)
    m.player_press_backward(False)
    m.player_press_left(False)
    m.player_press_right(False)
    m.player_press_use(False)
    m.player_press_attack(False)
    m.player_press_jump(False)
    m.player_press_sprint(False)


def wait_for_start():
    """Halts script execution until 'Start' is seen in the chat."""
    m.echo("Bot armed and ready. Waiting for 'Start'...")
    with EventQueue() as eq:
        eq.register_chat_listener()
        while True:
            event = eq.get(block=True)
            if event.type == "chat" and "Start" in event.message:
                m.echo("Match Started! Engaging...")
                break


def get_slot_by_name(name_substring):
    for item in m.player_inventory():
        if item.item and name_substring.lower() in item.item.lower():
            return item.slot
    return None


def get_arrow_count():
    count = 0
    for item in m.player_inventory():
        if item.item and "arrow" in item.item.lower():
            count += item.count
    return count


def equip_shield_to_offhand():
    shield_slot = get_slot_by_name("shield")
    if shield_slot is not None and shield_slot < 9:
        m.player_inventory_select_slot(shield_slot)
        time.sleep(0.2)
        m.player_press_swap_hands(True)
        time.sleep(0.1)
        m.player_press_swap_hands(False)
        time.sleep(0.2)
        m.echo("Shield successfully equipped to offhand.")


# --- Main Logic ---

def main():
    wait_for_start()
    equip_shield_to_offhand()

    # State machine tracking
    state = "IDLE"
    state_start_time = 0.0
    last_attack_time = 0.0
    attack_is_pressed = False
    shield_disable_time = 0.0  # Time when we last hit them with an Axe

    # Terrain / Stuck detection tracking
    last_pos = m.player().position
    last_pos_check_time = time.time()
    stuck_ticks = 0

    # Target velocity tracking for prediction
    opponent_last_pos = None
    opponent_last_time = time.time()

    while True:
        me = m.player()
        if not me or me.health <= 0:
            m.echo("Bot died or game ended.")
            release_all_keys()
            break

        # Locate the nearest opponent
        opponent = None
        min_dist = 999.0
        for p in m.players(sort="nearest", limit=5):
            if p.uuid != me.uuid:
                d = distance3d(me.position, p.position)
                if d < min_dist:
                    min_dist = d
                    opponent = p

        if not opponent:
            release_all_keys()
            time.sleep(0.1)
            continue

        target_pos = opponent.position
        dist = distance3d(me.position, target_pos)

        # --- TARGET VELOCITY CALCULATION ---
        current_time = time.time()
        dt = current_time - opponent_last_time
        target_vel = [0, 0, 0]

        if opponent_last_pos and dt > 0:
            target_vel = [
                (target_pos[0] - opponent_last_pos[0]) / dt,
                (target_pos[1] - opponent_last_pos[1]) / dt,
                (target_pos[2] - opponent_last_pos[2]) / dt
            ]

        opponent_last_pos = target_pos
        opponent_last_time = current_time

        # --- DYNAMIC INVENTORY CHECKS ---
        arrows_remaining = get_arrow_count()
        sword_slot = get_slot_by_name("sword")
        axe_slot = get_slot_by_name("axe")
        bow_slot = get_slot_by_name("bow")

        # --- TERRAIN / STUCK DETECTION ---
        if current_time - last_pos_check_time > 0.25:
            if state == "MELEE" and distance2d(me.position, last_pos) < 0.6:
                stuck_ticks += 1
            else:
                stuck_ticks = 0

            last_pos = me.position
            last_pos_check_time = current_time

        # --- WEAPON SELECTION & COOLDOWNS ---
        # If it's been > 5 seconds since our last axe hit, open with the Axe to disable their shield.
        use_axe = (current_time > shield_disable_time) and (axe_slot is not None)
        active_weapon_slot = axe_slot if use_axe else sword_slot
        weapon_cooldown = 1.0 if use_axe else 0.65  # Diamond Axe = 1.0s, Diamond Sword = 0.625s

        # --- STATE EXECUTIONS ---

        # 1. MELEE COMBAT & CHASING
        if dist < 6.0 or arrows_remaining == 0:

            if state == "CHARGING_BOW":
                m.player_press_use(False)

            state = "MELEE"
            if active_weapon_slot is not None:
                m.player_inventory_select_slot(active_weapon_slot)

            # Aim predicting movement
            aim_at_predicted(target_pos, target_vel, is_bow=False, dist=dist)

            m.player_press_forward(True)
            m.player_press_sprint(True)

            # --- Anti-stuck Escape Maneuver ---
            if stuck_ticks > 1:
                m.player_press_left(True)
                m.player_press_right(False)
            else:
                # --- Movement & Dodging Logic ---
                if dist > 3.0:
                    # Chase mode: Full speed straight ahead
                    m.player_press_left(False)
                    m.player_press_right(False)
                    m.player_press_jump(True)
                else:
                    # Strike zone: Weave to dodge counter-attacks
                    dodge_logic()
                    m.player_press_jump(True)

            # --- Attack & Shield Parry Logic ---
            if dist <= 3.2:
                time_since_attack = current_time - last_attack_time

                # If weapon is fully charged -> Attack
                if time_since_attack > weapon_cooldown:
                    m.player_press_use(False)  # Ensure shield is down
                    m.player_press_attack(True)
                    attack_is_pressed = True
                    last_attack_time = current_time

                    if use_axe:
                        shield_disable_time = current_time + 5.0  # Mark their shield as disabled
                else:
                    # Release attack click immediately after swinging
                    if attack_is_pressed:
                        m.player_press_attack(False)
                        attack_is_pressed = False

                    # --- Active Shielding (Parry) ---
                    # Raise shield 0.15s after attacking, drop it 0.15s before the next attack.
                    # This absorbs incoming hits but guarantees our next swing/jump isn't slowed down.
                    if 0.15 < time_since_attack < (weapon_cooldown - 0.15):
                        m.player_press_use(True)
                    else:
                        m.player_press_use(False)
            else:
                # If they are out of reach, do NOT block (blocking slows us down and ruins the chase)
                m.player_press_use(False)
                if attack_is_pressed:
                    m.player_press_attack(False)
                    attack_is_pressed = False

        # 2. RANGED COMBAT (Bow)
        else:
            if attack_is_pressed:
                m.player_press_attack(False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        m.echo(f"Bot encountered an error: {e}")
        release_all_keys()