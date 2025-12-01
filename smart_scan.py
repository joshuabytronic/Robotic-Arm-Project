from math import ceil
from Camera import surface_control, scan_control, Camera

# ==========================================
# CONFIGURATION
# ==========================================
# You can adjust these or import them if they are constant
sheet_dimensions = [636, 1235, 0]
sheet_mount_dimensions = [0, 0, 10]
camera = surface_control  # Default to surface control for this logic

# Plate positioning logic (copied from motionplanning.py for standalone function)
if camera == surface_control:
    sheet_x_location = 900 - 12.5 
elif camera == scan_control:
    sheet_x_location = 900 

sheet_offset = [
    sheet_x_location - (sheet_dimensions[0]) + sheet_mount_dimensions[0],
    (-sheet_dimensions[1])/2 + sheet_mount_dimensions[1],
    sheet_dimensions[2] + sheet_mount_dimensions[2]
]

# Calculate global offset
offset = [0,0,0]
camera_offset = camera.camera_offset
for index in range(0, len(offset)):
    offset[index] = (sheet_offset[index] + camera_offset[index])


def get_smart_coords():
    """
    Generates coordinates with forced edge alignment:
    1. Columns start exactly at X=0 edge and end exactly at X=Width edge.
    2. Rows start exactly at Y=0 edge and end exactly at Y=Height edge.
    3. Middle points are distributed evenly to satisfy overlap.
    4. Scans Top -> Bottom for every column.
    """
    # 1. Get Dimensions and FOV
    sheet_w, sheet_h, _ = sheet_dimensions
    
    # Full Field of View (for edge alignment)
    fov_x = camera.x_scan_length
    fov_y = camera.y_scan_length
    
    # Effective Step Size (for calculating count based on overlap)
    step_x, step_y = camera.scan_area
    
    # 2. Calculate Number of Steps (N)
    # ceil(sheet / step) ensures we have enough tiles to cover the area 
    # with at least the requested overlap.
    n_x = ceil(sheet_w / step_x)
    n_y = ceil(sheet_h / step_y)
    
    # 3. Define Start and End Centers (Local Coords)
    # To align edge of FOV with edge of sheet: Center = Edge +/- FOV/2
    x_start_center = fov_x / 2
    x_end_center = sheet_w - (fov_x / 2)
    
    y_start_center = fov_y / 2
    y_end_center = sheet_h - (fov_y / 2)
    
    # 4. Generate Grid Points (Linear Interpolation)
    def linspace(start, end, n):
        if n <= 1:
            return [(start + end) / 2] # Center if only 1 tile fits/needed
        return [start + i * (end - start) / (n - 1) for i in range(n)]

    x_centers = linspace(x_start_center, x_end_center, n_x)
    y_centers = linspace(y_start_center, y_end_center, n_y)
    
    coords = []
    
    # 5. Build Path
    # "do that for every x column" -> Loop X
    # "scan exactly the top... finish exactly at 300y" -> Loop Y (Start to End)
    for x_local in x_centers:
        for y_local in y_centers:
            # Transform to global
            x_global = x_local + offset[0]
            y_global = y_local + offset[1]
            z_global = offset[2]
            
            coords.append([x_global, y_global, z_global])
            
    return coords

# ==========================================
# RAPID CODE GENERATION
# ==========================================

socket_ip = "\"192.168.125.1\""
do_pulses = False
wait_time = 1
module_name = "Module1"

positions = {
    "new": "[-1, -1, -1, 0]",
    "old": "[-1, 0, -1, 0]",
    "test": "[0,0,0,0]"
}
joint_position = positions["new"]

socket_connection = (
    f"\n"
    f"    VAR socketdev server_socket;\n" 
    f"    VAR socketdev client_socket;\n"  
    f"    VAR string integer_in;\n"
    f"    VAR string client_ip;\n"

    # ! 1. Create, bind, and listen on the server socket
    f"\n"
    f"    ! 1. Create, bind, and listen on the server socket\n"
    f"    SocketCreate server_socket;\n" 
    f"    SocketBind server_socket, {socket_ip}, 8000;\n"
    f"    SocketListen server_socket;\n"
        
    #     Accept an incoming connection with a timeout (60 seconds)
    f"\n"
    f"    ! 2. Accept an incoming connection with a timeout (60 seconds)\n"
    f"    SocketAccept server_socket, client_socket \\ClientAddress := client_ip \\Time:=60;\n"
    f"    TPWrite \"Connected to client: \" + client_ip;\n"
    f"\n"
    )

