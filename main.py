import scanner_control, Camera, motionplanning
from scanner_control import MicroEpsilonDriver, Crb

# --- CONFIGURATION ---
IP_ADDRESS = '127.0.0.1'
MODBUS_PORT = 502
DATA_PORT = 502  # For the TCP data stream

# --- REGISTER MAP (Based on MEAutomationInterface.pdf) ---
# Holding Registers (Outputs to Sensor) - Offset = Register Number - 1
REG_CONTROL_SMART = 3   # Register 4 in manual (Smart Control)
# Input Registers (Inputs from Sensor)
REG_STATUS_ACQ    = 1   # Register 2 in manual (IB_StateAcquisition)

# --- CONTROL BITS (Register 4) ---
BIT_AUTO_MODE  = 1   # Bit 0: Q_AutomaticMode (Value 1)
BIT_START      = 2   # Bit 1: Q_Start (Value 2)
BIT_RESULT_ACK = 8   # Bit 3: Q_ResultsAck (Value 8)

def run_measurement_cycle():
    driver = MicroEpsilonDriver(IP_ADDRESS)
    crb = Crb()

    try:
        driver.connect()
        while True:
            # user_input = input("\nPress ENTER to Scan (or type 'q' to Quit): ")
            
            # if user_input.lower() == 'q':
            #     break # Exit the loop gracefully
                
            driver.run_measurement_cycle()
            
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


def main():
    run_measurement_cycle()


if __name__ == "__main__":
    main()

