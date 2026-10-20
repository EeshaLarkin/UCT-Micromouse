import uct_mouse
from motion import Motion

uct_mouse.init()
uct_mouse.set_polarity(1, 1)
uct_mouse.delay_ms(20)

m = Motion()
m.calibrate_gyro()
print("walls L/F/R:", m.read_walls())   # start cell: (True, False, True)
m.move(1)                               # drive into cell (1,0)
print("walls L/F/R:", m.read_walls())
m.pirouette()
