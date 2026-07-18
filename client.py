import time
from java import JavaClass
import minescript as m

Minecraft = JavaClass("net.minecraft.client.Minecraft")
mc = Minecraft.getInstance()
level = mc.level
current_player = mc.player

# Use script_loop for speed — runs off the render thread
m.set_default_executor(m.script_loop)

def is_player_invisible(player):
    entity = level.getEntity(player.id)
    if entity:
        return entity.isInvisible()
    return False

invisible_players = {}
last_invis_check = 0

def do_invisibility_checks():
    global last_invis_check
    now = time.time()
    # Only check invisibility every 0.5s, not every cycle
    if now - last_invis_check < 0.5:
        return
    last_invis_check = now

    for player in m.players():
        if player.id == mc.player.getId():
            continue
        if player.id not in invisible_players:
            invisible_players[player.id] = is_player_invisible(player)
            if invisible_players[player.id]:
                print(f"{player.name} is currently invisible.")
        else:
            currently_invisible = is_player_invisible(player)
            if currently_invisible and not invisible_players[player.id]:
                print(f"{player.name} has become invisible!")
            elif not currently_invisible and invisible_players[player.id]:
                print(f"{player.name} is no longer invisible.")
            invisible_players[player.id] = currently_invisible


def do_trigger_checks():
    targetted_entity = m.player_get_targeted_entity(max_distance=3)
    if targetted_entity is None:
        return

    cooldown = current_player.getAttackStrengthScale(0.0).value
    #velocity = m.player().velocity[1]

    if cooldown >= 1:
        #m.player_press_sprint(False)
        m.player_press_attack(True)
        m.player_press_attack(False)

print("Started client script")
m.player_press_jump(True)
while True:
    do_trigger_checks()           # trigger check FIRST — highest priority
    #do_invisibility_checks()       # invis check second, throttled