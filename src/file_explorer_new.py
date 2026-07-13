"""
Handles the main functionality of the File Explorer; file management such as:
    * Moving files/folders
    * Navigating through files/folders
    * Opening files/folders
    and more...

This also manages paths.

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

# used for project handling
_work_path: str = os.path.dirname(__file__)[:-len("src")]

# 
_resource_path: str = os.path.join(_work_path, "resource")
drives_path_name: str = "Drives" # custom name
_default_path: str = drives_path_name
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
class Entry:
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

class Path_Manager:
    """
    Class to encapsulate all path managing logic (including the tampering of class: Directory_Point).

    REDO THIS
    """
    _current_path: str = _default_path
    """
    I'm so bad at explaining this but:
        * pairs with split_path_into_list()
        * ex. current_path = C:\Alpha\Bravo\Charlie\Delta
        * then: current_path_compiled = ["C:\\", "Alpha", "Bravo", "Charlie", "Delta"]
    """
    current_path_compiled: list[str] = None

    # holds data about past navigated directories
    navigated_paths: list[str] = [_default_path]
    navigated_paths_index: int = 0

    entry_list_of_path: list[Entry] = []

    """
        * Property Handling
    """
    @property
    def current_path(cls) -> str:
        return cls._current_path
    
    @current_path.setter
    def current_path(cls, new_current_path):
        cls.current_path = new_current_path
        cls.current_path_compiled = cls.split_path_into_list(cls.current_path)

    """
        * Path Handling Logic Functions
    """
    @classmethod
    def split_path_into_list(cls, path: list[str]) -> list[str]:
        path_list = [path_node for path_node in os.path.normpath(path).split(os.sep)]

        # handle error scenario for if any elements in the path list is somehow empty (causes errors)
        index = len(path_list)-1
        while (index > 0 and path_list[index] == ""):
            path_list.pop()
            index -= 1

        return path_list
    
    @classmethod
    def path_list_shows_only_drive(cls, path_list: list[str]) -> bool:
        return len(path_list) == 1

    @classmethod
    def convert_list_to_path(cls, path_list: list[str]) -> str:
        if cls.path_list_shows_only_drive(path_list):
            return path_list[0] + os.sep
        return (os.sep).join(path_list)
    
    @classmethod
    def convert_str_to_path(cls, string: str) -> str:
        if string[len(string)-1] != os.sep:
            return os.path.normpath(string) + os.sep
        return os.path.normpath(string)

    @classmethod
    def get_abs_path(cls, file_name: str) -> str:
        # Returns most accurate OS path to the file.
        return os.path.join(cls.current_path, file_name)

    @classmethod
    def can_navigate_upwards(cls) -> bool:
        return cls.current_path != drives_path_name
    
    @classmethod
    def can_navigate_backwards(cls) -> bool:
        return cls.navigated_paths_index > 0

    @classmethod
    def can_navigate_forwards(cls) -> bool:
        return cls.navigated_paths_index+1 < len(cls.navigated_paths) and len(cls.navigated_paths) > 0
    
    @classmethod
    def navigate_backwards(cls) -> None:
        cls.navigated_paths_index -= 1
        cls.current_path = cls.navigated_paths[cls.navigated_paths_index]

    @classmethod
    def navigate_forwards(cls) -> None:
        cls.navigated_paths_index += 1
        cls.current_path = cls.navigated_paths[cls.navigated_paths_index]

    @classmethod
    def navigate_upwards(cls) -> None:
        if cls.path_list_shows_only_drive(cls.current_path_compiled):
            cls.current_path = drives_path_name
        else:
            cls.current_path_compiled.pop()
            cls.current_path = cls.convert_list_to_path(cls.current_path_compiled)
            
        cls.navigated_paths.append(cls.current_path)
        cls.navigated_paths_index = len(cls.navigated_paths)-1

    """
        * Directory Logic
    """
    @classmethod
    def update_current_path(cls, new_dir: str):
        cls.current_directory = new_dir
        cls.current_directory_path = cls.split_path_into_list(cls.current_directory)

    @classmethod
    def update_to_new_path(cls, new_dir: str):
        if cls.navigated_paths_index < len(cls.navigated_paths) and cls.navigated_paths[cls.navigated_paths_index] == cls.current_directory:
            cls.navigated_paths = cls.navigated_paths[:cls.navigated_paths_index+1]
        cls.update_current_directory(new_dir)

        # conditional edge case where user could enter the same directory after the directory was added to navigated_paths (at the end) and press enter and it would add the directory, even though it already exists at the end, adding redundancy.
        if cls.navigated_paths[cls.navigated_paths_index] != cls.current_directory:
            cls.navigated_paths.append(cls.current_directory)
            cls.navigated_paths_index = len(cls.navigated_paths)-1
    
    # make it so that you can also try checking the str
    @staticmethod
    def entry_is_folder(dir_data: Directory) -> bool:
        return dir_data.extension == _directory_extension
    
    # make it so that you can also try checking the str
    @staticmethod
    def entry_is_drive(dir_data: Directory) -> bool:
        return dir_data.extension == _drive_extension
    
    # make it so that you can also try checking the str
    @staticmethod
    def entry_is_file(dir_data: Directory) -> bool:
        return dir_data.extension == _file_extension
    
    @staticmethod
    def path_is_read_accessible(path):
        # use this as ref lowk im not making this a method
        return os.access(path, os.R_OK)
    
    # UNFINISHED
    @classmethod
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
    current_path_compiled = split_path_into_list(current_directory)

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

class UI_Display_Utility:
    """ Utility Class storing methods that utilize data to display information in a user-friendly manner. """
    @staticmethod
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
    
    @staticmethod
    def get_total_storage_data():
        total, used, free = 0, 0, 0
        for drive in get_list_of_drives_available():
            storage_data = get_storage_data(drive)
            total += storage_data.total
            used += storage_data.used
            free += storage_data.free
        return (total, used, free)
    
    @staticmethod
    def get_file_description(path, extension):
        if extension == "Drive":
            return f"{extension}\n\nA storage volume that contains files and folders."
        elif extension == "Folder":
            return f"{extension}\n\nA container used to organize files and subfolders in a filesystem."
        try:
            description = magic.from_file(path)
            if description == "data":
                description = "Unknown data file; No description can be provided."
            return f"{extension}\n\n{description}"
        except:
            return f"{extension}\n\nUnknown file; No description can be provided."
    
    # RENAME METHOD
    @staticmethod
    def get_storage_display_data(path):
        # returns value for SetValue in progress_bar_storage and a text for setText in display_storage
        storage_data = None
        s_format = ""

        if path == drives_directory:
            storage_data = get_total_storage_data()
            s_format = f"Overall: {get_size_str(storage_data[2])} free of {get_size_str(storage_data[0])}"
        else:
            storage_data = get_storage_data(path)
            s_format = f"{convert_to_path_str(Directory_Manager.current_directory_path[0]).strip('\\')}// {get_size_str(storage_data.free)} free of {get_size_str(storage_data.total)}"
        
        percentage = int((storage_data[1]/storage_data[0])*100)

        return (percentage, s_format)

class Utility:
    """
    IMPLEMENTED VALIDS
    """
    @staticmethod
    def get_open_file_explorer_command():
        file_explorer_dir = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        cur_dir = os.path.normpath(Directory_Manager.current_directory)
        return [file_explorer_dir, cur_dir]

    def get_list_of_drives_available():
        # (device, mountpoint, fstype, opts)
        return [convert_to_path_str(partition.device) for partition in psutil.disk_partitions()]
            