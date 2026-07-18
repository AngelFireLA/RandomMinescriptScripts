import math
import time
from math import sin, cos, pi, floor, ceil

from minescript import echo_json, ItemStack, player_inventory, container_get_items
import minescript as m
from minescript_plus import Inventory, lib_nbt_module, Screen, _get_nbt
import camera
import pathfinding

def setup_baritone():
    # Disable breaking blocks to clear a path
    m.chat("#allowBreak false")
    # Disable placing blocks (bridges/pillars) to cross gaps
    m.chat("#allowPlace false")
    # Allow parkour (jumping gaps)
    m.chat("#allowParkour true")
    # Reduce chat spam
    m.chat("#chatControl false")
    m.chat("#allowWalkOnBottomSlab true")
    m.chat("#jumpPenalty 0")
    m.chat("allowDiagonalDescend true")

setup_baritone()

def find_items(item_id: str, cust_name: str = "", container: bool = False, try_open: bool = False) -> int | None:
    """
    Finds the first inventory slot containing a specific item, optionally by matching a custom name, and optionally by
    searching an already opened container, or attempting to open a targeted one.
    Args:
        item_id (str): The ID of the item to search for.
        cust_name (str, optional): The custom name to match. If empty, only the item ID is considered. Defaults to "".
        container (bool, optional): If True, searches in the currently open container instead of the player's inventory. Defaults to False.
        try_open (bool, optional): If True and container is True, attempts to open the targeted chest before searching. Defaults to False.
    Returns:
        int | None: The slot ID of the first matching item, or None if not found.
    Notes:
        If try_open is True, then the function will close it after getting the items.
        Slot IDs:
            Player inventory: hotbar = 0-8, main = 9-35, offhand = 40, boots, leggins, chestplate, helmet = 36-39
            Single chest / Trap chest / Ender chest / Shulker box: 0-26
            Double chest: 0-53
            If you need to access the player's main inventory or hotbar with an open container, you must add the
            container's size to the slot IDs. For example, if you have an open double chest, its size is 54 slots,
            then the hotbar slots IDs will be from 0+54=54 to 8+54=62, and the main inventory will be from 9+54=63
            to 35+54=89.
    """
    if not lib_nbt_module:
        print("Error: lib_nbt module not found.")
        echo_json([
            {"text": "You can "},
            {"text": "download it from here", "underlined": True, "color": "#224488",
             "click_event": {"action": "open_url", "url": "https://minescript.net/sdm_downloads/lib_nbt-v1"},
             "hover_event": {"action": "show_text", "value": "https://minescript.net/sdm_downloads/lib_nbt-v1"}},
            {"text": ", and put it in the "},
            {"text": "/minescript", "bold": True},
            {"text": " folder."}
        ])
        return

    if not container:
        items: list[ItemStack] = player_inventory()
    else:
        if try_open:
            if not Inventory.open_targeted_chest():
                return None
        items: list[ItemStack] = container_get_items()
        if try_open:
            Screen.close_screen()
    if items is None:
        # return None
        raise Exception("Error: You need an open container.")  # pylint: disable=W0719

    fi = filter(lambda x: x.item == item_id, items)


    slots = []
    for it in fi:
        if cust_name == "":
            slots.append(it.slot)
        else:
            nbt: dict | None = _get_nbt(it.nbt)
            if nbt is not None and "components" in nbt:
                comp = nbt.get("components")
                if "minecraft:custom_name" in comp and comp.get("minecraft:custom_name") == cust_name:  # type: ignore
                    slots.append(it.slot)

    return None if not slots else slots

