# boot.py - UCT Micromouse Hybrid Bootloader
try:
    import pyb
    pyb.usb_mode('VCP+MSC')
except Exception as e:
    pass
