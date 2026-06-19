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

# Default to normal polarity (1, 1). If you need to reverse a motor's polarity,
# you can change the values here (e.g., uct_mouse.set_polarity(-1, 1))
uct_mouse.set_polarity(1, 1)

print("--- UCT Mouse is ALIVE! ---")

while True:
    print("Motors ON")
    uct_mouse.set_motors(50, 50)
    uct_mouse.delay_ms(1000)
    
    print("Motors OFF")
    uct_mouse.set_motors(0, 0)
    uct_mouse.delay_ms(1000)