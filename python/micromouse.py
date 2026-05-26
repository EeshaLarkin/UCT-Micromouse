import socket
import json
import time
import serial
import glob
import sys

class Micromouse:
    def __init__(self, method='tcp', host='127.0.0.1', port=8000, baud=115200, verbose=True):
        self.method = method
        self.host = host
        self.port = port
        self.baud = baud
        self.verbose = verbose
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ser = None
        self.connected = False
        
        # Local configuration tracker
        self.data_mode = "a"    # "a" = absolute, "d" = delta
        self.fields_mode = "f"  # "f" = full, "s" = sparse
        
        # Local shadow cache for downstream sensors to emulate SRAM pointers
        self.shadow = {
            "tof_l": 0,
            "tof_c": 0,
            "tof_r": 0,
            "ir_fl": 0,
            "ir_fr": 0,
            "ir_sl": 0,
            "ir_sr": 0,
            "lenc": 0,
            "renc": 0,
            "gyro": 0.0,
            "v_batt": 0.0,
            "btn1": 0,
            "btn2": 0
        }
        self.last_packet = {}
        self.tracked_deltas = set()
        self.last_tx = ""
        self.last_rx = ""
        
    def _merge_update(self, incoming_packet):
        """Applies Absolute/Delta data modifications to the local shadow state."""
        is_sync = incoming_packet.get("sync") == 1
        self.last_packet = incoming_packet
        
        for key, value in incoming_packet.items():
            if key in ["sync", "c", "p", "a"]:
                continue
                
            if key.startswith("+") and key[1:] in self.shadow:
                # Delta Update (e.g. "+lenc" -> "lenc")
                self.shadow[key[1:]] += value
                self.tracked_deltas.add(key[1:])
            else:
                # Absolute Update
                self.shadow[key] = value

    def connect(self):
        """Connects via TCP (Simulink loopback) or Serial VCP (Physical Hardware)."""
        if self.method == 'tcp':
            if self.verbose: print(f"Connecting to Simulink Autograder at {self.host}:{self.port}...")
            while not self.connected:
                try:
                    self.sock.connect((self.host, self.port))
                    self.connected = True
                    self.configure(sync=1) # Force full absolute packet to initialize delta trackers
                    if self.verbose: print("Connected to Autograder Engine successfully!")
                except ConnectionRefusedError:
                    time.sleep(0.5)
        elif self.method == 'serial':
            ports = glob.glob('/dev/cu.usbmodem*')
            if not ports:
                raise ConnectionError("No ST-Link VCP found! Is the board plugged in?")
            
            if self.verbose:
                print(f"Connecting to Serial {ports[0]} at {self.baud} baud...\n")
            self.ser = serial.Serial(ports[0], self.baud, timeout=0.1, write_timeout=0.1)
            self.ser.dtr = True
            self.ser.rts = True
            time.sleep(1.5)  # Wait for STM32 to finish hardware reboot after DTR assertion
            self.ser.reset_input_buffer()  # Flush any ST-Link boot-up garbage
            self.connected = True
            self.configure(sync=1) # Force full absolute packet to initialize delta trackers
            if self.verbose:
                print("Connected to Hardware Serial successfully!\n")

    def _exchange_data(self, actuator_dict):
        """Handles JSON exchange with Simulink or physical hardware."""
        if not self.connected:
            raise ConnectionError("Not connected. Call connect() first.")
        
        # 1. Send actuation intent string
        if actuator_dict:
            tx_str = json.dumps(actuator_dict, separators=(',', ':')) + '\r\n'
            self.last_tx = tx_str.strip()
            if self.method == 'tcp':
                self.sock.sendall(tx_str.encode('utf-8'))
            elif self.method == 'serial':
                self.ser.write(tx_str.encode('utf-8'))
        
        # 2. Receive and process telemetry frames
        if self.method == 'tcp':
            rx_bytes = self.sock.recv(1024)
            if not rx_bytes:
                raise ConnectionError("Connection closed.")
            rx_str = rx_bytes.decode('utf-8').strip()
            self.last_rx = rx_str
            for line in rx_str.split('\n'):
                if line:
                    self._merge_update(json.loads(line))
        elif self.method == 'serial':
            # Cap reads at 20 per tick to prevent infinite loop hangs
            max_reads = 20
            while self.ser.in_waiting > 0 and max_reads > 0:
                line = self.ser.readline()
                max_reads -= 1
                line_str = line.decode('utf-8', errors='replace').strip()
                if line_str:
                    self.last_rx = line_str
                try:
                    if line_str.startswith('{') and line_str.endswith('}'):
                        self._merge_update(json.loads(line_str))
                    elif line_str:
                        print(f"[STM32 Python]: {line_str}")
                except json.JSONDecodeError:
                    pass

    def configure(self, rate=None, data=None, fields=None, sync=None):
        """Update kernel streaming configuration and local tracking mode."""
        cfg = {}
        if rate is not None: cfg["rate"] = rate
        if data is not None: 
            cfg["enc_mode"] = data  # Send actual C kernel parameter key
            self.data_mode = data
        if fields is not None: 
            cfg["fields"] = fields
            self.fields_mode = fields
        if sync is not None: cfg["sync"] = sync
        
        if cfg:
            self._exchange_data({"c": cfg})
            
    def poll(self):
        """Manually request a sensor payload update."""
        self._exchange_data({"p": 1})

    def set_pwm(self, left_pwm, right_pwm):
        """Atomic call matching the embedded hardware proxy C API."""
        # Setting PWM forces the loopback exchange, updating sensors immediately
        self._exchange_data({"a": [left_pwm, right_pwm]})

    def get_encoders(self):
        return [self.shadow.get("lenc", 0), self.shadow.get("renc", 0)]

    def get_sensors(self):
        return self.shadow