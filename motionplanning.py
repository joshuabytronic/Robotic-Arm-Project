"""
All units in mm
x = 900, y = 0 is the bottom centre of the plate, therefore centre of plate is at x = 900 - (635/2) , y = 0
"""

from math import ceil
from Camera import surface_control, scan_control, Camera

#Variables for user to set:
sheet_dimensions = [636, 1235, 0]
sheet_mount_dimensions = [0, 0, 10]
camera = scan_control
module_name = "Module1"
do_pulses = False
wait_time = 1
digital_output = "ABB_Scalable_IO_0_DO1"
digital_input = "ABB_Scalable_IO_0_DI1"
socket_ip = "\"192.168.125.1\"" # needs quotation marks!

positions = {
    "new": "[-1, -1, -1, 0]",
    "old": "[-1, 0, -1, 0]",
    "test": "[0,0,0,0]"
}
joint_position = positions["new"]

#Socket connections
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
    f"    SocketBind server_socket, {socket_ip},  8000;\n"
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

#Constants
orientations = {
    "parallel": "[0, 0.7071, 0, 0.7071]",
    "parallel_2": "[0.65, 0.65, -0.3, 0.3]",
    "parallel_3": "[0.707106781,0,0.707106781,0]",
    "final": "[0.5, 0.5, -0.5, 0.5]", # this is a mess for now sorry if someone else uses this
    "final_2": "[0.5,0.5,0.5,-0.5]",
    "final_2_2": "[0.5,-0.5,0.5,0.5]",
    "perpendicular": "[0.0, 0.4, -1.0, 0]"
}
# parallel_orientation = "[0, 0.7071, 0, 0.7071]"
# perp_orientation = "[0.0, 0.4, -1.0, 0]"

scan_area = camera.scan_area
camera_offset = camera.camera_offset

#Plate positioning and offset calculations
if camera == surface_control:
    sheet_x_location = 900-12.5+20 
elif camera == scan_control:
    sheet_x_location = 900-12.5+20 #The offset in mm from the robot origin along the x axis

sheet_offset = [
        sheet_x_location - (sheet_dimensions[0]) + sheet_mount_dimensions[0],
        (-sheet_dimensions[1])/2 + sheet_mount_dimensions[1],
        sheet_dimensions[2] + sheet_mount_dimensions[2]
    ]

#Summing camera (inclusive of mount) and plate offsets for tooltip offset
offset = [0,0,0]
for index in range(0,len(offset)):
    offset[index] = (sheet_offset[index] + camera_offset[index])

def get_coords():
    if camera == surface_control:
        return get_surface_coords()
    elif camera == scan_control:
        return get_scan_coords()
    else:
        raise ValueError("Camera not recognised! Please check coordinate generation function!")

def get_surface_coords():
    coords = []
    
    #How many times can we divide the plate by the x and y scan area?
    x_times = ceil(sheet_dimensions[0] / scan_area[0])
    y_times = ceil(sheet_dimensions[1] / scan_area[1])


    edge_to_middle = [x/2 for x in scan_area]    

    for x in range(1,x_times+1):

        for y in range(1,y_times+1):
            #Find the centre of the area on the sheet
            if x == x_times:
                x_centre = (sheet_dimensions[0] - (scan_area[0] / 2))
            elif x == 1:
                x_centre = (scan_area[0] / 2)
            else:
                x_centre = (scan_area[0] * x) - edge_to_middle[0]
            
            if y == y_times:
                y_centre = (sheet_dimensions[1] - (scan_area[1] / 2))
            elif y == 1:
                y_centre = (scan_area[1] /2)
            else:
                y_centre = (scan_area[1] * y) - edge_to_middle[1]

            #Transform to global coords
            x_global = x_centre + offset[0]
            y_global = y_centre + offset[1]
            coords.append([x_global, y_global, offset[2]])
    
    # for x in range(1,x_times+1):
    #     if x % 2 == 0:
    #         y_range = range(1,y_times+1)
    #     else:
    #         y_range = range(y_times, 0, -1)
        
    #     for y in y_range:
    #         #Find the centre of the area on the sheet
    #         if x == x_times:
    #             x_centre = (sheet_dimensions[0] - (scan_area[0] / 2))
    #         else:
    #             x_centre = (scan_area[0] * x) - edge_to_middle[0]
            
    #         if y == y_times:
    #             y_centre = (sheet_dimensions[1] - (scan_area[1] / 2))
    #         else:
    #             y_centre = (scan_area[1] * y) - edge_to_middle[1]

    #         #Transform to global coords
    #         x_global = x_centre + offset[0]
    #         y_global = y_centre + offset[1]
    #         coords.append([x_global, y_global, offset[2]])
    
    return coords

