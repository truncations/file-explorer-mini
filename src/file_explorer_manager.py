"""
Handles the main functionality of the File Explorer; file management such as:
    * Moving files/folders
    * Navigating through files/folders
    * Opening files/folders
    and more...

This also manages paths.
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
    Path management class to handle logic with paths, and whatnot.

    Attributes:
        current_path
        current_path_compiled: Splits current_path into file_names by delimiter \\.
        navigated_paths
        navigated_paths_index: Index of current_path in navigated_paths (to make navigation like forwards/backwards functional)
        entry_list_of_path: List of entries (files/folders) of a path.
    """
    current_path: str = _default_path
    """
    I'm so bad at explaining this but:
        * pairs with split_path_into_list()
        * ex. current_path = C:\\Alpha\\Bravo\\Charlie\\Delta
        * then: current_path_compiled = ["C:", "Alpha", "Bravo", "Charlie", "Delta"]
    """
    current_path_compiled: list[str] = None

    # holds data about past navigated directories
    navigated_paths: list[str] = [_default_path]
    navigated_paths_index: int = 0

    entry_list_of_path: list[Entry] = []

    """
        * Property Handling
    """
    @classmethod
    def update_current_path(cls, new_current_path) -> str:
        cls.current_path = new_current_path
        cls.current_path_compiled = cls.split_path_into_list(cls.current_path)
        
    """
        * Path Handling Logic Functions
    """
    @classmethod
    def split_path_into_list(cls, path: str) -> list[str]:
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
    def is_current_path_drives(cls) -> bool:
        return cls.current_path == drives_path_name

    @classmethod
    def navigate_backwards(cls) -> None:
        cls.navigated_paths_index -= 1
        cls.update_current_path(cls.navigated_paths[cls.navigated_paths_index])

    @classmethod
    def navigate_forwards(cls) -> None:
        cls.navigated_paths_index += 1
        cls.update_current_path(cls.navigated_paths[cls.navigated_paths_index])

    @classmethod
    def navigate_upwards(cls) -> None:
        if cls.path_list_shows_only_drive(cls.current_path_compiled):
            cls.update_current_path(drives_path_name)
        else:
            cls.current_path_compiled.pop()
            cls.update_current_path(cls.convert_list_to_path(cls.current_path_compiled))
            
        if cls.navigated_paths[cls.navigated_paths_index] != cls.current_path:
            cls.navigated_paths.append(cls.current_path)
            cls.navigated_paths_index = len(cls.navigated_paths)-1

    @classmethod
    def update_to_new_path(cls, new_path: str) -> None:
        if cls.navigated_paths_index < len(cls.navigated_paths) and cls.navigated_paths[cls.navigated_paths_index] == cls.current_path:
            cls.navigated_paths = cls.navigated_paths[:cls.navigated_paths_index+1]
        cls.update_current_path(new_path)

        # conditional edge case where user could enter the same directory after the directory was added to navigated_paths (at the end) and press enter and it would add the directory, even though it already exists at the end, adding redundancy.
        if cls.navigated_paths[cls.navigated_paths_index] != cls.current_path:
            cls.navigated_paths.append(cls.current_path)
            cls.navigated_paths_index = len(cls.navigated_paths)-1
    
    @staticmethod
    def entry_is_folder(entry_data: Entry) -> bool:
        return entry_data.extension == _directory_extension
    
    @staticmethod
    def entry_is_drive(entry_data: Entry) -> bool:
        return entry_data.extension == _drive_extension
    
    @staticmethod
    def entry_is_file(entry_data: Entry) -> bool:
        return entry_data.extension == _file_extension
    
    @staticmethod
    def path_is_folder(path: str) -> bool:
        return os.path.isdir(path)
    
    @staticmethod
    def path_is_read_accessible(path) -> bool:
        # use this as ref lowk im not making this a method
        return os.access(path, os.R_OK)
    
    @classmethod
    def get_list_of_entries_in_cur_path(cls) -> list[Entry]:
        return cls.get_list_of_entries(cls.current_path)

    @classmethod
    def get_list_of_entries(cls, path: str) -> list[Entry]:
        obj_list_of_path = None

        if path == drives_path_name:
            obj_list_of_path = Utility.get_paths_of_drives_available()
        elif not os.path.exists(path) or not os.path.isdir(path):
            obj_list_of_path = []
        else:
            obj_list_of_path = os.listdir(path)

        list_of_files = []
        for cur_file_name in obj_list_of_path:
            full_path_to_file = os.path.join(path, cur_file_name)
            new_entry = Entry()

            # get date modified and size
            file_statistics = os.stat(cls.get_abs_path(full_path_to_file))
            file_modified_time = file_statistics.st_mtime
            file_size = file_statistics.st_size

            if path == drives_path_name:
                # assume all entries are drives
                new_entry.extension = _drive_extension
                file_size = shutil.disk_usage(full_path_to_file).total
            elif os.path.isfile(full_path_to_file):
                extension_dot_index = cur_file_name.rfind(".")
                new_entry.extension = cur_file_name[extension_dot_index:] if extension_dot_index != -1 else _file_extension
            else: # we know its a directory so can we read it?
                try:
                    with os.scandir(full_path_to_file) as test:
                        pass
                except:
                    continue
                new_entry.extension = _directory_extension

            new_entry.file_name = cur_file_name
            new_entry.date_modified = file_modified_time
            new_entry.size = file_size

            list_of_files.append(new_entry)

        cls.entry_list_of_path = list_of_files[:]
        return cls.entry_list_of_path

