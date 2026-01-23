import random
import time
from math import floor, ceil

import minescript as m
from minescript_plus import Keybind, Inventory
from minescript_plus_plus import find_items_containing, count_total_containing, get_relative_region
import pathfinding
from rotation import look

server_delay = 0.025

def closest_bridging_yaw(yaw, inclined=True):
    while yaw < -180:
        yaw += 360
    while yaw > 180:
        yaw -= 360

    if inclined:
        # Range: 0 to 90 -> 45
        if 0 <= yaw <= 90:
            return 45
        elif 90 < yaw <= 180:
            return 135
        elif -90 <= yaw < 0:
            return -45
        elif -180 <= yaw < -90:
            return -135
    else:
        if -45 <= yaw < 45:
            return 0
        elif 45 <= yaw < 135:
            return 90
        elif yaw >= 135 or yaw < -135:
            return 180
        elif -135 <= yaw < -45:
            return -90

    return yaw

def eagle_bridge():
    screen_name = m.screen_name()
    if screen_name is not None:
        return
    yaw, pitch = m.player_orientation()
    print("Starting Eagle Bridge")
    m.player_inventory_select_slot(1)
    new_yaw = closest_bridging_yaw(yaw)
    look(new_yaw, 78)
    time.sleep(0.3)
    m.player_press_use(True)
    time.sleep(0.05)
    m.player_press_right(True)
    time.sleep(0.05)
    m.player_press_backward(True)
    time.sleep(0.05)
    start_time = time.time()
    m.player_press_sneak(True)
    time.sleep(0.05)
    while time.time() - start_time < 5:
        time.sleep(server_delay)
        m.player_press_use(True)
        time.sleep(server_delay)
        x, y, z = m.player_position()
        if new_yaw == 45:
            z -= 0.4
            x = floor(x)
            y = round(y-1)
            z = round(z)
        elif new_yaw == -45:
            x -= 0.4
            x = round(x)
            y = round(y-1)
            z = floor(z)
        elif new_yaw == -135:
            #z += 0.1
            x = floor(x)
            y = round(y-1)
            z = round(z)
        elif new_yaw == 135:
            #x += 0.1
            x = round(x)
            y = round(y-1)
            z = floor(z)

        block = m.getblock(x, y, z)
        if "wool" in block or "sand" in block:
            m.player_press_sneak(False)
        else:
            m.player_press_sneak(True)


    print("Finished bridging")
    m.player_press_right(False)
    m.player_press_backward(False)
    m.player_press_sneak(False)
    time.sleep(0.1)
    m.player_press_use(False)

def breezly_bridge():
    screen_name = m.screen_name()
    if screen_name is not None:
        return
    yaw, pitch = m.player_orientation()
    print("Starting Breezly Bridge")
    m.player_inventory_select_slot(1)
    new_yaw = closest_bridging_yaw(yaw, inclined=False)
    look(new_yaw, 80.5)
    time.sleep(0.3)
    m.player_press_use(True)
    start_time = time.time()
    m.player_press_left(True)
    m.player_press_backward(True)
    while time.time() - start_time < 5:
        time.sleep(server_delay)
        m.player_press_use(True)
        time.sleep(server_delay)
        if new_yaw == -90:
            x, y, z = m.player_position()
            if "air" in m.getblock(ceil(x), round(y-1), floor(z-0.3)):
                m.player_press_left(False)
                m.player_press_right(True)
            elif "air" in m.getblock(ceil(x), round(y-1), floor(z+0.3)):
                m.player_press_right(False)
                m.player_press_left(True)
        elif new_yaw == 90:
            x, y, z = m.player_position()
            if "air" in m.getblock(floor(x-1), round(y-1), floor(z+0.3)):
                m.player_press_left(False)
                m.player_press_right(True)
            elif "air" in m.getblock(floor(x-1), round(y-1), floor(z-0.3)):
                m.player_press_right(False)
                m.player_press_left(True)
        elif abs(new_yaw) == 180:
            x, y, z = m.player_position()
            if "air" in m.getblock(floor(x-0.3), round(y-1), floor(z-1)):
                m.player_press_left(False)
                m.player_press_right(True)
            elif "air" in m.getblock(floor(x+0.3), round(y-1), floor(z-1)):
                m.player_press_right(False)
                m.player_press_left(True)
        elif new_yaw == 0:
            x, y, z = m.player_position()
            if "air" in m.getblock(floor(x+0.3), round(y-1), ceil(z)):
                m.player_press_left(False)
                m.player_press_right(True)
            elif "air" in m.getblock(floor(x-0.3), round(y-1), ceil(z)):
                m.player_press_right(False)
                m.player_press_left(True)

    print("Finished bridging")
    m.player_press_right(False)
    m.player_press_backward(False)
    m.player_press_left(False)
    time.sleep(0.1)
    m.player_press_use(False)

def moon_bridge():
    screen_name = m.screen_name()
    if screen_name is not None:
        return
    yaw, pitch = m.player_orientation()
    print("Starting Moon Bridge")
    m.player_inventory_select_slot(1)
    new_yaw = closest_bridging_yaw(yaw)
    look(new_yaw, 77)
    time.sleep(0.3)
    m.player_press_use(True)
    start_time = time.time()

    m.player_press_backward(True)
    state = "b"
    i = 0
    while time.time() - start_time < 5:
        if i == 0:
            if state =="b":
                m.player_press_backward(False)
                m.player_press_right(True)
                state = "r"
            elif state == "r":
                m.player_press_right(False)
                m.player_press_backward(True)
                state = "b"

        m.player_press_use(True)

        time.sleep(random.randint(20, 30)/1000)
        i = (i+1)%8

    print("Finished bridging")
    m.player_press_right(False)
    m.player_press_backward(False)
    m.player_press_left(False)
    time.sleep(0.1)
    m.player_press_use(False)

def actual_moon_bridge():
    screen_name = m.screen_name()
    if screen_name is not None:
        return
    yaw, pitch = m.player_orientation()
    print("Starting Actual Moon Bridge")
    m.player_inventory_select_slot(1)
    new_yaw = closest_bridging_yaw(yaw)
    look(new_yaw, 77)
    time.sleep(0.3)
    m.player_press_use(True)
    start_time = time.time()

    m.player_press_backward(True)
    state = "b"
    i = 0
    while time.time() - start_time < 5:
        if i == 0:
            if state =="b":
                m.player_press_right(True)
                state = "r"
            elif state == "r":
                m.player_press_right(False)
                state = "b"

        m.player_press_use(True)

        time.sleep(random.randint(20, 30)/1000)
        i = (i+1)%16

    print("Finished bridging")
    m.player_press_right(False)
    m.player_press_backward(False)
    m.player_press_left(False)
    time.sleep(0.1)
    m.player_press_use(False)

def setup_crosshair():
    screen_name = m.screen_name()
    if screen_name is not None:
        return
    yaw, pitch = m.player_orientation()
    print("Setting up crosshair")
    new_yaw = closest_bridging_yaw(yaw)
    look(new_yaw, 75.6)
    print("Crosshair set")