"""
All units in mm
x = 900, y = 0 is the bottom centre of the plate, therefore centre of plate is at x = 900 - (635/2) , y = 0
"""

from math import ceil
from Camera import surface_control, scan_control, Camera

#Variables for user to set:
plate_dimensions = [635, 1235, 0]
camera = scan_control

#Constants
orientations = {
    "parallel": "[0, 0.7071, 0, 0.7071]",
    "perpendicular": "[0.02, 0.4, -1.0, 0]"
}
parallel_orientation = "[0, 0.7071, 0, 0.7071]"
perp_orientation = "[0.02, 0.4, -1.0, 0]"

scan_area = camera.scan_area
camera_offset = camera.camera_offset

#Plate positioning and offset calculations
if camera == surface_control:
    plate_x_location = 900 
elif camera == scan_control:
    plate_x_location = 750 #The offset in mm from the robot origin along the x axis

plate_offset = [plate_x_location - (plate_dimensions[0]), (-plate_dimensions[1])/2, plate_dimensions[2]]

#Summing camera (inclusive of mount) and plate offsets for tooltip offset
offset = [0,0,0]
for index in range(0,len(offset)):
    offset[index] = (plate_offset[index] + camera_offset[index])

def get_coords():
    coords = []
    
    #How many times can we divide the plate by the x and y scan area?
    x_times = ceil(plate_dimensions[0] // scan_area[0])
    y_times = ceil(plate_dimensions[1] // scan_area[1])

    edge_to_middle = [x/2 for x in scan_area]
    for x in range(1,x_times+1):
        if x % 2 == 0:
            y_range = range(1,y_times+1)
        else:
            y_range = range(y_times, 0, -1)
        for y in y_range:
            #Find the centre of the area on the sheet
            x_centre = (scan_area[0] * x) - edge_to_middle[0]
            y_centre = (scan_area[1] * y) - edge_to_middle[1]

            #Transform to global coords
            x_global = x_centre + offset[0]
            y_global = y_centre + offset[1]
            coords.append([x_global, y_global, offset[2]])
    return coords

def get_scan_coords():
    coords = []
    
    #We scan for the entirety of x, y / height times
    y_min = 0
    y_max = plate_dimensions[1]
    x_times = ceil(plate_dimensions[0] / scan_area[0])
    for x in range(1,x_times+1):
        x_centre = (x * scan_area[0]) - (scan_area[0]/2)
        
        x_global = x_centre + offset[0]
        y_min_global = y_min + offset[1]
        y_max_global = y_max + offset[1]
        coords.append([x_global, y_min_global,offset[2] ])
        coords.append([x_global, y_max_global, offset[2]])

    return coords

def motion_to_txt(
        do_pulse: bool = False, 
        wait_time: int = 0.4, 
        pulse_pin: str = "ABB_Scalable_IO_0_DO6",
        module_name: str = "MODULE Wizard\n",
        coords: list = None,
        orientation: str = "parallel"
    ):

    effector_orientation = orientations[orientation]
    
    joint_config = "[-1, -1, -1, 0]" #old config = "[-1, 0, -1, 0]"
    external_joints = "[9E+09, 9E+09, 9E+09, 9E+09, 9E+09, 9E+09]"
    const_coords = f"{effector_orientation}, {joint_config}, {external_joints}"

    pulse_out =     f"    PulseDO\\PLength:=0.2,{pulse_pin};\n" if do_pulse else None
    wait_command =  f"    WaitTime {wait_time};\n" if wait_time else None

    location_strings, movement_strings = coords_to_string(camera, const_coords, wait_command, pulse_out)

    with open("motion.modx", "w") as motion:
        locations = "".join(location_strings)
        movements = "".join(movement_strings)
        
        motion.write(module_name)
        motion.write(locations)
        motion.write(movements)
        motion.write("  ENDPROC\n")
        motion.write("ENDMODULE")

def coords_to_string(camera_type: Camera, const_coords: str, wait_command: str = None, pulse_out: str = None):
    
    location_strings = []
    movement_strings = []
    
    #SURFACE CONTROL LOGIC ---------------------------------------------------
    if camera == surface_control:
        
        #Avoids passing singularity point at robot centre more than once
        coords.sort(key = lambda x: x[1])
        
        movement_strings.append("  PROC main()\n")
        movement_strings.append("    SingArea \\Wrist;\n")
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
    
    #SCAN CONTROL LOGIC ---------------------------------------------------
    elif camera == scan_control:
        
        movement_strings.append("  PROC main()\n")
        
        for number, coordinate in enumerate(coords):
            
            location = f"CONST robtarget Josh{str(number)}:= [{str(coordinate)}, {const_coords}];\n"
            
            if number % 2 != 0:
                
                #WE NEED TO INSERT THE OUTPUT TRIGGER HERE!!!
                
                movement = f"    MOVEJ Josh{str(number)}, v500, fine, tool0;\n"
                if wait_command:
                    movement_strings.append(wait_command)
            else:
                movement = f"    MOVEL Josh{str(number)}, v500, fine, tool0;\n"

            location_strings.append(location)
            movement_strings.append(movement)
            if pulse_out:
                movement_strings.append(pulse_out)
            if wait_command:
                movement_strings.append(wait_command)

        return location_strings, movement_strings
    
if __name__ == "__main__":
    #Getting co-ordinates and writing to the coordinates.csv

    if camera == surface_control:
        coords = get_coords()
    else:
        coords = get_scan_coords()
    
    #Fill RAPID file
    motion_to_txt(coords=coords, do_pulse=False, wait_time=None, orientation=camera.orientation)