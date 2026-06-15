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

_work_directory = os.path.dirname(__file__)[:-len("src")]
_resource_directory = os.path.join(_work_directory, "resource")
_default_directory = os.path.abspath(os.sep)

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
        Directory_Manager.current_directory_path.pop()
        Directory_Manager.current_directory = Directory_Manager.compile_list_into_path(Directory_Manager.current_directory_path)

        Directory_Manager.navigated_paths.append(Directory_Manager.current_directory)
        Directory_Manager.navigated_paths_index = len(Directory_Manager.navigated_paths)-1
    
    @staticmethod
    def get_list_of_files(directory):
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return []
        
        list_of_files = []
        for cur_file_name in os.listdir(directory):
            dir_point = Directory_Point(directory, cur_file_name)

            if os.path.isfile(os.path.join(directory, cur_file_name)):
                dir_point.extension = cur_file_name[cur_file_name.index("."):]
            else:
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
    