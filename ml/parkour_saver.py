import sys, os
import time
from math import floor

import minescript
import minescript_plus
try:
    parkour_name = sys.argv[1]
except:
    raise Exception("Please provide a parkour name as an argument.")

parkour_courses_folder = "minescript/parkour_courses/"
os.makedirs(parkour_courses_folder, exist_ok=True)
parkour_file_path = parkour_courses_folder + parkour_name + ".txt"
mini_checkpoints = []

def save_checkpoint():
    x, y, z = minescript.player_position()
    print(f"Checkpoint saved at ({floor(x)+0.5}, {floor(y)}, {floor(z)+0.5})")
    mini_checkpoints.append((floor(x)+0.5, floor(y), floor(z)+0.5))


def stop_recording():
    save_checkpoint()
    with open(parkour_file_path, "w") as f:
        for checkpoint in mini_checkpoints:
            f.write(f"{checkpoint[0]},{checkpoint[1]},{checkpoint[2]}\n")
    print(f"Parkour checkpoints saved to {parkour_file_path}")

print("Started saving parkour checkpoints.")

kb = minescript_plus.Keybind()
kb.set_keybind(320, save_checkpoint, name="SaveParkour")
kb.set_keybind(335, stop_recording, name="StopRecording")

while True:
    time.sleep(1)
