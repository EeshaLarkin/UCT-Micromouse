# boot.py - UCT Micromouse Hybrid Bootloader
import machine
import pyb
import time

# The User Switch is on PE6, active low
sw = machine.Pin('E6', machine.Pin.IN, machine.Pin.PULL_UP)

# Small delay to ensure pull-up is stable
time.sleep_ms(50)

# If switch is pressed (LOW) during boot, mount as Read-Write and skip main.py
if sw.value() == 0:
    # Mount Read-Write (Standard)
    pyb.usb_mode('VCP+MSC')
    # Skip main.py execution to prevent infinite print hangs and allow reprogramming
    pyb.main('')
else:
    # Disable MSC (Mass Storage) to prevent PC filesystem corruption on bump/power loss
    pyb.usb_mode('VCP')
