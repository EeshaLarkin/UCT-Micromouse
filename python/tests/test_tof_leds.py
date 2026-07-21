import uct_mouse
import machine
import sys

# Configure control pins for LEDs
print("Initializing LED control pins...")
pb3 = machine.Pin('B3', machine.Pin.OUT)
pb3.value(1)  # Enable master LED gating

# Configure processor board status LEDs (PC13, PC14, PC15)
led_left = machine.Pin('C13', machine.Pin.OUT)
led_center = machine.Pin('C14', machine.Pin.OUT)
led_right = machine.Pin('C15', machine.Pin.OUT)

print("Initializing Micromouse API...")
if not uct_mouse.init():
    print("Error: Could not initialize uct_mouse API.")
    sys.exit(1)

print("Running TOF-to-LED test sketch. Press Ctrl+C to stop.")
try:
    while True:
        # get_tof returns: (left, front_left, center, front_right, right)
        tof_l, _, tof_c, _, tof_r = uct_mouse.get_tof()

        # Light up corresponding LED if distance < 200mm (0.2m)
        led_left.value(1 if tof_l < 200 else 0)
        led_center.value(1 if tof_c < 200 else 0)
        led_right.value(1 if tof_r < 200 else 0)

        # Call delay_ms to keep C kernel tick active and refresh TOF readings
        uct_mouse.delay_ms(50)
except KeyboardInterrupt:
    print("Test stopped by user.")
finally:
    # Clean up and turn off all LEDs
    led_left.value(0)
    led_center.value(0)
    led_right.value(0)
    pb3.value(0)
    print("LEDs disabled.")