socket_close = (
    f"SocketClose client_socket;\n"
    f"SocketClose server_socket;\n"
)

orientations = {
    "parallel": "[0, 0.7071, 0, 0.7071]",
    "parallel_2": "[0.65, 0.65, -0.3, 0.3]",
    "parallel_3": "[0.707106781,0,0.707106781,0]",
    "final": "[0.5, 0.5, -0.5, 0.5]", 
    "final_2": "[0.5,0.5,0.5,-0.5]",
    "final_2_2": "[0.5,-0.5,0.5,0.5]",
    "perpendicular": "[0.0, 0.4, -1.0, 0]"
}

def coords_to_string(camera_type: Camera, const_coords: str, wait_command: str = None, pulse_out: str = None, coords: list = []):
    
    location_strings = []
    movement_strings = []
    
    # Logic adapted for smart_scan (assuming surface_control behavior)
    # We do NOT sort here because get_smart_coords already sorted them
    
    for number, coordinate in enumerate(coords):
        location = f"CONST robtarget Josh{str(number)}:= [{str(coordinate)}, {const_coords}];\n"
        
        # First move is Joint, subsequent are Linear (standard logic)
        if number < 1:
            movement = f"    MOVEJ Josh{str(number)}, vmax, fine, tool0;\n"
        else:
            movement = f"    MOVEL Josh{str(number)}, v500, fine, tool0;\n"
        
        location_strings.append(location)
        movement_strings.append(movement)
        if pulse_out:
            movement_strings.append(pulse_out)
        if wait_command:
            movement_strings.append(wait_command)
    
    return location_strings, movement_strings

def motion_to_txt(
        do_pulse: bool = False, 
        wait_time: int = 0.4, 
        pulse_pin: str = "ABB_Scalable_IO_0_DO6",
        module_name: str = "Wizard",
        coords: list = None,
        orientation: str = "parallel"
    ):

    effector_orientation = orientations[orientation]
    
    joint_config = joint_position
    external_joints = "[9E+09, 9E+09, 9E+09, 9E+09, 9E+09, 9E+09]"
    const_coords = f"{effector_orientation}, {joint_config}, {external_joints}"

    pulse_out = f"    PulseDO\\PLength:=0.2,{pulse_pin};\n" if do_pulse else None
    
    if wait_time:
        wait_command = (
            f"    WaitRob \\InPos;\n"
            f"    WaitTime 0.2;\n"
            f"    SocketSend client_socket \\Str := \"READY\";\n"
            f"    SocketReceive client_socket \\Str := integer_in \\Time:=30;\n"
            )
    else:
        wait_command = None

    location_strings, movement_strings = coords_to_string(camera, const_coords, wait_command, pulse_out, coords=coords)
    
    module_name_header = f"MODULE {module_name}\n"

    with open("motion.modx", "w") as motion:
        locations = "".join(location_strings)
        movements = "".join(movement_strings)
        
        motion.write(module_name_header)
        motion.write("\n")
        motion.write(locations)
        motion.write("\n")
        motion.write("")
        motion.write("  PROC main()\n")
        motion.write("    SingArea \\Wrist;\n")
        motion.write(socket_connection)
        motion.write(movements)
        motion.write("\n")
        motion.write(socket_close)
        motion.write("\n")
        motion.write("  ENDPROC\n")
        motion.write("ENDMODULE")

if __name__ == "__main__":
    coords = get_smart_coords()
    print(f"Generated {len(coords)} points.")
    
    # Generate the RAPID file
    motion_to_txt(
        coords=coords, 
        module_name=module_name, 
        do_pulse=do_pulses, 
        wait_time=wait_time, 
        orientation=camera.orientation
    )
    print("Successfully wrote to motion.modx")
