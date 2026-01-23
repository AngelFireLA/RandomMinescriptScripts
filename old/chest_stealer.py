import random
import time

import minescript
import sys
import minescript_plus
from minescript_plus import Inventory

print("Chest Stealer script started.")


while True:
    try:
        items = minescript.container_get_items()

        if "Chest" == minescript.screen_name():
            for item in items:
                if item.slot < 27:
                    Inventory.shift_click_slot(item.slot)

    except:
        pass