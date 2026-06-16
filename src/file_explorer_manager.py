"""
Handles the main functionality of the File Explorer; file management such as:
    * Moving files/folders
    * Navigating through files/folders
    * Opening files/folders
    and more...

This also manages directories.

Todo:
    * Implement opening files
"""

import os
import datetime
import src.configuration
import shutil
import psutil

_work_directory = os.path.dirname(__file__)[:-len("src")]
_resource_directory = os.path.join(_work_directory, "resource")
drives_directory = "Drives"
_default_directory = drives_directory

# TODO: Probably delete this, having directory points is not necessary since the object itself is unutilized after creation.
# we may simply handle the logic using the information implemented in the table from main.py
# we use methods from here that is needed in user_interface.py that is native to all
# however, Directory_Manager is okay. we'll do this rewriting AFTER completing all todos in user_interface.py
class Directory_Point:
    """
    File's path with some information like file extension, date modified, and size.
    
    Attributes:
        path: Path to the file.
        file_name: File name.
        extension: File extension; ex. .txt, .exe, .doc
        date_modified: Date of when the file was last modified.
        size: Size of file (may not be accurate).
    """
    _time_format_str = "%m/%d/%Y %I:%M %p"
    _file_size_suffixes = [
        "KB","MB","GB","TB","PB","EB","ZB","YB",
    ]
    _BYTES_MULTIPLE_CONST = 1024
    _IS_DIRECTORY_KEY = "Folder"
    _IS_DRIVE_KEY = "Drive"
    _IS_FILE_KEY = "File"

    def __init__(self, path: str = "", file_name: str = "", extension: str = "", date_modified: float = 0.0, size: int = -1):
        self.path = path
        self.file_name = file_name

        self.extension = extension
        self.date_modified = date_modified
        self.size = size

    def point_is_folder(self):
        return self.extension == Directory_Point._IS_DIRECTORY_KEY
    
    def get_abs_path(self):
        # Returns most accurate OS path to the file.
        return os.path.join(self.path, self.file_name)
    
    def get_date_modified_str(self):
        return datetime.datetime.fromtimestamp(self.date_modified).strftime(Directory_Point._time_format_str)
    
    def get_size_str(self):
        # Returns the size of the file under a suffix if neccessary.
        amt_after_multiple = self.size
        for multiple in Directory_Point._file_size_suffixes:
            amt_after_multiple = amt_after_multiple / Directory_Point._BYTES_MULTIPLE_CONST
            if amt_after_multiple <= Directory_Point._BYTES_MULTIPLE_CONST:
                return f"{amt_after_multiple:.2f} {multiple}"
            
    def __str__(self):
        # FOR DEBUGGING PURPOSES.
        return f"{self.get_abs_path()}, date modified: {self.get_date_modified_str()}, size: {self.get_size_str()}"
    
