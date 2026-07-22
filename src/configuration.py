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
    change_zoom_by_wheel_amt = 25
    zoom_window_height_scale = 3
    max_zoom_scale_by_percentage = 1000

class Media_Config:
    min_vid_audio_percentage_progressed_for_backwards = 5
    default_zoom = 100
    default_volume = 50
    max_volume = 100

def get_max_log_count():
    return _max_log_count