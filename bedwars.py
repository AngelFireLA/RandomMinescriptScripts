import math
import random
import time
from math import floor, ceil
from threading import Thread

import minescript as m
import minescript_plus
from bridge import eagle_bridge, breezly_bridge, moon_bridge, setup_crosshair
from camera import look_at, look
from minescript_plus import Keybind, Inventory
from minescript_plus_plus import find_items_containing, count_total_containing, get_relative_region, get_relative_coords, place_block
print("Bedwars script launched !")
kb = Keybind()

WOOD_TIER = LEATHER_TIER = 1
STONE_TIER = CHAINMAIL_TIER = 2
IRON_TIER = 3
DIAMOND_TIER = 4

item_prices = {
    "wool": {"iron_ingot": 4, "gold_ingot": 0, "emerald": 0, "quantity": 16},
    "stone_sword": {"iron_ingot": 10, "gold_ingot": 0, "emerald": 0},
    "iron_sword": {"iron_ingot": 0, "gold_ingot": 7, "emerald": 0},
    "diamond_sword": {"iron_ingot": 0, "gold_ingot": 0, "emerald": 4},
    "end_stone": {"iron_ingot": 24, "gold_ingot": 0, "emerald": 0, "quantity": 24},
    "golden_apple": {"iron_ingot": 0, "gold_ingot": 3, "emerald": 0},
    "fireball": {"iron_ingot": 40, "gold_ingot": 0, "emerald": 0},
    "chainmail_boots": {"iron_ingot": 40, "gold_ingot": 0, "emerald": 0},
    "oak_planks": {"iron_ingot": 0, "gold_ingot": 4, "emerald": 0, "quantity": 16}
}

bed_layers_block = {1:"end_stone", 2:"oak_planks", 3:"wool"}

