"""
Handles the main functionality of the File Explorer; file management such as:
    * Moving files/folders
    * Navigating through files/folders
    * Opening files/folders
    and more...

This also manages directories.

Todo:
    * Implement opening files
    * Refactor
        STEP 1: Move everything.
        STEP 2: Rename variables.
"""

from dataclasses import dataclass
import os
import datetime
import src.configuration
import shutil
import psutil
import magic

_work_directory = os.path.dirname(__file__)[:-len("src")]
_resource_directory = os.path.join(_work_directory, "resource")
drives_directory: str = "Drives" # custom name
_default_directory: str = drives_directory
_ui_src_file_name: str = "ui_source.ui"

_directory_extension: str = "Folder"
_drive_extension: str = "Drive"
_file_extension: str = "File"

_time_format_str: str = "%m/%d/%Y %I:%M %p"
_file_size_suffixes: list[str] = [
        "KB","MB","GB","TB","PB","EB","ZB","YB",
    ]
_BYTES_MULTIPLE_CONST: int = 1024

@dataclass
class Directory:
    """
    An object based on the directory provided with some basic information like file extension, date modified, and size.

    Attributes:
        path: Path to the file.
        file_name: File name.
        extension: File extension; ex. .txt, .exe, .doc
        date_modified: Date of when the file was last modified.
            * This is defined as a float, provided by os.stat(<>).st_mtime, which is converted back by gate_date_modified_str.
        size: Size of file (may not be accurate).
    """
    path: str = ""
    file_name: str = ""
    extension: str = ""
    date_modified: float = 0.0
    size: int = -1

    def get_date_modified_str(self) -> str:
        return datetime.datetime.fromtimestamp(self.date_modified).strftime(_time_format_str)

    def __str__(self) -> str:
        # FOR DEBUGGING PURPOSES.
        return f"{self.path}, date modified: {self.get_date_modified_str()}, size: {self.size}"

class Directory_Manager:
    """
    Class to encapsulate all directory managing logic (including the tampering of class: Directory_Point).


    """
    current_directory: str = _default_directory
    current_directory_path: list[str] = None

    # stores paths for navigation, so that we can use the backwards/forwards buttons.
    navigated_paths: list[str] = [current_directory]
    navigated_paths_index: int = 0

    directory_list_of_cur_dir: list[Directory] = []

    """
        * Path Handling Logic Functions
    """
    @classmethod
    @staticmethod
    def split_path_into_list(cls, directory: list[str]) -> list:
        path_list = [path for path in os.path.normpath(directory).split(os.sep)]

        # handle error scenario for if any elements in the path list is somehow empty (causes errors)
        index = len(path_list)-1
        while (index > 0 and path_list[index] == ""):
            path_list.pop()
            index -= 1

        return path_list
    
    @classmethod
    @staticmethod
    def path_list_shows_only_drive(cls, path_list):
        return len(path_list) == 1

    @classmethod
    @staticmethod
    def compile_list_into_path(cls, path_list):
        if cls.path_list_shows_only_drive(path_list):
            return path_list[0] + os.sep
        return (os.sep).join(path_list)

    @classmethod
    @staticmethod
    def can_navigate_upwards(cls):
        return cls.current_directory != drives_directory
    
    @classmethod
    @staticmethod
    def can_navigate_backwards(cls):
        return cls.navigated_paths_index > 0

    @classmethod
    @staticmethod
    def can_navigate_forwards(cls):
        return cls.navigated_paths_index+1 < len(cls.navigated_paths) and len(cls.navigated_paths) > 0
    
    @classmethod
    @staticmethod
    def navigate_backwards(cls):
        cls.navigated_paths_index -= 1
        cls.update_current_directory(cls.navigated_paths[cls.navigated_paths_index])

    @classmethod
    @staticmethod
    def navigate_forwards(cls):
        cls.navigated_paths_index += 1
        cls.update_current_directory(cls.navigated_paths[cls.navigated_paths_index])

    @classmethod
    @staticmethod
    def navigate_upwards(cls):
        if cls.path_list_shows_only_drive(cls.current_directory_path):
            cls.current_directory = drives_directory
            cls.current_directory_path = cls.split_path_into_list(cls.current_directory)
        else:
            cls.current_directory_path.pop()
            cls.current_directory = cls.compile_list_into_path(cls.current_directory_path)
            
        cls.navigated_paths.append(cls.current_directory)
        cls.navigated_paths_index = len(cls.navigated_paths)-1

    """
        * Directory Logic
    """
    @classmethod
    @staticmethod
    def update_current_directory(cls, new_dir: str):
        Directory_Manager.current_directory = new_dir
        Directory_Manager.current_directory_path = Directory_Manager.split_path_into_list(Directory_Manager.current_directory)

    @classmethod
    @staticmethod
    def update_to_new_directory(cls, new_dir: str):
        if Directory_Manager.navigated_paths_index < len(Directory_Manager.navigated_paths) and Directory_Manager.navigated_paths[Directory_Manager.navigated_paths_index] == Directory_Manager.current_directory:
            Directory_Manager.navigated_paths = Directory_Manager.navigated_paths[:Directory_Manager.navigated_paths_index+1]
        Directory_Manager.update_current_directory(new_dir)

        # conditional edge case where user could enter the same directory after the directory was added to navigated_paths (at the end) and press enter and it would add the directory, even though it already exists at the end, adding redundancy.
        if Directory_Manager.navigated_paths[Directory_Manager.navigated_paths_index] != Directory_Manager.current_directory:
            Directory_Manager.navigated_paths.append(Directory_Manager.current_directory)
            Directory_Manager.navigated_paths_index = len(Directory_Manager.navigated_paths)-1
    
    @classmethod
    @staticmethod
    def get_list_of_files(cls, directory):
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

            # get date modified and size
            file_statistics = os.stat(dir_point.get_abs_path())
            file_modified_time = file_statistics.st_mtime
            file_size = file_statistics.st_size

            if directory == drives_directory:
                dir_point.extension = Directory_Point._IS_DRIVE_KEY
                file_size = get_storage_data(full_directory).total
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

            dir_point.date_modified = file_modified_time
            dir_point.size = file_size

            list_of_files.append(dir_point)
        return list_of_files
    
    # setup definitions for Directory_Manager variables if the methods above are required.
    current_directory_path = split_path_into_list(current_directory)

class Resource_File_Getter:
    """ Utility Class to allow files from resource folder to be utilized. """
    @classmethod
    def __new__(cls):
        raise TypeError("class: Resource_File_Getter has permissions from __new__: CANNOT BE CREATED")

    @staticmethod
    def get_dir_ui_file():
        return os.path.join(_resource_directory, _ui_src_file_name)
    
    @staticmethod
    def get_dir_image_from_icons(image_file_name: str):
        """WARNING: image_file_name must include extension."""
        _, extension = os.path.splitext(image_file_name)
        assert extension != "" or image_file_name.rfind(".") != -1, "class: Resource_File_Getter from get_dir_image_from_icons: NO FILE EXTENSION DETECTED FOR 'image_file_name'"
        return os.path.join(_resource_directory, "icons", image_file_name)

def directory_is_folder(dir_data: Directory) -> bool:
    return dir_data.extension == _directory_extension

def directory_is_drive(dir_data: Directory) -> bool:
    return dir_data.extension == _drive_extension

def directory_is_file(dir_data: Directory) -> bool:
    return dir_data.extension == _file_extension

def directory_is_read_accessible(path):
    # use this as ref lowk im not making this a method
    return os.access(path, os.R_OK)
