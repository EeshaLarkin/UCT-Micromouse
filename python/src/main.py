# =========================================================================
# IMPORTANT NOTE FOR STUDENTS:
# On the physical microcontroller (bare-metal), sensor values (ToF, encoders, 
# battery) are refreshed inside uct_mouse.delay_ms(). If you write a loop 
# that reads sensors without calling delay_ms(), the values will NEVER update 
# and the program will lock up. Always include a uct_mouse.delay_ms(...) call 
# in your control loops!
# =========================================================================


import uct_mouse

# Initialize connection to either the PC Simulator or Physical Hardware
uct_mouse.init()

# Load custom motor polarities from config file if present
try:
    with open("polarity.txt", "r") as f:
        lines = f.read().strip().split(",")
        left_pol = int(lines[0])
        right_pol = int(lines[1])
        uct_mouse.set_polarity(left_pol, right_pol)
        print("[Boot] Loaded motor polarity: Left={}, Right={}".format(left_pol, right_pol))
except Exception:
    # Default to normal polarity if file not found
    uct_mouse.set_polarity(1, 1)

print("--- UCT Mouse is ALIVE! ---")

while True:
    print("Motors ON")
    uct_mouse.set_motors(50, 50)
    uct_mouse.delay_ms(1000)
    
    print("Motors OFF")
    uct_mouse.set_motors(0, 0)
    uct_mouse.delay_ms(1000)