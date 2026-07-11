import uct_mouse
import time

print("Starting OLED test...")
if not uct_mouse.init():
    print("Failed to initialize mouse")
else:
    print("Mouse initialized. Display should be active.")
    try:
        for i in range(100):
            print(f"Tick {i}...")
            uct_mouse.delay_ms(200)
    except KeyboardInterrupt:
        pass
    print("OLED test finished.")
