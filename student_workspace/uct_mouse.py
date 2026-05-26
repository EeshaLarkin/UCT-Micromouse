from micromouse import Micromouse

# -------------------------------------------------------------------------
# DESKTOP MOCK ABSTRACTION LAYER (Tier 2 - Simulator Version)
# This file acts as a polymorphic replacement for the PikaPython C-bindings.
# When students submit their main.py to the autograder, this file translates
# their API calls into JSON TCP packets for the Simulink 3D environment.
# -------------------------------------------------------------------------

class Mouse:
    def __init__(self):
        # Automatically connect to the Simulink Autograder on port 8000
        self._client = Micromouse(method='tcp')
        self._client.connect()
        self._client.configure(data='d') # Enable sparse delta encoding

    def set_pwm(self, left: int, right: int):
        self._client.set_pwm(left, right)

    def get_tof_l(self) -> int:
        return self._client.get_sensors().get('tof_l', 0)

    def get_tof_c(self) -> int:
        return self._client.get_sensors().get('tof_c', 0)

    def get_tof_r(self) -> int:
        return self._client.get_sensors().get('tof_r', 0)

    def get_gyro(self) -> float:
        return self._client.get_sensors().get('gyro', 0.0)

    def get_v_batt(self) -> float:
        return self._client.get_sensors().get('v_batt', 0.0)

    def tick(self):
        # In the TCP desktop simulator, we explicitly poll the JSON stream
        # to pull down the latest physics step from Simulink.
        self._client.poll()