def get_scan_coords():
    coords = []

    y_min = 0
    y_min_global = y_min + offset[1]
    
    y_max = sheet_dimensions[1]
    y_max_global = y_max + offset[1]
    x_constant = sheet_dimensions[0] / 2 
    x_constant_global = x_constant + offset[0]

    coords.append([x_constant_global,y_min_global,offset[2]])
    coords.append([x_constant_global,y_max_global,offset[2]])
    return coords


def legacy_get_scan_coords():
    raise NotImplementedError("This function is deprecated. Use get_scan_coords() instead.")    
    coords = []
    
    y_min = 0
    y_max = sheet_dimensions[1]
    x_times = ceil(sheet_dimensions[0] / scan_area[0])
    
    for x in range(1,x_times+1):
        if x == x_times:
            x_centre = (sheet_dimensions[0] - (scan_area[0] / 2))
        else:
            x_centre = (x * scan_area[0]) - (scan_area[0]/2)
        
        x_global = x_centre + offset[0]
        
        #This shortens the path by alternating the direction of scan.
        #Remove if statement to keep direction of scan 
        y_min_global = (y_min + offset[1]) if x % 2 == 0 else (y_max + offset[1])
        y_max_global = (y_max + offset[1]) if x % 2 == 0 else (y_min + offset[1])
        
        coords.append([x_global, y_min_global, offset[2]])
        coords.append([x_global, y_max_global, offset[2]])

    return coords

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

    pulse_out =     f"    PulseDO\\PLength:=0.2,{pulse_pin};\n" if do_pulse else None
    
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
    
    module_name = f"MODULE {module_name}\n"

    with open("motion.modx", "w") as motion:
        locations = "".join(location_strings)
        movements = "".join(movement_strings)
        
        motion.write(module_name)
        motion.write("\n")
        motion.write(locations)
        motion.write("\n")
        
        if wait_time: motion.write(socket_connection)
        motion.write("  PROC main()\n")
        motion.write("    SingArea \\Wrist;\n")
        motion.write(movements)
        motion.write("\n")
        if wait_time: motion.write(socket_close)
        motion.write("\n")
        motion.write("  ENDPROC\n")
        motion.write("ENDMODULE")

def coords_to_string(camera_type: Camera, const_coords: str, wait_command: str = None, pulse_out: str = None, coords: list = []):
    
    location_strings = []
    movement_strings = []
    
    #SURFACE CONTROL LOGIC ---------------------------------------------------
    if camera == surface_control:
        
        #Avoids passing singularity point at robot centre more than once
        coords.sort(key = lambda x: x[1])
        
        for number, coordinate in enumerate(coords):
            location = f"CONST robtarget Josh{str(number)}:= [{str(coordinate)}, {const_coords}];\n"
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
    
    #SCAN CONTROL LOGIC ---------------------------------------------------------
    elif camera == scan_control:
        
        for number, coordinate in enumerate(coords):
            
            location = f"CONST robtarget Josh{str(number)}:= [{str(coordinate)}, {const_coords}];\n"
            
            if (number + 1) % 2 != 0:
                
                movement = f"    MOVEJ Josh{str(number)}, vmax, fine, tool0;\n"
                if wait_command:
                    movement_strings.append(wait_command)
                #Pulse out should be after this? ----------------------------------------
            else:
                movement = f"    MOVEL Josh{str(number)}, v500, fine, tool0;\n"
                #This is where pulse stop needs to be? ----------------------------------

            location_strings.append(location)
            movement_strings.append(movement)
            if pulse_out:
                movement_strings.append(pulse_out)
            if wait_command:
                movement_strings.append(wait_command)

        return location_strings, movement_strings

    else:
        raise ValueError("Failed at coords_to_string()")


if __name__ == "__main__":
    #Getting co-ordinates and writing to the coordinates.csv

    coords = get_coords()
    
    #Fill RAPID file
    motion_to_txt(coords=coords, module_name=module_name, do_pulse=do_pulses, wait_time=wait_time, orientation=camera.orientation)