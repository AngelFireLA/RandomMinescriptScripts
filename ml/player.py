import minescript
import minescript as m
from math import pi, sin, cos, floor
RAD_FACTOR = pi / 180.0


def fast_trig_loop(yaw):
    return sin(yaw*RAD_FACTOR), cos(yaw*RAD_FACTOR)

def get_block_category(block_name):
    if block_name == "minecraft:air":
        return 0
    if "fence" in block_name or "wall" in block_name:
        return 1
    if "ice" in block_name:
        return 2
    if "slime" in block_name:
        return 3
    if "ladder" in block_name:
        return 4
    if "trapdoor" in block_name:
        return 5
    if "slab" in block_name:
        return 6
    if "bars" in block_name:
        return 7
    return 8

from math import floor, ceil

def region_pos1_pos2(x, y, z, sin_yaw, cos_yaw,
                     forward=7, back=2, side=3,
                     up=3, down=1):
    """
    Local box:
      forward in [-back, +forward]
      strafe  in [-side, +side]
      vertical in [-down, +up]

    Returns pos1, pos2 as integer BlockPos corners for get_block_region.
    """

    # Local corners in (forward, strafe)
    local_corners = [
        (-back, -side),
        (-back, +side),
        (+forward, -side),
        (+forward, +side),
    ]

    xs = []
    zs = []
    for f, s in local_corners:
        dx = cos_yaw * s - sin_yaw * f
        dz = sin_yaw * s + cos_yaw * f
        xs.append(x + dx)
        zs.append(z + dz)

    min_x = floor(min(xs))
    max_x = ceil(max(xs))
    min_z = floor(min(zs))
    max_z = ceil(max(zs))

    min_y = floor(y - down)
    max_y = ceil(y + up)

    pos1 = (min_x, min_y, min_z)
    pos2 = (max_x, max_y, max_z)
    return pos1, pos2