class Directory_Manager:
    """
    Class to encapsulate all directory managing logic (including the tampering of class: Directory_Point).
    """
    current_directory = _default_directory
    current_directory_path = None

    # stores paths for navigation, so that we can use the backwards/forwards buttons.
    navigated_paths = [current_directory]
    navigated_paths_index = 0

    @staticmethod
    def get_default_directory():
        return _default_directory

    @staticmethod
    def get_dir_ui_file(ui_file_name):
        return os.path.join(_resource_directory, ui_file_name)

    # MUST INCLUDE FILE EXTENSION.
    @staticmethod
    def get_dir_image_from_icons(image_file_name):
        return os.path.join(_resource_directory, "icons", image_file_name)
    
    @staticmethod
    def dir_is_read_accessible(path):
        return os.access(path, os.W_OK)
    
    # list_obj -> list of str(s)
    @staticmethod
    def split_path_into_list(directory):
        path_list = [path for path in os.path.normpath(directory).split(os.sep)]

        # handle error scenario for if any elements in the path list is somehow empty (causes errors)
        index = len(path_list)-1
        while (index > 0 and path_list[index] == ""):
            path_list.pop()
            index -= 1

        return path_list
    
    @staticmethod
    def path_list_shows_only_drive(path_list):
        return len(path_list) == 1
    
    @staticmethod
    def current_directory_is_drives():
        return Directory_Manager.current_directory == drives_directory
    
    @staticmethod
    def compile_list_into_path(path_list):
        if Directory_Manager.path_list_shows_only_drive(path_list):
            return path_list[0] + os.sep
        return (os.sep).join(path_list)
    
    @staticmethod
    def update_current_directory(new_dir: str):
        Directory_Manager.current_directory = new_dir
        Directory_Manager.current_directory_path = Directory_Manager.split_path_into_list(Directory_Manager.current_directory)

    @staticmethod
    def update_to_new_directory(new_dir: str):
        if Directory_Manager.navigated_paths_index < len(Directory_Manager.navigated_paths) and Directory_Manager.navigated_paths[Directory_Manager.navigated_paths_index] == Directory_Manager.current_directory:
            Directory_Manager.navigated_paths = Directory_Manager.navigated_paths[:Directory_Manager.navigated_paths_index+1]
        Directory_Manager.update_current_directory(new_dir)

        # conditional edge case where user could enter the same directory after the directory was added to navigated_paths (at the end) and press enter and it would add the directory, even though it already exists at the end, adding redundancy.
        if Directory_Manager.navigated_paths[Directory_Manager.navigated_paths_index] != Directory_Manager.current_directory:
            Directory_Manager.navigated_paths.append(Directory_Manager.current_directory)
            Directory_Manager.navigated_paths_index = len(Directory_Manager.navigated_paths)-1

    @staticmethod
    def can_navigate_backwards():
        return Directory_Manager.navigated_paths_index > 0

    @staticmethod
    def can_navigate_forwards():
        return Directory_Manager.navigated_paths_index+1 < len(Directory_Manager.navigated_paths) and len(Directory_Manager.navigated_paths) > 0
    
    @staticmethod
    def navigate_backwards():
        Directory_Manager.navigated_paths_index -= 1
        Directory_Manager.update_current_directory(Directory_Manager.navigated_paths[Directory_Manager.navigated_paths_index])

    @staticmethod
    def navigate_forwards():
        Directory_Manager.navigated_paths_index += 1
        Directory_Manager.update_current_directory(Directory_Manager.navigated_paths[Directory_Manager.navigated_paths_index])

    @staticmethod
    def navigate_upwards():
        if Directory_Manager.path_list_shows_only_drive(Directory_Manager.current_directory_path):
            Directory_Manager.current_directory = drives_directory
            Directory_Manager.current_directory_path = Directory_Manager.split_path_into_list(Directory_Manager.current_directory)
        else:
            Directory_Manager.current_directory_path.pop()
            Directory_Manager.current_directory = Directory_Manager.compile_list_into_path(Directory_Manager.current_directory_path)
            
        Directory_Manager.navigated_paths.append(Directory_Manager.current_directory)
        Directory_Manager.navigated_paths_index = len(Directory_Manager.navigated_paths)-1
    
    @staticmethod
    def get_list_of_files(directory):
        directory_list = None

        if directory == drives_directory:
            directory_list = get_list_of_drives_available()
        elif not os.path.exists(directory) or not os.path.isdir(directory):
            return []
        else:
            directory_list = os.listdir(directory)

        list_of_files = []
        for cur_file_name in directory_list:
            full_directory = os.path.join(directory, cur_file_name)
            dir_point = Directory_Point(directory, cur_file_name)
            attempt_access_as_dir = None

            if directory == drives_directory:
                dir_point.extension = Directory_Point._IS_DRIVE_KEY
            elif os.path.isfile(full_directory):
                extension_dot_index = cur_file_name.rfind(".")
                dir_point.extension = cur_file_name[extension_dot_index:] if extension_dot_index != -1 else Directory_Point._IS_FILE_KEY
            else:
                try:
                    attempt_access_as_dir = os.listdir(full_directory)
                except Exception:
                    attempt_access_as_dir = None
                finally:
                    if attempt_access_as_dir is None:
                        continue
                dir_point.extension = Directory_Point._IS_DIRECTORY_KEY
                
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

def is_dir_given_path(directory):
    return os.path.isdir(directory)

def convert_to_path_str(string):
    if string[len(string)-1] != os.sep:
        return os.path.normpath(string) + os.sep
    return os.path.normpath(string)

def get_open_file_explorer_command():
    file_explorer_dir = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
    cur_dir = os.path.normpath(Directory_Manager.current_directory)
    return [file_explorer_dir, cur_dir]

# RETURNS LIST OF vars_util.Directory_Point objects.
def get_files_in_cur_directory(search_string : str = ""):
    cur_dir = Directory_Manager.current_directory
    list_of_files = Directory_Manager.get_list_of_files(cur_dir)
    return list_of_files
    
def get_abs_path(file_name):
    # Returns most accurate OS path to the file.
    return os.path.join(Directory_Manager.current_directory, file_name)

def get_size_str(size):
    _file_size_suffixes = [
        "KB","MB","GB","TB","PB","EB","ZB","YB",
    ]

    # Returns the size of the file under a suffix if neccessary.
    amt_after_multiple = size
    for multiple in Directory_Point._file_size_suffixes:
        amt_after_multiple = amt_after_multiple / Directory_Point._BYTES_MULTIPLE_CONST
        if amt_after_multiple <= Directory_Point._BYTES_MULTIPLE_CONST:
            return f"{amt_after_multiple:.2f} {multiple}"
        
def get_list_of_drives_available():
    # (device, mountpoint, fstype, opts)
    return [convert_to_path_str(partition.device) for partition in psutil.disk_partitions()]
        
def get_total_storage_data():
    total, used, free = 0, 0, 0
    for drive in get_list_of_drives_available():
        storage_data = get_storage_data(drive)
        total += storage_data[0]
        used += storage_data[1]
        free += storage_data[2]
    return (total, used, free)

def get_storage_data(path):
    total, used, free = shutil.disk_usage(path) # i might use this
    return (total, used, free)
    
def get_storage_display_data(path):
    # returns value for SetValue in progress_bar_storage and a text for setText in display_storage
    storage_data = None
    s_format = ""

    if path == drives_directory:
        storage_data = get_total_storage_data()
        s_format = f"Overall: {get_size_str(storage_data[2])} free of {get_size_str(storage_data[0])}"
    else:
        storage_data = get_storage_data(path)
        s_format = f"{convert_to_path_str(Directory_Manager.current_directory_path[0]).strip('\\')}// {get_size_str(storage_data[2])} free of {get_size_str(storage_data[0])}"
    
    percentage = int((storage_data[1]/storage_data[0])*100)

    return (percentage, s_format)