import math
import random
import time
from math import floor, ceil
from threading import Thread

import minescript as m
import minescript_plus
from bridge import eagle_bridge, breezly_bridge, moon_bridge, setup_crosshair
from camera import look_at
from minescript_plus import Keybind, Inventory
from minescript_plus_plus import find_items_containing, count_total_containing, get_relative_region, get_relative_coords, place_block
import pathfinding
print("Bedwars script launched !")
kb = Keybind()

WOOD_TIER = LEATHER_TIER = 1
STONE_TIER = CHAINMAIL_TIER = 2
IRON_TIER = 3
DIAMOND_TIER = 4

item_prices = {
    "wool": {"iron_ingot": 4, "gold_ingot": 0, "emerald": 0},
    "stone_sword": {"iron_ingot": 10, "gold_ingot": 0, "emerald": 0},
    "iron_sword": {"iron_ingot": 0, "gold_ingot": 7, "emerald": 0},
    "diamond_sword": {"iron_ingot": 0, "gold_ingot": 0, "emerald": 4},
    "end_stone": {"iron_ingot": 24, "gold_ingot": 0, "emerald": 0},
    "golden_apple": {"iron_ingot": 0, "gold_ingot": 3, "emerald": 0},
    "fireball": {"iron_ingot": 40, "gold_ingot": 0, "emerald": 0},
    "chainmail_boots": {"iron_ingot": 40, "gold_ingot": 0, "emerald": 0}
}

class Bot(Thread):
    def __init__(self):
        super().__init__()
        self.ressources = {"gold_ingot": 0, "iron_ingot":0, "diamond":0, "emerald":0}
        self.sword_tier = WOOD_TIER
        self.armor_tier = LEATHER_TIER
        self.x, self.y, self.z = m.player_position()
        self.generator_pos: tuple = None
        self.bed_pos: dict = {"head": [], "foot": []}
        self.shop_pos: tuple[int] = None
        self.upgrades_pos: tuple = None
        self.spawn_pos: tuple = None
        self.bed_prot_pos: dict = {}
        self.update()

    @staticmethod
    def get_bed_pos():
        bed_pos_dict = {"head": [], "foot": []}
        pos1, pos2 = get_relative_region(20, 5, 5, 5, 2)
        block_region = m.get_block_region(pos1, pos2)
        for x in range(pos1[0], pos2[0] + 1):
            for y in range(pos1[1], pos2[1] + 1):
                for z in range(pos1[2], pos2[2] + 1):
                    block = block_region.get_block(x, y, z)
                    if block is not None and "bed" in block:
                        print("Bed found at", (x, y, z), block)
                        bed_pos_dict[block[-5:-1]] = (x, y, z)
        return bed_pos_dict

    @staticmethod
    def get_npc_pos(entities):
        shop_pos = []
        upgrades_pos = []
        for entity in entities[:]:
            if entity.type == "entity.minecraft.armor_stand":
                entities.remove(entity)
                if "Upgrades" in entity.name:
                    print("Upgrades NPC found at", entity.position)
                    upgrades_pos = entity.position
                    upgrades_pos[1] = ceil(upgrades_pos[1]) - 0.4
                elif "Shop" in entity.name:
                    print("Shop NPC found at", entity.position)
                    shop_pos = entity.position
                    shop_pos[1] = ceil(shop_pos[1]) - 0.4
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
        for i in range(1, layer+1):
            new_prot_coords = []
            relative_blocks_to_head = []
            relative_blocks_to_bottom = []
            for forward in range(-i, i + 1):
                for side in range(-i, i + 1):
                    for up in range(0, i+1):
                        if (forward == 0 and side == 0 and up == 0) or (abs(forward) + abs(side) + abs(up) > i):
                            continue
                        if forward >= 0:
                            relative_blocks_to_head.append((forward, side, up))
                        if forward <= 0:
                            relative_blocks_to_bottom.append((forward, side, up))


            for rel_block in relative_blocks_to_head:
                absolute_coords = get_relative_coords(yaw, *rel_block, player_coords=self.bed_pos["head"])
                floored_abs_coords = (floor(absolute_coords[0]), floor(absolute_coords[1]), floor(absolute_coords[2]))
                if floored_abs_coords not in prot_coords: new_prot_coords.append(floored_abs_coords)
            for rel_block in relative_blocks_to_bottom:
                absolute_coords = get_relative_coords(yaw, *rel_block, player_coords=self.bed_pos["foot"])
                floored_abs_coords = (floor(absolute_coords[0]), floor(absolute_coords[1]), floor(absolute_coords[2]))
                if floored_abs_coords not in prot_coords: prot_coords.append(floored_abs_coords)
            new_prot_coords.sort(key=lambda x: x[1])
            prot_coords.extend(new_prot_coords)
        return prot_coords

    def update_ressources(self):
        player_inv = m.player_inventory()
        for ressource in self.ressources:
            self.ressources[ressource] = count_total_containing(player_inv, ressource)

    def buy(self, item_name: str = "wool", amount: int = 1):

        for ressource in self.ressources:
            if self.ressources[ressource] < item_prices[ressource]:
                print("Not enough", ressource)
                return

        screen_name = m.screen_name()
        if screen_name is None or "Shop" not in screen_name:
            path = pathfinding.path_find((self.x, self.y, self.z), self.shop_pos, closest_if_fail=True)
            pathfinding.path_walk_to(path=path)
            look_at(*self.shop_pos)
            m.player_press_use(True)
            time.sleep(0.05)
            m.player_press_use(False)
            time.sleep(0.5)
            screen_name = m.screen_name()
        if screen_name is None or "Shop" not in screen_name:
            m.player_press_forward(True)
            time.sleep(0.1)
            m.player_press_forward(False)
            look_at(*self.shop_pos)
            m.player_press_use(True)
            time.sleep(0.05)
            m.player_press_use(False)
            time.sleep(0.5)
            screen_name = m.screen_name()
        if screen_name is None or "Shop" not in screen_name:
            print("Failed to get in the shop")
            return
        else:
            item_slot = find_items_containing(item_name, container=True)["wool" in item_name or "tnt" in item_name]
            if item_slot is  None:
                print("Couldn't find the item")
                return

            for i in range(amount):
                Inventory.click_slot(item_slot)
                time.sleep(0.15)

    def place_protection(self):
        for coord in self.bed_prot_pos[1]:
            if "air" not in m.getblock(coord[0], coord[1], coord[2]):
                print(m.getblock(coord[0], coord[1], coord[2]))
                continue
            place_block(target_coords=coord)

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
        if 1 not in self.bed_prot_pos:
            self.bed_prot_pos[1] = self.get_bed_prot_coords(2)
        self.update_ressources()

    def run(self):
        print("Started")
        #self.wait_for_start_of_game()
        time.sleep(1)
        while True:
            self.update()
            time.sleep(0.05)

    def move_to_generator(self):
        c_x, c_y, c_z = m.player_position()
        path = pathfinding.path_find((c_x, c_y, c_z), self.generator_pos, closest_if_fail=True)
        pathfinding.path_walk_to(path=path, )
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

