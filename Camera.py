class Camera():
    def __init__(
            self,
            name = None,
            depth = None,
            focal_length = 0,
            x_scan_length=None,
            y_scan_length=None, 
            camera_position = [0,0,0], # We can integrate depth into this?
            mount_depth = 0, #Should this change to mount offset?
            overlap = None,
            orientation: str = "parallel"
            ):
        """Initialize a Camera object with given properties. 
         Args:
            name (str): Name of the camera.
            depth (float): Depth of the camera mount.
            focal_length (float): Focal length of the camera.
            x_scan_length (float): Scanning length in the x direction.
            y_scan_length (float): Scanning length in the y direction.
        """

        self._name = name
        self._depth = depth
        self._focal_length = focal_length
        self._x_scan_length = x_scan_length
        self._y_scan_length = y_scan_length
        self._camera_position = camera_position
        self.overlap = overlap

        self._mount_depth = mount_depth
        valid_orientations = set(("parallel","perpendicular"))
        if orientation in valid_orientations:
            self.orientation = orientation
        else:
            raise ValueError("Please enter a correct orientation value: Currently supported are perpendicular, parallel")
        self.area_calc()
        self.camera_offset_calc()

    def camera_offset_calc(self):
        self.camera_offset = [0,0,0]
        self.camera_offset[0] = self.camera_position[0]
        self.camera_offset[1] = self.camera_position[1]
        self.camera_offset[2] = self.camera_position[2] + self.depth + self.focal_length + self._mount_depth
    
    @property
    def mount_depth(self):
        if self._mount_depth:
            return self._mount_depth
        raise ValueError("Mount depth not specified!")
    @mount_depth.setter
    def mount_depth(self, value):
        self._mount_depth = value
    
    @property
    def camera_position(self):
        return self._camera_position if self._camera_position else [0,0,0]
    
    @camera_position.setter
    def camera_position(self, new_position):
        if isinstance(new_position, list):
            for i, item in enumerate(new_position):
                self._camera_position[i] = item
        else:
            raise ValueError("Camera position must be a list of x,y,z values, offset from the mounting position")

    @property
    def depth(self):
        val = getattr(self, "_depth", None)
        if val is None:
            raise NotImplementedError("Camera must have a depth.")
        return val
    @depth.setter
    def depth(self, value):
        self._depth = value
    
    @property
    def focal_length(self):
        val = getattr(self, "_focal_length", None)
        if val is None:
            raise NotImplementedError("Camera must have a focal length.")
        return val
    @focal_length.setter
    def focal_length(self, value):
        self._focal_length = value
    
    @property
    def x_scan_length(self):
        val = getattr(self, "_x_scan_length", None)
        if val is None:
            raise NotImplementedError("Camera must have an x scanning length.")
        return val
    @x_scan_length.setter
    def x_scan_length(self, value):
        self._x_scan_length = value
    
    @property
    def y_scan_length(self):
        val = getattr(self, "_y_scan_length", None)
        if val is None:
            raise NotImplementedError("Camera must have a y scanning length.")
        return val
    @y_scan_length.setter
    def y_scan_length(self, value):
        self._y_scan_length = value
    
    def area_calc(self):    
        """Calculates the scan area and sets as class variable
        """        
        if self.overlap == None:
            self.scan_area = [self.x_scan_length, self.y_scan_length]
        else:
            non_overlapping_area = 1 - self.overlap
            x_scannable = self.x_scan_length * non_overlapping_area
            y_scannable = self.y_scan_length * non_overlapping_area
            self.scan_area = [x_scannable, y_scannable]


surface_control = Camera(
    name="Surface Control",
    depth=0,
    focal_length=440,
    x_scan_length=240,
    y_scan_length=150,
    mount_depth = 10,
    overlap = 0.3,
    orientation = "parallel"
)

scan_control = Camera(
    name="Scan Control",
    depth=0,
    focal_length= 400,
    x_scan_length= 335, #Make sure it's oriented the correct way
    y_scan_length= 1,
    mount_depth = 10,
    overlap = None,
    orientation = "perpendicular"
)