class Bot(Thread):
    def __init__(self):
        super().__init__()
        self.ressources = {"gold_ingot": 0, "iron_ingot":0, "diamond":0, "emerald":0}
        self.inventory = {}
        self.sword_tier = WOOD_TIER
        self.armor_tier = LEATHER_TIER
        self.x, self.y, self.z = m.player_position()
        self.generator_pos: tuple = None
        self.bed_pos: dict = {"head": [], "foot": []}
        self.shop_pos: tuple[int] = None
        self.upgrades_pos: tuple = None
        self.spawn_pos: tuple = None
        self.bed_prot_pos: dict = {}
        self.bed_prot_status = []
        #self.update()

    def smart_move(self, x, y, z):
        y = floor(y)

        m.chat("#cancel")
        time.sleep(0.05)
        # Using goal + path is often more stable than goto for scripts
        m.chat(f"#goto {x} {y} {z}")
        curr_pos = m.player_position()
        distance = math.sqrt((curr_pos[0] - x) ** 2 + (curr_pos[1] - y) ** 2 + (curr_pos[2] - z) ** 2)
        # while the player is more than a block away from the target, we wait
        while distance > 0.5:
            time.sleep(0.05)
            curr_pos = m.player_position()
            distance = math.sqrt((curr_pos[0] - x) ** 2 + (curr_pos[1] - y) ** 2 + (curr_pos[2] - z) ** 2)
        m.chat("#cancel")

    @staticmethod
    def get_bed_pos():
        bed_pos_dict = {"head": [], "foot": []}
        pos1, pos2 = get_relative_region(25, 5, 5, 5, 4)
        block_region = m.get_block_region(pos1, pos2)
        for x in range(pos1[0], pos2[0] + 1):
            for y in range(pos1[1], pos2[1] + 1):
                for z in range(pos1[2], pos2[2] + 1):
                    block = block_region.get_block(x, y, z)
                    if block is not None and "bed" in block and "rock" not in block:
                        print("Bed found at", (x, y, z), block)
                        bed_pos_dict[block[-5:-1]] = (x, y, z)
        return bed_pos_dict

    @staticmethod
    def get_npc_pos(entities):
        shop_pos_armor_stand = []
        upgrades_armor_stand = []
        villagers = []
        for entity in entities[:]:
            if entity.type == "entity.minecraft.armor_stand":
                entities.remove(entity)
                if "Upgrades" in entity.name:
                    print("Upgrades armor stand found at", entity.position)
                    upgrades_armor_stand = entity.position
                elif "Shop" in entity.name:
                    print("Shop armor stand found at", entity.position)
                    shop_pos_armor_stand = entity.position
            elif entity.type == "entity.minecraft.villager":
                villagers.append(entity)
        # find the closest villager of both armor stands and assign their position to the corresponding npc
        closest_shop_villager = None
        closest_upgrades_villager = None
        closest_to_shop_distance = float("inf")
        closest_to_upgrades_distance = float("inf")
        for villager in villagers:
            if shop_pos_armor_stand:
                distance_to_shop = math.sqrt((villager.position[0] - shop_pos_armor_stand[0]) ** 2 + (villager.position[1] - shop_pos_armor_stand[1]) ** 2 + (villager.position[2] - shop_pos_armor_stand[2]) ** 2)
                if distance_to_shop < closest_to_shop_distance:
                    closest_to_shop_distance = distance_to_shop
                    closest_shop_villager = villager
            if upgrades_armor_stand:
                distance_to_upgrades = math.sqrt((villager.position[0] - upgrades_armor_stand[0]) ** 2 + (villager.position[1] - upgrades_armor_stand[1]) ** 2 + (villager.position[2] - upgrades_armor_stand[2]) ** 2)
                if distance_to_upgrades < closest_to_upgrades_distance:
                    closest_to_upgrades_distance = distance_to_upgrades
                    closest_upgrades_villager = villager
        if closest_shop_villager:
            shop_pos = list(closest_shop_villager.position)
            yaw_rad = math.radians(closest_shop_villager.yaw)
            shop_pos[0] = floor(shop_pos[0] - 3 * math.sin(yaw_rad))
            shop_pos[1] = floor(shop_pos[1]) + 1
            shop_pos[2] = floor(shop_pos[2] + 3 * math.cos(yaw_rad))
            print("Shop pos (3 blocks in front of villager):", shop_pos)
        else:
            print("Shop villager not found, using armor stand position", shop_pos_armor_stand)
            shop_pos = shop_pos_armor_stand
        if closest_upgrades_villager:
            upgrades_pos = list(closest_upgrades_villager.position)
            yaw_rad = math.radians(closest_upgrades_villager.yaw)
            upgrades_pos[0] = floor(upgrades_pos[0] - 3 * math.sin(yaw_rad))
            upgrades_pos[1] = floor(upgrades_pos[1])
            upgrades_pos[2] = floor(upgrades_pos[2] + 3 * math.cos(yaw_rad))
            print("Upgrades pos (3 blocks in front of villager):", upgrades_pos)
        else:
            print("Upgrades villager not found, using armor stand position", upgrades_armor_stand)
            upgrades_pos = upgrades_armor_stand
        return shop_pos, upgrades_pos

    @staticmethod
    def get_generator_pos(entities):
        entities = [entity for entity in entities if entity.type == "entity.minecraft.item"]
        iron_ingots = [entity.position for entity in entities if entity.name == "Iron Ingot"]
        if iron_ingots:
            iron_ingots.sort(key=lambda x: x[1])
            print("Generator found at", iron_ingots[0])
            return iron_ingots[0][0], ceil(iron_ingots[0][1]), iron_ingots[0][2]
        else:
            print("Generator not found")
            return []

    def get_bed_prot_coords(self, layer=2):
        head_x, _, head_z = self.bed_pos["head"]
        foot_x, _, foot_z = self.bed_pos["foot"]

        dx = head_x - foot_x
        dz = head_z - foot_z

        yaw = math.degrees(math.atan2(-dx, dz))
        prot_coords = []
        for i in range(1, layer + 1):
            new_prot_coords = []
            relative_blocks_to_head = []
            relative_blocks_to_bottom = []
            for forward in range(-i, i + 1):
                for side in range(-i, i + 1):
                    for up in range(0, i + 1):
                        if (forward == 0 and side == 0 and up == 0) or (abs(forward) + abs(side) + abs(up) > i):
                            continue
                        if forward >= 0:
                            relative_blocks_to_head.append((forward, side, up))
                        if forward <= 0:
                            relative_blocks_to_bottom.append((forward, side, up))

            for rel_block in relative_blocks_to_head:
                absolute_coords = get_relative_coords(yaw, *rel_block, player_coords=self.bed_pos["head"])
                floored_abs_coords = (floor(absolute_coords[0]), floor(absolute_coords[1]), floor(absolute_coords[2]))
                if floored_abs_coords not in prot_coords and floored_abs_coords not in new_prot_coords:
                    new_prot_coords.append(floored_abs_coords)
            for rel_block in relative_blocks_to_bottom:
                absolute_coords = get_relative_coords(yaw, *rel_block, player_coords=self.bed_pos["foot"])
                floored_abs_coords = (floor(absolute_coords[0]), floor(absolute_coords[1]), floor(absolute_coords[2]))
                if floored_abs_coords not in prot_coords and floored_abs_coords not in new_prot_coords:
                    new_prot_coords.append(floored_abs_coords)

            # # First, sort all blocks in this layer by their y coordinate
            # new_prot_coords.sort(key=lambda x: x[1])

            # Group blocks by their y coordinate (height)
            height_groups = {}
            for coord in new_prot_coords:
                y_value = 1
                if y_value not in height_groups:
                    height_groups[y_value] = []
                height_groups[y_value].append(coord)

            # For each height group, sort the blocks by distance to the first block in that group
            # This makes placement more efficient by keeping the bot close to where it last placed
            sorted_new_prot_coords = []
            for y_value in sorted(height_groups.keys()):
                group = height_groups[y_value]
                if len(group) <= 1:
                    # No need to sort if there's only one block at this height
                    sorted_new_prot_coords.extend(group)
                    continue

                # The first block in the group acts as the reference point
                first_block = group[0]
                remaining_blocks = list(group[1:])

                # Start the sorted list with the first block
                sorted_group = [first_block]

                # Greedily pick the nearest unvisited block each time (nearest-neighbor approach)
                current_block = first_block
                while remaining_blocks:
                    # Calculate the distance from the current block to every remaining block
                    closest_block = None
                    closest_distance = float('inf')
                    for candidate_block in remaining_blocks:
                        # Calculate squared Euclidean distance (no need to sqrt for comparison)
                        distance_squared = (
                                (candidate_block[0] - current_block[0]) ** 2 +
                                (candidate_block[1] - current_block[1]) ** 2 +
                                (candidate_block[2] - current_block[2]) ** 2
                        )
                        if distance_squared < closest_distance:
                            closest_distance = distance_squared
                            closest_block = candidate_block

                    # Add the closest block to the sorted group and remove it from remaining
                    sorted_group.append(closest_block)
                    remaining_blocks.remove(closest_block)
                    # Update the current block to the one we just added
                    current_block = closest_block

                sorted_new_prot_coords.extend(sorted_group)

            prot_coords.extend(sorted_new_prot_coords)
        return prot_coords

    def update_ressources(self):
        player_inv = m.player_inventory()
        for ressource in self.ressources:
            self.ressources[ressource] = count_total_containing(player_inv, ressource)

    def update_inventory(self):
        player_inv = m.player_inventory()
        self.inventory = {}
        for item in item_prices:
            self.inventory[item] = count_total_containing(player_inv, item)

    def has_ressources_for(self, item, quantity=1):
        return all(self.ressources[ressource] >= item_prices[item][ressource]*quantity for ressource in item_prices[item] if ressource not in ["quantity", "diamond"])

    def get_closest_villager(self, starting_pos=None):
        if starting_pos is None:
            starting_pos = m.player_position()
        entities = m.entities(max_distance=20)[:]
        villagers = [entity for entity in entities if entity.type == "entity.minecraft.villager"]
        closest_villager = None
        closest_distance = float("inf")
        for villager in villagers:
            distance = math.sqrt((villager.position[0] - starting_pos[0]) ** 2 + (villager.position[1] - starting_pos[1]) ** 2 + (villager.position[2] - starting_pos[2]) ** 2)
            if distance < closest_distance:
                closest_distance = distance
                closest_villager = villager
        return floor(closest_villager.position[0])+0.5, floor(closest_villager.position[1])+1.2, floor(closest_villager.position[2])+0.5

    def buy(self, item_name: str = "wool", amount: int = 1):

        for ressource in self.ressources:
            if ressource != "diamond" and self.ressources[ressource] < item_prices[item_name][ressource]:
                print("Not enough", ressource)
                return

        screen_name = m.screen_name()
        if screen_name is None or "Shop" not in screen_name:
            print("not in shop")
            distance_to_shop = math.sqrt((self.x - self.shop_pos[0]) ** 2 + (self.y - self.shop_pos[1]) ** 2 + (self.z - self.shop_pos[2]) ** 2)
            if distance_to_shop > 2:
                self.smart_move(*self.shop_pos)
                print("path finded")
            look_at(*self.get_closest_villager())
            look(m.player_orientation()[0], 0)
            m.player_press_use(True)
            time.sleep(0.05)
            m.player_press_use(False)
            time.sleep(0.5)
            print("right clicked")
            screen_name = m.screen_name()
        if screen_name is None or "Shop" not in screen_name:
            print("Failed to get in the shop")
            return
        else:
            item_slot = find_items_containing(item_name, container=True)["wool" in item_name or "tnt" in item_name]
            if item_slot is None:
                print("Couldn't find the item")
                # press escape
                minescript_plus.Screen.close_screen()
                return

            for i in range(amount):
                Inventory.click_slot(item_slot)
                time.sleep(0.15)
            minescript_plus.Screen.close_screen()

    def place_protection(self, prot_layer=3):
        for coord in self.bed_prot_pos[prot_layer]:
            place_block(coord, building_block=bed_layers_block[prot_layer])
            time.sleep(0.05)
        self.bed_prot_status.append(prot_layer)

    @staticmethod
    def wait_for_start_of_game():
        message_to_detect = "Goodluck with your BedWars Game"
        with m.EventQueue() as event_queue:
            event_queue.register_chat_listener()
            while True:
                event = event_queue.get()
                if event.type == m.EventType.CHAT and message_to_detect in event.message:
                    print("Game Starting detected")
                    return

    def update(self):
        self.x, self.y, self.z = m.player_position()
        entities = m.entities(max_distance=20)[:]
        if not self.generator_pos:
            self.generator_pos = self.get_generator_pos(entities)
        if not self.shop_pos or not self.upgrades_pos:
            self.shop_pos, self.upgrades_pos = self.get_npc_pos(entities)
        if not self.bed_pos["head"]:
            self.bed_pos = self.get_bed_pos()
        if not self.spawn_pos:
            self.spawn_pos = self.x, self.y, self.z
        for i in range(1, 4):
            if i not in self.bed_prot_pos:
                self.bed_prot_pos[i] = self.get_bed_prot_coords(i)
        self.update_ressources()
        self.update_inventory()

    def run(self):
        print("Started")
        #self.wait_for_start_of_game()
        time.sleep(2)
        while True:
            self.update()
            self.take_decision()

    def take_decision(self):
        bed_layer = 1
        while bed_layer in self.bed_prot_status and bed_layer < 4:
            bed_layer += 1
        block = bed_layers_block[bed_layer]
        while block in m.getblock(*self.bed_prot_pos[bed_layer][0]):
            print("Bed protection layer", bed_layer, "is already being placed, next layer")
            bed_layer += 1
            block = bed_layers_block[bed_layer]
        if bed_layer < 4:
            print("Bed protection layer", bed_layer, "is not placed yet")
            bed_prot_layer_size = len(self.bed_prot_pos[bed_layer])
            if bed_prot_layer_size > self.inventory[block]:
                quantity_to_buy = ceil((bed_prot_layer_size-self.inventory[block])/item_prices[block]["quantity"])
                print(f"Not enough {block} for bed protection layer {bed_layer}, need to buy {quantity_to_buy} more")
                if not self.has_ressources_for(block, quantity_to_buy):
                    print("Not enough ressources to buy blocks for bed protection layer", bed_layer)
                    self.move_to_generator()
                    return
                print("Buying blocks for bed protection layer", bed_layer)
                self.buy(block, quantity_to_buy)
            else:
                print("enough blocks in inventory for bed protection layer", bed_layer)
                self.place_protection(bed_layer)
        else:
            print("All bed protection layers are placed or in progress")


    def move_to_generator(self):
        self.smart_move(*self.generator_pos)
        print("Done")


