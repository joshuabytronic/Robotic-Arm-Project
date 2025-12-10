import time
import socket
from pymodbus.client import ModbusTcpClient
from config import *
from motionplanning import get_coords


# --- CONFIGURATION ---
IP_ADDRESS = '127.0.0.1'
MODBUS_PORT = 502
DATA_PORT = 502  # For the TCP data stream

class Crb:
    def __init__(self, ip = "192.168.125.1", port = 8000, timeout = 2.0):
        try:
            self.ip = ip
            self.port = port
            self.timeout = timeout
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.port))
            print(f"Connected to robot at {self.ip}:{self.port}")
            self.connected = True
        except Exception as e:
            print(f"Error connecting to robot: {str(e)}")
            self.connected = False
            raise e

    def reconnect(self, max_attempts = 5, pause_time = 0.2):
        for _ in range(max_attempts):
            try:
                self.sock.connect((self.ip, self.port))
                self.connected = True
                return True
            except Exception as e:
                self.connected = False
                time.sleep(pause_time)
        return False

    def send(self, message):
        for _ in range(2):
            try:
                self.sock.sendall(message)
                print(f"Sent to robot: {message}\n")
                return True
            except Exception as e:
                self.reconnect(max_attempts=2,pause_time=0.2)
                print(f"Error sending message to robot: {str(e)}")
        return False

    def send_coords(self, x, y, z = 140.0):
        for _ in range(2):
            try:
                msg = f"{float(x):.3f},{float(y):.3f},{float(z):.3f}"
                self.sock.sendall(msg.encode())
                print(f"Sent to robot: {msg}\n")
                return True
            except Exception as e:
                self.reconnect(max_attempts=2,pause_time=0.2)
                print(f"Error sending to robot: {str(e)}")
        return False
    
    def go(self, x = None, y = None, z = None):
        if x and y and z:
            return self.send_coords(x, y, z)
        else:
            return self.send(b"go")

    def receive(self, attempts = 1):
        for _ in range(attempts):
            try:
                data = self.sock.recv(1024)
                if data:
                    return data
                else:
                    return None
            except Exception as e:
                self.reconnect()
                print(f"Error receiving from robot: {str(e)}")
        return None

    def wait_ready(self, ready_signal = b'READY'):
        while True:
            try:
                data = self.receive(attempts = 5)
                if data and ready_signal in data:
                    print(data.decode("utf-8"))
                    print("Robot READY signal recieved.")
                    return True
            except socket.timeout:
                print("Waiting for Robot READY signal... press Ctrl+C to exit...")
                

    def close(self):
        try:
            self.sock.close()
            print("Closed socket")
        except:
            pass

# --- REGISTER MAP (Based on MEAutomationInterface.pdf) ---
# Holding Registers (Outputs to Sensor) - Offset = Register Number - 1
REG_CONTROL_SMART = 3   # Register 4 in manual (Smart Control)
# Input Registers (Inputs from Sensor)
REG_STATUS_ACQ    = 1   # Register 2 in manual (IB_StateAcquisition)

# --- CONTROL BITS (Register 4) ---
BIT_AUTO_MODE  = 1   # Bit 0: Q_AutomaticMode (Value 1)
BIT_START      = 2   # Bit 1: Q_Start (Value 2)
BIT_RESULT_ACK = 8   # Bit 3: Q_ResultsAck (Value 8)

