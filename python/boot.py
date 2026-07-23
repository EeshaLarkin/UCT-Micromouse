# boot.py - UCT Micromouse Hybrid Bootloader
try:
    import machine
    import pyb
    import time
     
    # The User Switch is on PE6, active low
    sw = machine.Pin('PE6', machine.Pin.IN, machine.Pin.PULL_UP)
     
    # Small delay to ensure pull-up is stable
    time.sleep_ms(50)
     
    # If switch is pressed (LOW) during boot, mount as Read-Write
    if sw.value() == 0:
        # Mount Read-Write (Standard)
        # pyb.usb_mode('VCP+MSC')
        pass
    else:
        # Fallback to VCP-only to prevent corruption from power glitches
        # pyb.usb_mode('VCP')
        pass
except Exception as e:
    pass