def buy_stone_sword():
    if Inventory.find_item("minecraft:stone_sword") is not None:
        return
    if Inventory.count_total(m.player_inventory(), "minecraft:iron_ingot") < 10:
        return
    stone_sword_slot = Inventory.find_item("minecraft:stone_sword", container=True)
    if not stone_sword_slot:
        return
    Inventory.click_slot(stone_sword_slot)
    time.sleep(0.15)

def buy_wool():
    player_inv = m.player_inventory()
    if count_total_containing(player_inv, "wool") >= 48:
        return
    if Inventory.count_total(player_inv, "minecraft:iron_ingot") < 4:
        return
    wool_slots = find_items_containing("wool", container=True)
    if wool_slots is None:
        return
    Inventory.click_slot(wool_slots[1])
    time.sleep(0.15)

def buy_iron_armor():
    if Inventory.find_item("minecraft:iron_boots") is not None:
        return
    if Inventory.count_total(m.player_inventory(), "minecraft:gold_ingot") < 12:
        return
    iron_armor_slot = Inventory.find_item("minecraft:iron_boots", container=True)
    if not iron_armor_slot:
        return
    Inventory.click_slot(iron_armor_slot)
    time.sleep(0.15)

def buy_basic_stuff():
    screen_name = m.screen_name()
    if screen_name is None or "Shop" not in screen_name:
        return

    for i in range(3):
        buy_wool()

    buy_stone_sword()
    buy_iron_armor()



bot = Bot()

kb.set_keybind(320, exit, name="Quit")
kb.set_keybind(321, buy_basic_stuff, name="BuyBasicStuff")
kb.set_keybind(322, eagle_bridge, name="Eagle Bridge")
kb.set_keybind(323, breezly_bridge, name="Breezly Bridge")
kb.set_keybind(325, setup_crosshair, name="Setup crosshair")
kb.set_keybind(327, bot.buy, name="Setup crosshair")
kb.set_keybind(328, bot.place_protection)
kb.set_keybind(329, bot.start, name="Test")


while True:
    time.sleep(1)

