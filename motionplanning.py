"""
All units in mm
x = 900, y = 0 is the bottom centre of the plate, therefore centre of plate is at x = 900 - (635/2) , y = 0
The global - local co-ords might be a bit confusing will fix later
"""

from math import ceil
import csv

#Properties of the plate
plate_dimensions = [635, 1235, 0] #x,y,z dimensions of plate]

#Properties of camera
x_scan_length = 240 
y_scan_length = 150
scanner_depth = 0
scanner_focal_length = 440

#Properties of the camera mount
mount_depth = 10

#Properties of scanning area and overlap percentage b/t each picture
overlap = 0.3
non_overlapping_area = 1 - overlap
x_scannable = x_scan_length * non_overlapping_area
y_scannable = y_scan_length * non_overlapping_area

#Moving 0,0,0 to be at the plate centre
""" 1. Place the bottom of the plate to be at x = 900
    2. Shift x(0) to the plate centre
    3. Shift 0,0,0 to mount centre
    4. Shift 0,0,0 to camera centre
"""
#Plate offset
plate_x_location = 900 
plate_offset = [plate_x_location - (plate_dimensions[0] / 2), 0, 0]

mount_offset = [0,0,mount_depth]
scanner_offset = [0,0,scanner_depth + scanner_focal_length]

#Summing all the offsets up!
offset = [0,0,0]
for index in range(0,len(offset)-1):
    offset[index] = (
        plate_offset[index] +
        mount_offset[index] +
        scanner_offset[index]
    )



def get_coords():
    #Initialising the co-ordinate array
    coordinates = []
    z_coord = plate_dimensions[2] + scanner_depth + scanner_focal_length + scanner_offset[2]
    half_plate = [dimension/2 for dimension in plate_dimensions]

    #How many times we can fit the scan area in the x-y plane
    divisible_x = ceil(plate_dimensions[0] / x_scannable)
    divisible_y = ceil(plate_dimensions[1] / y_scannable)

    #Filling the coordinates array
    for y in range(1,divisible_y):
        for x in range(1,divisible_x):
            x_coord = ((x_scannable * x) - half_plate[0]) + plate_x_location + scanner_offset[0]
            y_coord = ((y_scannable * y) - half_plate[1]) + scanner_offset[1]
            coordinates.append([x_coord, y_coord, z_coord])
    return(coordinates)

def coords_to_csv(coordinates: list):
    if not coordinates:
        raise ValueError("Coordinates is empty! Please ensure all initial properties are set!")
    
    try:
        with open("coordinates.csv", "w", newline="") as cofile:
            writer = csv.writer(cofile, delimiter=",")
            writer.writerow(["x_mm", "y_mm", "z_mm"])
            writer.writerows([[round(x, 3), round(y, 3), round(z, 3)] for x, y, z in coordinates])
    except PermissionError:
        raise PermissionError("Permission Error: File is open or script does not have permission to modify files.")

def motion_to_txt(
        do_pulse: bool = True, 
        wait_time: int = 0.4, 
        pulse_pin: str = "ABB_Scalable_IO_0_DO6",
        module_name: str = "MODULE Wizard\n",
        coords: list = None
        ):
    if not coords:
        raise ValueError("Please input coordinates from get_coords()")
    
    #Constants: Some portion of the co-ordinates is the same at position e.g rotation is more or less constant

    parallel_orientation = "[0, 0.7071, 0, 0.7071]"
    perp_orientation = "[0.02, 0.4, -1.0, 0]"

    effector_orientation = parallel_orientation
    joint_config = "[-1, -1, -1, 0]" #old config = "[-1, 0, -1, 0]"
    external_joints = "[9E+09, 9E+09, 9E+09, 9E+09, 9E+09, 9E+09]"
    const_coords = f"{effector_orientation}, {joint_config}, {external_joints}"

    pulse_out =     f"    PulseDO\\PLength:=0.2,{pulse_pin};\n"
    wait_command =  f"    WaitTime {wait_time};\n"
    
    #
    with open("motion.modx", "w") as motion:
        motion.write(module_name)
        
        #Creating variables containing location data
        for number, coordinate in enumerate(coords):
            motion.write(f"CONST robtarget Josh{str(number)}:= [{str(coordinate)}, {const_coords}];\n")

        #Main function
        motion.write("  PROC main()\n")
        motion.write("    SingArea \\Wrist;\n") #This allows wrist rotation during linear movement if a singularity is encountered
        #Writing each move position
        for number, _ in enumerate(coords):
            
            if number < 1:
                #Using MoveJ to ensure we can move to correct start position
                move_command = "    MOVEJ Josh" + str(number) + ", v500, fine, tool0;\n" 
            else:
                #Using MoveL to keep wrist in correct orientation
                move_command = "    MOVEJ Josh" + str(number) + ", v500, fine, tool0;\n" 
            
            motion.write(move_command)
            
            #Optional wait time and sending pulses to an output
            if do_pulse:
                motion.write(pulse_out)
            if wait_time:
                motion.write(wait_command)

        motion.write("  ENDPROC\n")
        motion.write("ENDMODULE")

if __name__ == "__main__":
    #Getting co-ordinates and writing to the coordinates.csv
    coords = get_coords()
    coords_to_csv(coords)
    
    #Fill RAPID file
    motion_to_txt(coords=coords, do_pulse=False)