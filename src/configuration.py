"""
Module to do the following:
    * Store variables that can be configured to change the program's behavior.
    
This module should be used for ALL configurations.
    NO configurations should be added to any other script than this one.

Any variables stored on the global scope of this module should be assumed to be private. 
    (denoted with a _ at the beginning of the variable name.)
Any variables denoted with 
"""

_max_log_count = 30

class File_Explorer_Table_Config:
    NAME_COL_WIDTH = 225
    DATE_MODIFIED_COL_WIDTH = 150
    TYPE_COL_WIDTH = 100
    SIZE_COL_WIDTH = 80
    
class Window_Config:
    min_width = 50
    min_height = 200

    # to remove for later
    default_width = 800
    default_height = 500

class Image_Config:
    min_image_size = 15
    max_zoomed_image_delta = 1440
    zoom_window_height_scale = 2.5

def get_max_log_count():
    return _max_log_count