class Resource_File_Getter:
    """ Utility Class to allow files from resource folder to be utilized. """
    @classmethod
    def __new__(cls):
        raise TypeError("class: Resource_File_Getter has permissions from __new__: CANNOT BE CREATED")

    @staticmethod
    def get_dir_ui_file() -> None:
        return os.path.join(_resource_path, _ui_src_file_name)
    
    @staticmethod
    def get_path_to_img(image_file_name: str) -> str:
        """WARNING: image_file_name must include extension."""
        _, extension = os.path.splitext(image_file_name)
        assert extension != "" or image_file_name.rfind(".") != -1, "class: Resource_File_Getter from get_dir_image_from_icons: NO FILE EXTENSION DETECTED FOR 'image_file_name'"
        return os.path.join(_resource_path, "icons", image_file_name)

class UI_Display_Utility:
    """ Utility Class storing methods that utilize data to display information in a user-friendly manner. """
    @staticmethod
    def get_size_str(size) -> str:
        _file_size_suffixes = [
            "KB","MB","GB","TB","PB","EB","ZB","YB",
        ]

        # Returns the size of the file under a suffix if neccessary.
        amt_after_multiple = size
        for multiple in _file_size_suffixes:
            amt_after_multiple = amt_after_multiple / _BYTES_MULTIPLE_CONST
            if amt_after_multiple <= _BYTES_MULTIPLE_CONST:
                return f"{amt_after_multiple:.2f} {multiple}"
    
    @staticmethod
    def get_total_storage_data() -> tuple:
        total, used, free = 0, 0, 0
        for drive in Utility.get_paths_of_drives_available():
            storage_data = shutil.disk_usage(drive)
            total += storage_data.total
            used += storage_data.used
            free += storage_data.free
        return (total, used, free)
    
    @staticmethod
    def get_file_description(path, extension) -> str:
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
    def get_storage_display_data(path) -> tuple[int, str]:
        # returns value for SetValue in progress_bar_storage and a text for setText in display_storage
        storage_data = None
        s_format = ""

        if path == drives_path_name:
            storage_data = UI_Display_Utility.get_total_storage_data()
            s_format = f"Overall: {UI_Display_Utility.get_size_str(storage_data[2])} free of {UI_Display_Utility.get_size_str(storage_data[0])}"
        else:
            storage_data = shutil.disk_usage(path)
            s_format = f"{Path_Manager.convert_str_to_path(Path_Manager.current_path_compiled[0]).strip('\\')}// {UI_Display_Utility.get_size_str(storage_data.free)} free of {UI_Display_Utility.get_size_str(storage_data.total)}"
        
        percentage = int((storage_data[1]/storage_data[0])*100)

        return (percentage, s_format)

class Utility:
    """
    IMPLEMENTED VALIDS
    """
    @staticmethod
    def get_open_file_explorer_command() -> tuple[str, str]:
        file_explorer_dir = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        cur_dir = os.path.normpath(Path_Manager.current_path)
        return (file_explorer_dir, cur_dir)

    def get_paths_of_drives_available() -> list[str]:
        # (device, mountpoint, fstype, opts)
        return [Path_Manager.convert_str_to_path(partition.device) for partition in psutil.disk_partitions()]

    def open_file(path: str) -> None:
        try:
            os.startfile(path)
        except:
            pass

# setup definitions for Directory_Manager variables if the methods above are required.
Path_Manager.current_path_compiled = Path_Manager.split_path_into_list(Path_Manager.current_path)