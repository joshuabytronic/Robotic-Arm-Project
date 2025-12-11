from Camera import surface_control, scan_control

# --- VARIABLES FOR GENERATING COORDINATES ---
# sheet_dimensions = [636, 1235, 0] # height, length, depth (y, x, z)
sheet_dimensions = [1235, 636, 0] # length, height, depth (x, y, z)
sheet_mount_dimensions = [0, 0, 10]
camera = surface_control
module_name = "Module1"
do_pulses = False
wait_time = 1
digital_output = "ABB_Scalable_IO_0_DO1"
digital_input = "ABB_Scalable_IO_0_DI1"
socket_ip = "\"192.168.125.1\"" # needs quotation marks!


# --- SCANNER CONFIGURATION ---
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

