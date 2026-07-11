import uct_mouse
import time

print("Starting long OLED test...")
if not uct_mouse.init():
    print("Failed to initialize mouse")
else:
    print("Mouse initialized.")
    try:
        for i in range(1500): # 1500 * 200ms = 300 seconds
            if i % 10 == 0:
                print(f"Tick {i}...")
            uct_mouse.delay_ms(200)
    except KeyboardInterrupt:
        pass
    print("Long test finished.")