def find_items_containing(partial_item_id: str, cust_name: str = "", container: bool = False, try_open: bool = False) -> int | None:
    """
    Finds the first inventory slot containing a specific item, optionally by matching a custom name, and optionally by
    searching an already opened container, or attempting to open a targeted one.
    Args:
        item_id (str): The ID of the item to search for.
        cust_name (str, optional): The custom name to match. If empty, only the item ID is considered. Defaults to "".
        container (bool, optional): If True, searches in the currently open container instead of the player's inventory. Defaults to False.
        try_open (bool, optional): If True and container is True, attempts to open the targeted chest before searching. Defaults to False.
    Returns:
        int | None: The slot ID of the first matching item, or None if not found.
    Notes:
        If try_open is True, then the function will close it after getting the items.
        Slot IDs:
            Player inventory: hotbar = 0-8, main = 9-35, offhand = 40, boots, leggins, chestplate, helmet = 36-39
            Single chest / Trap chest / Ender chest / Shulker box: 0-26
            Double chest: 0-53
            If you need to access the player's main inventory or hotbar with an open container, you must add the
            container's size to the slot IDs. For example, if you have an open double chest, its size is 54 slots,
            then the hotbar slots IDs will be from 0+54=54 to 8+54=62, and the main inventory will be from 9+54=63
            to 35+54=89.
    """
    if not lib_nbt_module:
        print("Error: lib_nbt module not found.")
        echo_json([
            {"text": "You can "},
            {"text": "download it from here", "underlined": True, "color": "#224488",
             "click_event": {"action": "open_url", "url": "https://minescript.net/sdm_downloads/lib_nbt-v1"},
             "hover_event": {"action": "show_text", "value": "https://minescript.net/sdm_downloads/lib_nbt-v1"}},
            {"text": ", and put it in the "},
            {"text": "/minescript", "bold": True},
            {"text": " folder."}
        ])
        return

    if not container:
        items: list[ItemStack] = player_inventory()
    else:
        if try_open:
            if not Inventory.open_targeted_chest():
                return None
        items: list[ItemStack] = container_get_items()
        if try_open:
            Screen.close_screen()
    if items is None:
        # return None
        raise Exception("Error: You need an open container.")  # pylint: disable=W0719

    fi = filter(lambda x: partial_item_id in x.item, items)


    slots = []
    for it in fi:
        if cust_name == "":
            slots.append(it.slot)
        else:
            nbt: dict | None = _get_nbt(it.nbt)
            if nbt is not None and "components" in nbt:
                comp = nbt.get("components")
                if "minecraft:custom_name" in comp and comp.get("minecraft:custom_name") == cust_name:  # type: ignore
                    slots.append(it.slot)

    return None if not slots else slots

def count_total_containing(inventory: list[ItemStack], partial_item_id: int) -> int:
    """
    Counts the total number of items with a specific item ID in the given inventory.

    Args:
        inventory (list[ItemStack]): A list of ItemStack objects representing the inventory.
        item_id (int): The ID of the item to count.

    Returns:
        int: The total count of items with the specified item ID in the inventory.
    """
    return sum(stack.count for stack in inventory if partial_item_id in stack.item)

RAD_FACTOR = pi / 180.0

def fast_trig_loop(yaw):
    return sin(yaw*RAD_FACTOR), cos(yaw*RAD_FACTOR)

def get_relative_region(forward=7, back=2, side=3,
                     up=3, down=1):
    x, y, z = m.player_position()
    sin_yaw, cos_yaw = fast_trig_loop(m.player_orientation()[0])

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


def get_relative_coords(yaw, forward=0, side=0, up=0, player_coords=None):
    x, y, z = m.player_position() if not player_coords else player_coords
    yaw_rad = math.radians(yaw)

    # Standard Minecraft rotation matrix
    dx_forward = -math.sin(yaw_rad) * forward
    dz_forward = math.cos(yaw_rad) * forward

    dx_side = -math.cos(yaw_rad) * side
    dz_side = -math.sin(yaw_rad) * side

    # FIX 2: Round the offsets to nearest integer immediately.
    # Since we are placing blocks on a grid, we don't want partial floats like 0.999 or 0.0001
    final_dx = round(dx_forward + dx_side)
    final_dz = round(dz_forward + dz_side)

    new_x = x + final_dx
    new_y = y + up
    new_z = z + final_dz

    # Return integers
    return floor(new_x), floor(new_y), floor(new_z)

def quick_use():
    m.player_press_use(True)
    time.sleep(0.05)
    m.player_press_use(False)

def place_block(target_coords=None, building_block="wool"):
    yaw = m.player_orientation()[0]
    if not target_coords:
        target_coords = get_relative_coords(yaw, forward=2, side=0)
    if "air" not in m.get_block(*target_coords):
        return

    original_building_block = building_block
    building_block = None
    for item in m.player_inventory():
        if original_building_block in item.item:
            building_block = item.item
            print("Using building block:", building_block)
            break

    if building_block is None:
        print(f"Error: No {original_building_block} found in inventory.")
        return

    m.chat(f"#sel clear")
    time.sleep(0.05)
    m.chat(f"#sel 1 {target_coords[0]} {target_coords[1]} {target_coords[2]}")
    time.sleep(0.05)
    m.chat(f"#sel 2 {target_coords[0]} {target_coords[1]} {target_coords[2]}")
    time.sleep(0.05)
    m.chat(f"#sel set {building_block}")
    for i in range(500):
        time.sleep(0.05)
        if building_block in m.get_block(*target_coords):
            break
    print("Placed block at", target_coords)
