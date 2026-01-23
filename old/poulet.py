import random
import time

import minescript
import sys

nb_poulets = int(sys.argv[1])
print(f"Invocation de {nb_poulets} poulets...")
x,y,z = minescript.player_position()
for i in range(nb_poulets):
    time.sleep(0.05)
    minescript.execute("summon chicken " + str(x + random.randint(-2, 2)) + " " + str(y + 5) + " " + str(z + random.randint(-2, 2)))

