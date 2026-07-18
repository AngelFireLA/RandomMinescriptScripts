import minescript
import time


def reset_bot():
    # 1. Kill the player to reset health and hunger
    minescript.echo("Resetting bot state...")
    minescript.execute("/kill @s")

    # 2. Wait for respawn
    # We loop until health is greater than 0
    while True:
        try:
            if minescript.player_health() > 0:
                break
        except:
            pass
        time.sleep(0.5)

    # Small delay to ensure the server has registered the respawn
    time.sleep(1)

    # 3. Clear any existing items just in case
    minescript.execute("/clear @s")

    # 4. Set Armor (Unenchanted Diamond)
    minescript.execute("/item replace entity @s armor.head with diamond_helmet")
    minescript.execute("/item replace entity @s armor.chest with diamond_chestplate")
    minescript.execute("/item replace entity @s armor.legs with diamond_leggings")
    minescript.execute("/item replace entity @s armor.feet with diamond_boots")

    # 5. Set Hotbar (Specific order)
    # Slot 0: Diamond Axe
    minescript.execute("/item replace entity @s hotbar.0 with diamond_axe")
    # Slot 1: Diamond Sword
    minescript.execute("/item replace entity @s hotbar.1 with diamond_sword")

    # Slot 2: Bow with Infinity
    # (Using 1.20.5+ Component syntax. For older versions use: bow{Enchantments:[{id:"minecraft:infinity",lvl:1}]})
    minescript.execute('/item replace entity @s hotbar.2 with bow[enchantments={infinity:1}]')

    # Slot 3: Golden Apple
    minescript.execute("/item replace entity @s hotbar.3 with golden_apple")
    # Slot 4: 5 Steaks
    minescript.execute("/item replace entity @s hotbar.4 with cooked_beef 5")

    # 6. Set Offhand (Shield)
    minescript.execute("/item replace entity @s weapon.offhand with shield")

    # 7. Add 1 Arrow (Needed for Infinity to work)
    minescript.execute("/give @s arrow 1")

    # 8. Reset selected slot to Sword (standard prep)
    minescript.player_inventory_select_slot(0)

    minescript.echo("Ready for battle. Waiting for 'Start' message.")


if __name__ == "__main__":
    reset_bot()