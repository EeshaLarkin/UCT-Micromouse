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

print("--- PikaScript is ALIVE! ---")

while True:
    print("Motors ON")
    uct_mouse.set_motors(30, 30)
    uct_mouse.delay_ms(1000)
    
    print("Motors OFF")
    uct_mouse.set_motors(0, 0)
    uct_mouse.delay_ms(1000)