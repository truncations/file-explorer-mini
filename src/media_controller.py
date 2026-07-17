"""
lets work on this after QSortProxy

we'll have to modify the multithreader to add the file into this list made in this python file
IF the file we look at or the entry is a media file so that we don't have to recompute for another for loop

NOTE: QVideoWidget is also a widget and is not supported in QT Designer by default so you will need to
code the widgets/UI implementation before implementing a media controller.
"""

from dataclasses import dataclass
import src.file_explorer_manager as file_explorer_manager

@dataclass
class Media_Controller:
    selected_file_name: str = ""

    @classmethod
    def get_type_of_media(cls, full_file_name: str | None = None):
        if not full_file_name:
            full_file_name = cls.selected_file_name
        return file_explorer_manager.Path_Manager.get_guess_type(full_file_name)

