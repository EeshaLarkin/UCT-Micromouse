from micromouse import Micromouse
import time

if __name__ == '__main__':
    mouse = Micromouse(method='serial', verbose=True)
    mouse.connect()
    
    time.sleep(0.5) # Let sensors settle
    
    print("Starting cell movement...")
    mouse.move_cells(1.0, speed=40)