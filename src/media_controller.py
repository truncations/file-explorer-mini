"""
lets work on this after QSortProxy

we'll have to modify the multithreader to add the file into this list made in this python file
IF the file we look at or the entry is a media file so that we don't have to recompute for another for loop

NOTE: QVideoWidget is also a widget and is not supported in QT Designer by default so you will need to
code the widgets/UI implementation before implementing a media controller.
"""

from enum import Enum
from typing import NamedTuple
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtCore import Qt, QSize, QUrl, pyqtSignal, pyqtSlot, QModelIndex, QObject
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
import src.file_explorer_manager as file_explorer_manager
import src.configuration as configuration
import random

class Loop_States(Enum):
    NOT_LOOPING = 1
    LOOPING_MEDIA_LIST = 2
    LOOPING_SINGLE_ENTRY = 3

class Media_File_Types(Enum):
    NONE = -1
    IMAGE = 0
    VIDEO = 1
    AUDIO = 2

class Media_List_Item(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.assigned_id: int = -1 # for shuffling
    
    def __lt__(self, other: QListWidgetItem):
        if Media_Controller_States.media_shuffle_enabled:
            return self.assigned_id < other.assigned_id
        else:
            return self.text() < other.text()
        
class Media_Controller_States:
    """
    Stores Media Controller states that can be used in any other classes.
    """
    media_shuffle_enabled: bool = False
    is_playing_media: bool = False
    loop_state: Loop_States = Loop_States.NOT_LOOPING
    stored_volume: int = configuration.Media_Config.default_volume # prevent resetting audio to 100 for each

class Media_Controller(QObject):
    _signal_add_to_media_list: pyqtSignal = pyqtSignal(file_explorer_manager.Entry)
   
    """
    Class Definitions
        * Properties
            ^^ includes methods that are exclusively part of the property
        * Magic Methods
        * ect.
    """
    @property
    def selected_file_name(self):
        return self._selected_file_name
    
    @selected_file_name.setter
    def selected_file_name(self, new_file_name):
        self._selected_file_name = new_file_name
        self._get_type_of_media()

    def _get_type_of_media(self, full_file_name: str | None = None):
        if not full_file_name:
            full_file_name = self.selected_file_name
        if not self.selected_file_name:
            return
        guess_type = file_explorer_manager.Path_Manager.get_guess_type(full_file_name)
        match guess_type:
            case "image":
                self.selected_file_type = Media_File_Types.IMAGE
            case "video":
                self.selected_file_type = Media_File_Types.VIDEO
            case "audio":
                self.selected_file_type = Media_File_Types.AUDIO
            case _:
                print("MEDIA FILE SOMEHOW NOT MEDIA FILE? by _get_type_of_media")
                self.selected_file_type = Media_File_Types.NONE

    def __init__(self, Main_Application_Pointer = None):
        super().__init__()

        self._selected_file_name: str | None = ""
        self.selected_file_type: Media_File_Types = Media_File_Types.NONE
        self.selected_file_metadata: QMediaMetaData | None = None

        self.states = Media_Controller_States
        self._cached_icons: dict[str, QIcon] = {}

        self._setup_QT_media_elements()
        self._map_all_needed_ui_elements(Main_Application_Pointer)
        self.setup_cached_icons_for_media()
        self.connect_signals_and_slots()

    """
    UI setup functions
    """
    def _setup_QT_media_elements(self) -> None:
        self.media_player_system: QMediaPlayer = QMediaPlayer()
        self.video_widget: QVideoWidget = QVideoWidget()
        self.audio_output: QAudioOutput = QAudioOutput()

        self.media_player_system.setVideoOutput(self.video_widget)
        self.media_player_system.setAudioOutput(self.audio_output)

    def _map_all_needed_ui_elements(self, Main_Application_Pointer) -> None:
        """
        Maps all needed Main_Application UI elements (to be used in this Media_Controller class)
        to this class with the self keyword.
        """
        if Main_Application_Pointer is None: return
        M_A_P = Main_Application_Pointer
        
        self.button_playstate = M_A_P.button_playstate
        self.media_entry_list = M_A_P.media_entry_list
        self.slider_setting = M_A_P.slider_setting
        self.slider_progress = M_A_P.slider_progress
        self.label_progress = M_A_P.label_progress
        self.label_setting = M_A_P.label_setting
        self.input_status_bar = M_A_P.input_status_bar
        self.media_scroller = M_A_P.media_scroller
        self.media_image_display = M_A_P.media_image_display
        self.button_forwards_media = M_A_P.button_forwards_media
        self.button_backwards_media = M_A_P.button_backwards_media
        self.button_loop = M_A_P.button_loop
        self.button_shuffle = M_A_P.button_shuffle

    def setup_cached_icons_for_media(self) -> None:
        self._cached_icons.update({"image": file_explorer_manager.Resource_File_Getter.get_path_to_img("image.png")})
        self._cached_icons.update({"audio": file_explorer_manager.Resource_File_Getter.get_path_to_img("music_note.png")})
        self._cached_icons.update({"video": file_explorer_manager.Resource_File_Getter.get_path_to_img("video.png")})

    def connect_signals_and_slots(self) -> None:
        self._signal_add_to_media_list.connect(self.add_to_media_list, Qt.ConnectionType.QueuedConnection)

        self.media_entry_list.itemClicked.connect(self.media_list_item_clicked)
        self.button_playstate.clicked.connect(self.playstate_button_clicked)
        self.media_player_system.positionChanged.connect(self.media_sys_progress_changed)
        self.media_player_system.durationChanged.connect(self.media_sys_duration_changed)
        self.media_player_system.metaDataChanged.connect(self.media_sys_metadata_changed)
        self.slider_progress.sliderPressed.connect(self.progress_slider_pressed)
        self.slider_progress.sliderMoved.connect(self.progress_slider_moved)
        self.slider_progress.sliderReleased.connect(self.progress_slider_released)
        self.slider_setting.sliderMoved.connect(self.setting_slider_moved)
        self.button_forwards_media.clicked.connect(self.forwards_clicked)
        self.button_backwards_media.clicked.connect(self.backwards_clicked)
        self.button_loop.clicked.connect(self.loop_clicked)
        self.button_shuffle.clicked.connect(self.shuffle_clicked)

    """
    Helper Functions/Utility Private Functions
    """
    def is_selected_file_playable(self) -> bool:
        return self.selected_file_type in [Media_File_Types.VIDEO, Media_File_Types.AUDIO]

    """
    UI updating functions
        * Updates visual elements
    """
    def update_display(self, path_to_media_file: str, entry_file_name: str | None = None):
        self.clear_display_media()
        self.selected_file_name = path_to_media_file
        self.slider_progress.setMaximum(0)
        
        # occurs when double clicking on an item and we want to select this/highlight this
        if entry_file_name:
            item = self.media_entry_list.findItems(entry_file_name, Qt.MatchFlag.MatchCaseSensitive)[0]
            if item:
                index = self.media_entry_list.indexFromItem(item)
                self.media_entry_list.setCurrentRow(index.row())

        self.stop_song()
        self.update_progress_label()

        if self.selected_file_type == Media_File_Types.IMAGE:
            self.update_display_img()
        elif self.selected_file_type == Media_File_Types.VIDEO:
            self.update_display_video()
        elif self.selected_file_type == Media_File_Types.AUDIO:
            self.update_display_audio()

    def update_display_img(self):
        if self.selected_file_name:
            self.video_widget.setVisible(False)
            self.media_scroller.setVisible(True)

            self.button_playstate.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("play.png")))
            self.update_setting_limits(new_val=100, new_max=configuration.Image_Config.max_zoom_scale_by_percentage)

            self.update_existing_img()

    def update_existing_img(self):
        if self.selected_file_name:
            pixmap: QPixmap = QPixmap(self.selected_file_name)
            zoom = self.slider_setting.value()/100
            self.load_image_to_display(pixmap, zoom)

    def update_display_video(self):
        if self.selected_file_name:
            self.update_setting_limits(self.states.stored_volume, 100)

            self.video_widget.setVisible(True)
            self.media_scroller.setVisible(False)
            self.media_player_system.setSource(QUrl.fromLocalFile(self.selected_file_name))

    def update_display_audio(self):
        if self.selected_file_name:
            self.update_setting_limits(self.states.stored_volume, 100)

            self.video_widget.setVisible(False)
            self.media_scroller.setVisible(True)
            self.media_player_system.setSource(QUrl.fromLocalFile(self.selected_file_name))

    def update_setting_limits(self, new_val: int, new_max: int):
        self.slider_setting.setValue(new_val)
        self.setting_slider_moved(new_val)
        self.slider_setting.setMaximum(new_max)

    def clear_display_media(self):
        self.selected_file_name = ""
        self.media_image_display.clear()

        self.media_player_system.setSource(QUrl())

    def play_song(self):
        if self.is_selected_file_playable():
            self._is_playing_media = True
            self.media_player_system.play()
            self.button_playstate.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("pause.png")))

    def pause_song(self):
        self._is_playing_media = False
        self.media_player_system.pause()
        self.button_playstate.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("play.png")))

    def stop_song(self):
        self._is_playing_media = False
        self.media_player_system.stop()
        self.button_playstate.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("play.png")))

    """
    Slots for signals provided by QWidget() objects
    OR events that have been subclassed.
    """
    def media_finished_trigger_check(self):
        if self.slider_progress.value() != self.slider_progress.maximum():
            return
        loop_state: Loop_States = self.states.loop_state
        if loop_state == Loop_States.NOT_LOOPING:
            self.media_player_system.setPosition(0)
            self.stop_song()
        elif loop_state == Loop_States.LOOPING_MEDIA_LIST:
            self.forwards_clicked()
            self.play_song()
        elif loop_state == Loop_States.LOOPING_SINGLE_ENTRY and self._is_playing_media:
            self.media_player_system.setPosition(0)
            self.play_song()

    def update_progress_label(self):
        max_duration = int(self.slider_progress.maximum()/1000)
        current_duration = int(self.slider_progress.value()/1000)

        md_hours, md_minutes, md_seconds = convert_num_to_time(max_duration)
        cd_hours, cd_minutes, cd_seconds = convert_num_to_time(current_duration)
        
        msg = None
        if cd_hours > 0:
            msg = f"{cd_hours:02d}:{cd_minutes:02d}:{cd_seconds:02d} / {md_hours:02d}:{md_minutes:02d}:{md_seconds:02d}"
        else:
            msg = f"{cd_minutes:02d}:{cd_seconds:02d} / {md_minutes:02d}:{md_seconds:02d}"
        self.label_progress.setText(msg)
    
    def media_list_item_clicked(self, item_clicked: QListWidgetItem):
        file_name = item_clicked.text()
        self.update_display(file_explorer_manager.Path_Manager.get_abs_path(file_name))

    def playstate_button_clicked(self):
        if not self.selected_file_name or not self.is_selected_file_playable():
            return

        self._is_playing_media = not self._is_playing_media

        if self._is_playing_media:
            self.media_play_song()
        else:
            self.media_pause_song()
            
    def media_sys_progress_changed(self, progress: int):
        if self.slider_progress.isSliderDown():
            return
        # audio/video finished.
        self.media_finished_trigger_check()
        self.slider_progress.setValue(progress)
        self.update_progress_label()

    def media_sys_duration_changed(self, duration: int):
        self.slider_progress.setMaximum(duration)
        self.update_progress_label()

    def media_sys_metadata_changed(self):
        self.selected_file_metadata = self.media_player_system.metaData()
        self.load_audio_metadata()
        
    def load_audio_metadata(self):
        if self.selected_file_metadata and self.selected_file_type != Media_File_Types.AUDIO:
            return
        music_image = self.selected_file_metadata.value(QMediaMetaData.Key.CoverArtImage)
        if not music_image:
            music_image = self.selected_file_metadata.value(QMediaMetaData.Key.ThumbnailImage)
        if music_image:
            pixmap = QPixmap.fromImage(music_image)
            self.load_image_to_display(pixmap)

    def load_image_to_display(self, pixmap: QPixmap, zoom: float = 1):
        pixmap_size = pixmap.size()
        media_scroller_size: QSize = self.media_scroller.size()
        #zoom = self.slider_setting.value()/100
        # TODO (?): fix math for this especially when full screening
        width = min(pixmap_size.width(), media_scroller_size.width()) * zoom
        height = min(pixmap_size.height(), media_scroller_size.height()) * zoom
        actual_size = QSize(int(width)-3, int(height)-4)
        self.media_image_display.setPixmap(pixmap.scaled(actual_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def progress_slider_pressed(self):
        self.media_player_system.pause()
        self.button_playstate.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("play.png")))

    def progress_slider_moved(self, value: int):
        if self.slider_progress.isSliderDown() and self.selected_file_name and self.is_selected_file_playable():
            self.media_player_system.setPosition(value)
            self.update_progress_label()

    def progress_slider_released(self):
        if self._is_playing_media:
            self.media_player_system.play()
            self.button_playstate.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("pause.png")))
            self.media_finished_trigger_check()
            
    def setting_slider_moved(self, value: int):
        if self.selected_file_type == Media_File_Types.IMAGE:
            # snap to 100 b/c thats the magic value
            if value >= 90 and value <= 110 and value != 100:
                self.slider_setting.setValue(100)
            else:
                self.label_setting.setText(f"Zoom: {value:,}%")
            self.update_existing_img()
        else:
            self.label_setting.setText(f"Volume: {value}%")
            self.audio_output.setVolume(value/100)
            self.states.stored_volume = value

    def backwards_clicked(self):
        if self.is_selected_file_playable() and self.media_player_system.position() / self.media_player_system.duration() > configuration.Media_Config.min_vid_audio_percentage_progressed_for_backwards/100:
            self.media_player_system.setPosition(0)
            return
        row: QModelIndex = self.media_entry_list.currentRow()
        if row <= -1:
            return
        elif row-1 <= -1:
            row = self.media_entry_list.count()-1
        else:
            row -= 1
        self.media_entry_list.setCurrentRow(row)
        self.media_list_item_clicked(self.media_entry_list.item(row))
        self.play_song()

    def forwards_clicked(self):
        row: QModelIndex = self.media_entry_list.currentRow()
        if row <= -1:
            return
        elif row+1 >= self.media_entry_list.count():
            row = 0
        else:
            row += 1
        self.media_entry_list.setCurrentRow(row)
        self.media_list_item_clicked(self.media_entry_list.item(row))
        self.play_song()

    def loop_clicked(self):
        loop_state = self.states.loop_state.value + 1
                
        if loop_state > 3:
            loop_state = 1
        
        match loop_state:
            case 1:
                self.states.loop_state = Loop_States.NOT_LOOPING

                self.button_loop.setChecked(False)
                self.button_loop.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("refresh.png")))
            case 2:
                self.states.loop_state = Loop_States.LOOPING_MEDIA_LIST

                self.button_loop.setChecked(True)
            case 3:
                self.states.loop_state = Loop_States.LOOPING_SINGLE_ENTRY

                self.button_loop.setChecked(True)
                self.button_loop.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("loop_one_item.png")))
            case _:
                raise ValueError("TOO HIGH VALUE FROM media_loop_clicked.")

    def shuffle_clicked(self):
        self.states.media_shuffle_enabled = self.button_shuffle.isChecked()
        if self.states.media_shuffle_enabled:
            media_entry_count = self.media_entry_list.count()
            numbers = random.sample(range(media_entry_count), media_entry_count)
            for index in range(media_entry_count):
                item: Media_List_Item = self.media_entry_list.item(index)
                item.assigned_id = numbers[index]
        self.media_entry_list.sortItems(Qt.SortOrder.AscendingOrder)

    @pyqtSlot(file_explorer_manager.Entry)
    def add_to_media_list(self, entry: file_explorer_manager.Entry):
        new_icon = QIcon(QPixmap(self._cached_icons[entry.media_file_type]))
        new_item = Media_List_Item(new_icon, entry.file_name)
        self.media_entry_list.addItem(new_item)

def convert_num_to_time(value: int) -> tuple:
    time_data = NamedTuple("time_data", [("hours", int), ("minutes", int), ("seconds", int)])
    hours = value // 3600
    minutes = (value-(hours*3600))//60
    seconds = value-(minutes*60)
    return time_data(hours=hours, minutes=minutes, seconds=seconds)
