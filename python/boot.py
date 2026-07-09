# boot.py - UCT Micromouse Hybrid Bootloader
import machine
import pyb
import time

# The User Switch is on PE6, active low
sw = machine.Pin('E6', machine.Pin.IN, machine.Pin.PULL_UP)

# Small delay to ensure pull-up is stable
time.sleep_ms(50)

# Always enable VCP+MSC to ensure the VCP port and USB drive mount reliably on all OS platforms
pyb.usb_mode('VCP+MSC')

# If switch is pressed (LOW) during boot, skip main.py execution to prevent hangs
if sw.value() == 0:
    # Skip main.py execution to allow safe REPL access and reprogramming
    pyb.main('')
