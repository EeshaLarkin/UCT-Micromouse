# main.py -- UCT Micromouse Default Telemetry Streamer
import uct_mouse

# Initialize hardware (wakes OLED screen and sensor peripherals)
uct_mouse.init()
uct_mouse.set_motors(0, 0)

print("--- UCT Micromouse Online ---")
print("Streaming live telemetry over USB serial. Replace main.py with your code!")

while True:
    tof = uct_mouse.get_tof()
    enc = uct_mouse.get_encoders()
    vbatt = uct_mouse.get_vbatt()
    gyro = uct_mouse.get_gyro()
    print("VBatt: %.2fV | Gyro: %+.2f dps | Enc: (%d, %d) | ToF: %s" % (
        vbatt, gyro, enc[0], enc[1], str(tof)
    ))
    uct_mouse.delay_ms(250)
