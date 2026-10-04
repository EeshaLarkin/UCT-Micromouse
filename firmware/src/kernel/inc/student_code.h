#ifndef STUDENT_CODE_H
#define STUDENT_CODE_H
const char* student_python_code = 
"# main.py -- UCT Micromouse Default Telemetry Streamer\n"
"import uct_mouse\n"
"\n"
"# Initialize hardware (wakes OLED screen and sensor peripherals)\n"
"uct_mouse.init()\n"
"uct_mouse.set_motors(0, 0)\n"
"\n"
"print(\"--- UCT Micromouse Online ---\")\n"
"print(\"Streaming live telemetry over USB serial. Replace main.py with your code!\")\n"
"\n"
"while True:\n"
"    tof = uct_mouse.get_tof()\n"
"    enc = uct_mouse.get_encoders()\n"
"    vbatt = uct_mouse.get_vbatt()\n"
"    gyro = uct_mouse.get_gyro()\n"
"    print(\"VBatt: %.2fV | Gyro: %+.2f dps | Enc: (%d, %d) | ToF: %s\" % (\n"
"        vbatt, gyro, enc[0], enc[1], str(tof)\n"
"    ))\n"
"    uct_mouse.delay_ms(250)\n"
;
#endif