class Player:
                    # f, b, s, u, d
    region_around = (7, 1, 5, 2, 1)

    def __init__(self):
        self.forward_dist = 0
        self.strafe_dist = 0
        self.vertical_dist = 0

        self.vel_forward = 0
        self.vel_vertical = 0
        self.vel_strafe = 0

        self.yaw = [] # sin(yaw), cos(yaw)
        self.update_yaw_pitch()
        self.dist_xz = 0
        self.current_standing_block = "minecraft:air"
        self.standing_block_category = 0
        self.is_grounded = False
        self.data_region_around = []

        self.ticks_since_jump = 0
        # is forward, is left, is right, is backwards, is sprint, is sneak, is jump
        self.last_action = [False, False, False]
        #self.last_action = [False, False, False, False, False]




    def update_yaw_pitch(self):
        yaw = m.player_orientation()[0]
        self.yaw = fast_trig_loop(yaw)

    def standing_block(self, changed_y=None):
        x, y, z = m.player_position()
        y += 1
        if changed_y is not None:
            y = changed_y
        block_under = m.getblock(floor(x), floor(y - 1), floor(z))
        x_change = 0
        z_change = 0
        if "air" in block_under:
            if x >= 0:
                new_x = x % 1
                if 0 <= new_x <= 0.3:
                    x_change = -0.4
                elif 0.7 <= new_x <= 1:
                    x_change = 0.4
            else:
                new_x = abs(x) % 1
                if 0 <= new_x <= 0.3:
                    x_change = 0.4
                elif 0.7 <= new_x <= 1:
                    x_change = -0.4
            if z >= 0:
                new_z = z % 1
                if 0 <= new_z <= 0.3:
                    z_change = -0.4
                elif 0.7 <= new_z <= 1:
                    z_change = 0.4
            else:
                new_z = abs(z) % 1
                if 0 <= new_z <= 0.3:
                    z_change = 0.4
                elif 0.7 <= new_z <= 1:
                    z_change = -0.4
            block_under = m.getblock(floor(x + x_change), floor(y - 1), floor(z + z_change))
            if "air" in block_under:
                block_under = m.getblock(floor(x), floor(y - 1), floor(z + z_change))
                if "air" in block_under:
                    block_under = m.getblock(floor(x + x_change), floor(y - 1), floor(z))
        abs_y_1 = abs(y) % 1
        if abs_y_1 in [0.5, 0] and "air" in block_under and changed_y is None:
            block_under = self.standing_block(y - 1)
        return block_under

    def is_on_ground(self):
        abs_y = abs(m.player_position()[1]) % 1
        return (abs_y < 0.1 or 0.4 < abs_y < 0.6) and "air" not in self.current_standing_block

    def recalc_coords(self, new_checkpoint):
        c_x, c_y, c_z = new_checkpoint
        x, y, z = m.player_position()
        dx = c_x - x
        dy = c_y - y
        dz = c_z - z

        sin_yaw, cos_yaw = self.yaw
        self.forward_dist = dz * cos_yaw - dx * sin_yaw
        self.strafe_dist = dz * sin_yaw + dx * cos_yaw
        self.vertical_dist = dy
        self.dist_xz = (dx**2 + dz**2)**0.5

    def update_velocity(self):
        vx, vy, vz = m.player().velocity
        self.vel_vertical = vy
        sin_yaw, cos_yaw = self.yaw
        self.vel_forward = vz * cos_yaw - vx * sin_yaw
        self.vel_strafe = vz * sin_yaw + vx * cos_yaw

    def get_region_around(self):
        x, y, z = m.player_position()
        sin_yaw, cos_yaw = self.yaw

        pos1, pos2 = region_pos1_pos2(
            x, y, z, sin_yaw, cos_yaw, *self.region_around
        )

        region = m.get_block_region(pos1, pos2)
        return region

    def convert_region_to_data(
            self,
            region=None,
            one_hot=True,
            num_categories=9,
    ):
        """
        Samples a yaw-aligned local grid around the player and returns a flat feature list.

        Ordering (deterministic):
          for f in [-back .. +forward]:
            for s in [-side .. +side]:
              for v in [-down .. +up]:
                append features for that cell

        If one_hot=True: appends num_categories floats per cell.
        Else: appends one int category per cell.
        """
        forward, back, side, up, down = self.region_around
        # Ensure yaw is available
        if not self.yaw:
            self.update_yaw_pitch()

        sin_yaw, cos_yaw = self.yaw

        # Fetch region if not provided (this is the world-aligned AABB container)
        if region is None:
            region = self.get_region_around()

        # Player world position (float)
        x0, y0, z0 = m.player_position()

        data = []

        # Local -> world mapping consistent with your forward/strafe formulas:
        # forward = dz*cos - dx*sin
        # strafe  = dz*sin + dx*cos
        #
        # Inverse (local -> world):
        # dx =  cos*strafe - sin*forward
        # dz =  sin*strafe + cos*forward
        for f in range(-back, forward + 1):
            for s in range(-side, side + 1):

                dx = (cos_yaw * s) - (sin_yaw * f)
                dz = (sin_yaw * s) + (cos_yaw * f)

                wx = floor(x0 + dx)
                wz = floor(z0 + dz)

                for v in range(-down, up + 1):

                    wy = floor(y0 + v)

                    # Fast lookup from the already-fetched region (no new world query)
                    try:
                        block_name = region.get_block(wx, wy, wz)
                    except:
                        block_name = "minecraft:air"
                    cat = get_block_category(block_name) if block_name is not None else 0
                    if one_hot:
                        # One-hot encode
                        for k in range(num_categories):
                            data.append(1.0 if k == cat else 0.0)
                    else:
                        data.append(cat)

        return data

    def update_standing_block(self):
        self.current_standing_block = self.standing_block()
        self.standing_block_category = get_block_category(self.current_standing_block)
