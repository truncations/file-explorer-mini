import os
import datetime
import shutil
from win32api import GetMonitorInfo, MonitorFromPoint

height_screen_key = 3

# Stores Keys for readability and Variables here.

# DO NOT CHANGE
_base_directory = os.path.dirname(__file__)[:-len("src")]
_resource_directory = os.path.join(_base_directory, "resource")
ui_src_file_name = "ui_source.ui"

max_log_count = 30

class File_Explorer_Config:
    NAME_COL_WIDTH = 225
    DATE_MODIFIED_COL_WIDTH = 150
    TYPE_COL_WIDTH = 100
    SIZE_COL_WIDTH = 80
    
class Directory_Point:
    time_format_str = "%m/%d/%Y %I:%M %p"
    file_size_multiples = [
        "KB","MB","GB","TB","PB","EB","ZB","YB",
    ]
    BYTES_MULTIPLE_CONST = 1024
    IS_DIRECTORY_KEY = "Folder"

    def __init__(self, path="", file_name="", extension="", date_modified=0.0, size=-1):
        self.path = path
        self.file_name = file_name

        self.extension = extension
        self.date_modified = date_modified
        self.size = size

    def point_is_dir(self):
        return self.extension == Directory_Point.IS_DIRECTORY_KEY
    
    def get_abs_path(self):
        return os.path.join(self.path, self.file_name)
    
    def get_date_modified_str(self):
        return datetime.datetime.fromtimestamp(self.date_modified).strftime(Directory_Point.time_format_str)
    
    def get_size_str(self):
        amt_after_multiple = self.size
        for multiple in Directory_Point.file_size_multiples:
            amt_after_multiple = amt_after_multiple / Directory_Point.BYTES_MULTIPLE_CONST
            if amt_after_multiple <= Directory_Point.BYTES_MULTIPLE_CONST:
                return f"{amt_after_multiple:.2f} {multiple}"
    # DEBUGGING PURPOSES
    def __str__(self):
        return f"{self.get_abs_path()}, date modified: {self.get_date_modified_str()}, size: {self.get_size_str()}"
    
class Directory_Manager:
    default_directory = os.path.abspath(os.sep)
    current_directory = default_directory
    current_directory_path = None

    @staticmethod
    def get_dir_ui_file(ui_file_name):
        return os.path.join(_resource_directory, ui_file_name)

    # MUST INCLUDE FILE EXTENSION.
    @staticmethod
    def get_dir_image_from_icons(image_file_name):
        return os.path.join(_resource_directory, "icons", image_file_name)
    
    # list_obj -> list of str(s)
    @staticmethod
    def split_path_into_list(directory):
        path_list = [path for path in os.path.normpath(directory).split(os.sep)]
        return path_list
    
    def compile_list_into_path(path_list):
        if len(path_list) == 1:
            return path_list[0] + os.sep
        return (os.sep).join(path_list)
    
    @staticmethod
    def get_list_of_files(directory):
        if not os.path.exists(directory):
            return []
        if not os.path.isdir(directory):
            return []
        
        list_of_files = []
        for file in os.listdir(directory):
            cur_file = file

            dir_point = Directory_Point(directory, cur_file)

            # get extension
            if os.path.isfile(dir_point.get_abs_path()):
                dir_point.extension = cur_file[cur_file.index("."):]
            else:
                dir_point.extension = Directory_Point.IS_DIRECTORY_KEY

            # get date modified and size
            file_statistics = os.stat(dir_point.get_abs_path())
            file_modified_time = file_statistics.st_mtime
            file_size = file_statistics.st_size

            dir_point.date_modified = file_modified_time
            dir_point.size = file_size

            list_of_files.append(dir_point)
        return list_of_files
    
    # setup definitions for Directory_Manager variables if the methods above are required.
    current_directory_path = split_path_into_list(current_directory)

class Window_Config():
    min_width = 50
    min_height = 200

    # to remove for later
    default_width = 800
    default_height = 500

    @staticmethod
    def get_taskbar_height():
        primary_monitor = MonitorFromPoint((0,0))
        monitor_info = GetMonitorInfo(primary_monitor)
        actual_screen_area = monitor_info.get("Monitor")
        available_screen_area = monitor_info.get("Work")
        return actual_screen_area[height_screen_key]-available_screen_area[height_screen_key]


def get_open_file_explorer_command():
    file_explorer_dir = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
    cur_dir = os.path.normpath(Directory_Manager.current_directory)
    return [file_explorer_dir, cur_dir]

def is_dir_given_path(directory):
    return os.path.isdir(directory)

def convert_to_path_str(string):
    return os.path.normpath(string)

