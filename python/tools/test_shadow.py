import time
from micromouse import Micromouse

def main():
    print("=== UCT Micromouse Telemetry Test ===")
    
    # 1. Instantiate the client in Serial mode (connects to ST-Link automatically)
    mouse = Micromouse(method='serial')
    mouse.connect()
    
    # 2. Configure the hardware to transmit encoders as deltas (+lenc, +renc)
    print("Configuring kernel to use Delta Encoding ('d')...")
    mouse.configure(data='d')
    
    ticks = 0
    try:
        while True:
            # Actuate motors to 0 (pings the loopback exchange & prevents C watchdog cutoff)
            mouse.set_pwm(0, 0) 
            
            # Every ~5 seconds (500 ticks), print the full shadow state and force a sync check
            if ticks % 500 == 0 and ticks > 0:
                print(f"\n[Tick {ticks:04d}] Shadow State: {mouse.get_sensors()}")
                print(f"[Tick {ticks:04d}] Requesting Full Absolute Sync Dump to verify math...")
                mouse.configure(sync=1)
            
            # Every ~1 second (100 ticks), print the latest raw sparse packet (skipping sync ticks)
            elif ticks % 100 == 0 and ticks > 0:
                print(f"[Tick {ticks:04d}] Latest Sparse Packet: {mouse.last_packet}")
                
            time.sleep(0.01) # Sleep to approximate a 100Hz control loop
            ticks += 1
            
    except KeyboardInterrupt:
        print("\nExiting Shadow State Test...")

if __name__ == "__main__":
    main()