class MicroEpsilonDriver:
    def __init__(self, ip):
        self.mb = ModbusTcpClient(ip, port=MODBUS_PORT)
        self.sock = None
        self.ip = ip
        self.timer = time.time()

    def connect(self):
        if not self.mb.connect():
            raise ConnectionError("Could not connect to Modbus (Port 502).")
        print("✅ Modbus Connected.")
        
        # Connect to Data Stream
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.ip, DATA_PORT))
            print("✅ TCP Data Stream Connected.")
        except Exception as e:
            print(f"⚠️ Could not connect to Data Port {DATA_PORT}: {e}")

    def get_state(self):
        """Reads Input Register 2 to get current State Machine status."""
        # unit=1 or slave=1 depending on pymodbus version
        rr = self.mb.read_input_registers(REG_STATUS_ACQ)
        if rr.isError():
            # Fallback for older pymodbus
            rr = self.mb.read_input_registers(REG_STATUS_ACQ)
            if rr.isError(): return -1
        
        # High byte is UserSet, Low byte is`` StateAcquisition
        # We mask 0xFF to get just the Low`` 
        #"1111111111111qaByte (State)
        return rr.registers[0] & 0xFF

    def set_control_register(self, value):
        """Writes to Holding Register 4."""
        self.mb.write_register(REG_CONTROL_SMART, value)

    def get_data(self, blocking = False):
        try:
            if blocking:
                self.sock.setblocking(True)
            else:
                self.sock.setblocking(False)
            
            data = self.sock.recv(4096)  # Adjust buffer size as needed
            if data:
                print(f"Received {len(data)} bytes of data.")
                print(data.decode("utf-8"))
                return data
            else:
                print("No data received.")
                return None
        except Exception as e:
            return None

    
    def automatic_mode(self, do_timed_events: bool = False):
        # 1. Automatic mode ON - REG 4 write 1
        current_state = self.get_state()
       
        if do_timed_events: print(f"Current State: {current_state}")
        
        if current_state == 150: # Manual Mode
            print(">> Switching to Automatic Mode...")
            self.set_control_register(BIT_AUTO_MODE)
            
            # Wait for State 1 (Ready)
            for _ in range(10):
                time.sleep(0.2)
                state = self.get_state()
                if do_timed_events: print(f"   State: {state}")
                if state == 1: break
            else:
                print("❌ Timeout waiting for Ready State (1)")
                return False

        if self.get_state() != 1:
            print("❌ Sensor not Ready. Check connections.")
            return False

        print("✅ Sensor is READY (State 1).")
        return True    

    def trigger_measurement(self, do_timed_events: bool = False):
        # 2. TRIGGER MEASUREMENT
        #time.sleep(0.5)
        
        print(">> Triggering Scan (Sending 3)...")
        self.set_control_register(BIT_AUTO_MODE | BIT_START)

        # 3. WAIT FOR PROCESSING
        # State sequence: 1 -> 2 (Exposure) -> 3/4 (Processing) -> 5 (Wait for Acknowledgement)
        processing_timer = time.time()
        
        print(">> Waiting for completion...")
        data_received = False
        for _ in range(20):
            state = self.get_state()
            if do_timed_events: print(f"   State: {state}")
            
            # State 5 means "I have data, please acknowledge"
            if state == 5: 
                break
    
            # # While waiting, check for TCP data
            if not data_received  and time.time() - processing_timer > 1.0:
                data = self.get_data()
                data_received = data is not None

            time.sleep(0.2)
        
        if not data_received:
                data = self.get_data()
                data_received = data is not None
        

    def acknowledge(self):
        print(">> Acknowledging Results (Sending 9)...")
        self.set_control_register(BIT_AUTO_MODE | BIT_RESULT_ACK)
        time.sleep(0.2)
        
        # 5. RESET TO READY
        # Go back to just AutoMode(1) -> Value 1
        print(">> Resetting to Ready (Sending 1)...")
        self.set_control_register(BIT_AUTO_MODE)
        time.sleep(0.2)
        
        final_state = self.get_state()
        print(f"Final Sensor State: {final_state} (Should be 1)")
        if final_state != 1:
            print("❌ Sensor not in Ready State after acknowledgment.")
            self.acknowledge()
    
    def run_measurement_cycle(self, robot: Crb, coords: list = [None, None, None]):
        print("\n--- STARTING MEASUREMENT CYCLE ---")
        
        # Timed events are console outputs, stops spam in console
        if time.time() - self.timer > 3:
            self.timer = time.time()
            do_timed_events = True
        else:
            do_timed_events = False

        # 1. SWITCH SCANNER TO AUTOMATIC MODE
        if not self.automatic_mode(do_timed_events):
            return self.run_measurement_cycle(robot, coords)
        
        # 2. WAIT FOR ROBOT TO BE READY (STATIONARY WAITING FOR NEXT MOVE)
        robot.wait_ready()
        
        # 3. TRIGGER SCANNER MEASUREMENT
        self.trigger_measurement(do_timed_events)

        # 4. ACKNOWLEDGE RESULTS
        self.acknowledge()

        # 5. SEND GO SIGNAL TO ROBOT
        robot.go(coords[0],coords[1],coords[2])
        time.sleep(0.5)

    def close(self, robot: Crb = None):
        self.mb.close()
        if self.sock: self.sock.close()
        if robot: robot.close()

    def exit_to_manual_mode(self):
            """Switches the sensor back to Manual Mode so the GUI works again."""
            print("\n>> Exiting: Switching sensor back to Manual Mode (Reg 4 = 0)...")
            # Writing 0 turns off Bit 0 (AutomaticMode), forcing state 150 (Manual)
            self.set_control_register(0)
            time.sleep(0.5)
            print("✅ Sensor is in Manual Mode. You can now use 3DInspect manually.")

if __name__ == "__main__":
    coords = get_coords()
    print(coords)
    
    driver = MicroEpsilonDriver(IP_ADDRESS)
    crb = Crb()
    while True:
        x = int(input("Please enter x coordinate: ").strip())
        y = int(input("Please enter y coordinate: ").strip())
        z = int(input("Please enter z coordinate: ").strip())
        driver.connect()
        driver.run_measurement_cycle(crb, [x,y,z])

    coords = get_coords()
    for coord in coords:
        try:
            driver.connect()
            driver.run_measurement_cycle(crb, coord)
        
        except KeyboardInterrupt:
            print("\nStopped by User.")
        
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        
        finally:
            # This runs no matter how you stop (Error, Quit, or Ctrl+C)
            try:
                driver.exit_to_manual_mode()
            except:
                pass
            driver.close()
            crb.close()
            print("🔌 Connection Closed.")