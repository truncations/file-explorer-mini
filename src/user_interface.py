"""
Handles the user interface through QT in Python.
The user interface is already created with a .ui file and is initialized in QT. 
If there are any new UI elements that need to be added, it will be done in this script.

This script also manages the user expereince.

BRANCH-- TODO:
- custom sorting by clicking header column
- plan settings and start
REMINDER TO PUT THE OLD TODO BACK WHEN DONE
"""

from PyQt6 import uic # allows to load ui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QLabel,
    QWidget, 
    QSizePolicy,
    QLineEdit,
    QVBoxLayout,
    QStackedLayout,
    QPushButton,
    QProgressBar,
    QFileIconProvider,
    QListWidget,
    QListWidgetItem,
    QSlider
)
from PyQt6.QtCore import (
    Qt,
    QPoint,
    QFileInfo,
    QSortFilterProxyModel,
    QAbstractTableModel,
    QModelIndex,
    QEvent, 
    pyqtSignal, 
    pyqtSlot, 
    QRunnable,
    QThreadPool,
    QSize,
    QFileSystemWatcher,
    QUrl,
    QItemSelection
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QIcon, QPixmap
from typing import NamedTuple, Callable, Any
import sys
import src.configuration as configuration
import src.file_explorer_manager as file_explorer_manager
import src.media_controller as media_manager
from subprocess import run as subprocess_run
from win32api import GetMonitorInfo, MonitorFromPoint

app = QApplication([])

class File_Navigation_Commands:
    FORWARD = file_explorer_manager.Path_Manager.navigate_forwards
    BACKWARD = file_explorer_manager.Path_Manager.navigate_backwards
    UP = file_explorer_manager.Path_Manager.navigate_upwards

class Special_Bounds_Keys:
    TOP_OF_SCREEN = 1
    BOTTOM_OF_SCREEN = -1
    NO_SPECIALS = 0

class File_Explorer_Keys:
    NAME = 0
    DATE_MODIFIED = 1
    TYPE = 2
    SIZE = 3

    DATA_ICON = 0
    DATA_NAME = 1

class File_Explorer_Pages:
    EXPLORER = 0
    MEDIA = 1
    SETTINGS = 2

class File_Explorer_Table_Model(QAbstractTableModel):
    def __init__(self, data: list[list] | None = None, parent = None):
        super().__init__(parent)
        self._data = data if data else []
        self._headers = ["Name", "Date Modified", "Type", "Size"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._data) if self._data else 0
        else:
            return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        # is a constant that never changes
        if not parent.isValid():
            return 4
        else:
            return 0

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        if index.row() >= len(self._data) or index.row() < 0:
            return None
        if index.column() == File_Explorer_Keys.NAME:
            if role == Qt.ItemDataRole.DecorationRole:
                return self._data[index.row()][index.column()][File_Explorer_Keys.DATA_ICON] # ICON
            if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
                return self._data[index.row()][index.column()][File_Explorer_Keys.DATA_NAME] # NAME
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._data[index.row()][index.column()]
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> str:
        if (role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole) and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        
    """
    editable TableModel
    """
    def insertRows(self, position: int, amount: int = 1, index: QModelIndex = QModelIndex()):
        self.beginInsertRows(QModelIndex(), position, position + amount - 1)

        for row in range(0, amount):
            self._data.insert(position + row, [[0,1], "", "", ""])

        self.endInsertRows()

        return True
    
    def removeRows(self, position: int, amount: int = 1, index: QModelIndex = QModelIndex()):
        self.beginRemoveRows(QModelIndex(), position, position + amount - 1)

        del self._data[position:position + amount]

        self.endRemoveRows()

        return True
    
    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        row = index.row()
        if not (len(self._data) > row >= 0):
            return False
        
        data_row = self._data[row]
        if index.column() == File_Explorer_Keys.NAME:
            if role == Qt.ItemDataRole.EditRole:
                data_row[index.column()][File_Explorer_Keys.DATA_NAME] = value
            elif role == Qt.ItemDataRole.DecorationRole:
                data_row[index.column()][File_Explorer_Keys.DATA_ICON] = value
            else:
                return False
        else:
            data_row[index.column()] = value
            self.dataChanged.emit(index, index, [role])

        return True
    
    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag(QAbstractTableModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable)
    
    def add_multi_entries(self, rows: list[list]):
        if not rows:
            return
        start = len(self._data)
        end = start + len(rows) - 1
        self.beginInsertRows(QModelIndex(), start, end)
        self._data.extend(rows)
        self.endInsertRows()
    
    def edit_entry(self, row: int, col: int, value, role: int = Qt.ItemDataRole.EditRole):
        if not self._data: return
        index = self.index(row, col)
        self.setData(index, value, role)

    def remove_entry(self, row: int):
        if not self._data: return
        self.removeRows(row)

    def get_entry_data(self, row: int, col: int):
        if col == File_Explorer_Keys.NAME:
            return self._data[row][col][File_Explorer_Keys.DATA_NAME] 
        else:
            return self._data[row][col]

    def clear_all_entries(self):
        if not self._data: return
        self.removeRows(0, len(self._data))

class File_Explorer_Proxy_Model(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()

    """OVERRIDE SORTING BEHAVIOR"""
    # TODO: figured out that there's a default column that the proxy model sorts by which in this case is NAME conveniently so
    # if you do test other header cells SORTING IS FUNCTIONAL but does not behave the way it should be expected, will need to consider that
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Currently assumes Folder sort then Name sort (we'll add more later)
        
        Returns a boolean:
            * True -> if left value should come before right value
            * False -> right value should come before left value"""
        model = self.sourceModel()
        left_index_ext = model.index(left.row(), File_Explorer_Keys.TYPE)
        right_index_ext = model.index(right.row(),  File_Explorer_Keys.TYPE)

        left_entry_name: str = model.data(left, Qt.ItemDataRole.EditRole)
        right_entry_name: str = model.data(right, Qt.ItemDataRole.EditRole)
        left_entry_ext: str = model.data(left_index_ext, Qt.ItemDataRole.DisplayRole)
        right_entry_ext: str = model.data(right_index_ext, Qt.ItemDataRole.DisplayRole)

        if left_entry_ext == right_entry_ext == file_explorer_manager._directory_extension:
            return left_entry_name.lower() > right_entry_name.lower()
        elif left_entry_ext == file_explorer_manager._directory_extension or right_entry_ext == file_explorer_manager._directory_extension:
            return not left_entry_ext == file_explorer_manager._directory_extension
        else:
            return left_entry_name.lower() > right_entry_name.lower()

class File_Exp_Worker(QRunnable):
    def __init__(self, main_app: QMainWindow):
        super().__init__()
        self.main_app: QMainWindow = main_app
        # might have to adapt this for even bigger numbers
        self.query_size = 50

    def _compile_file_to_data(self, file: file_explorer_manager.Entry) -> list:
        file_name, file_icon = self.main_app.get_name_and_icon_for_table(file)
        if file.is_media_file:
            self.main_app.media_controller._signal_add_to_media_list.emit(file)
        size = not file_explorer_manager.Path_Manager.entry_is_folder(file) and file_explorer_manager.UI_Display_Utility.get_size_str(file.size) or ""
        return [[file_icon, file_name], file.get_date_modified_str(), file.extension.strip('.'), size]

    @pyqtSlot()
    def run(self):
        buffer = []
        files = file_explorer_manager.Path_Manager.get_list_of_entries_in_cur_path()
        for file in files:
            buffer.append(self._compile_file_to_data(file))
            if len(buffer) >= self.query_size:
                self.main_app._signal_add_to_file_explorer.emit(buffer)
                buffer.clear()
        if buffer:
            self.main_app._signal_add_to_file_explorer.emit(buffer)
        self.main_app._signal_finished_adding_to_file_explorer.emit()

class Main_Application(QMainWindow):
    _signal_add_to_file_explorer: pyqtSignal = pyqtSignal(list)
    _signal_finished_adding_to_file_explorer: pyqtSignal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self._file_exp_table_model: File_Explorer_Table_Model | QAbstractTableModel = File_Explorer_Table_Model()
        self._file_exp_proxy_model: File_Explorer_Proxy_Model | QSortFilterProxyModel = File_Explorer_Proxy_Model()
        self._file_system_watcher: QFileSystemWatcher = QFileSystemWatcher()
        self._is_window_at_top: bool = False
        self._thread_pool: QThreadPool = QThreadPool()
        self._cached_icons_by_ext: dict[str, QIcon] = {}
        self._ctrl_pressed: bool = False

        self.load_ui()
        self.design_layouts()
        self.setup_main_window_functions()
        self.setup_file_explorer_table()
        self.setup_video_widget_for_media()
        self.connect_signals_and_slots()
        self.show_page(File_Explorer_Pages.EXPLORER) # show explorer page for default
        self.update_file_explorer()

    """
    Main Application setup functions (ran with __init__)
    """
    def load_ui(self) -> None:
        """
        Loads user interface file into QMainWindow.
        """
        uic.load_ui.loadUi(file_explorer_manager.Resource_File_Getter.get_dir_ui_file(), self)

    def design_layouts(self) -> None:
        """
        Layouts that need to be created/modified; set up for the application will be done here.
        """
        # Setup for storage display on status bar
        QStackedLayout_bar_storage = QStackedLayout()
        QStackedLayout_bar_storage.setStackingMode(QStackedLayout.StackingMode.StackAll)
        QStackedLayout_bar_storage.addWidget(self.display_storage)
        QStackedLayout_bar_storage.addWidget(self.progress_bar_storage)

        #self.display_storage.raise_()
        self.display_storage.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.bar_storage.setLayout(QStackedLayout_bar_storage)

    def setup_main_window_functions(self) -> None:
        """
        Disable some Windows default functionality. (Applied when running any application of any sort.)
        """
        # minimize, fullscreen, quit, move window.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setup_file_explorer_table(self) -> None:
        """
        Setup the file explorer table (for visuals) displayed in the explorer page of the application.
            * Establishes a M/V architecture with file_explorer as viewer (QTableView) and _file_exp_table_model as model.
        """
        self._file_exp_proxy_model.setSourceModel(self._file_exp_table_model)
        self.file_explorer.setModel(self._file_exp_proxy_model)
        self.file_explorer.setSortingEnabled(True)

        self.file_explorer.horizontalHeader().setFont(self.file_explorer.font())
        self.file_explorer.setColumnWidth(File_Explorer_Keys.NAME, configuration.File_Explorer_Table_Config.NAME_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.DATE_MODIFIED, configuration.File_Explorer_Table_Config.DATE_MODIFIED_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.TYPE, configuration.File_Explorer_Table_Config.TYPE_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.SIZE, configuration.File_Explorer_Table_Config.SIZE_COL_WIDTH)

    def setup_video_widget_for_media(self) -> None:
        self.media_controller = media_manager.Media_Controller(self)
        media_video_widget = self.media_controller.video_widget

        media_vid_widget_holder = QWidget()
        media_vid_holder_layout = QHBoxLayout()
        media_vid_widget_holder.setLayout(media_vid_holder_layout)
        media_vid_holder_layout.addWidget(media_video_widget)
        media_vid_holder_layout.setContentsMargins(2,0,0,2)

        self.media_player.layout().addWidget(media_vid_widget_holder)

    def connect_signals_and_slots(self) -> None:
        """
        Connects all QT Signals and Slots;
            * Provided that they are events that are NOT derived from QMainWindow.
        """
        self.button_close_window.clicked.connect(self.close_window)
        self.button_minimize_window.clicked.connect(self.minimize_window)
        self.button_fullscreen_window.clicked.connect(self.fullscreen_button_clicked)

        self.button_forwards.clicked.connect(lambda: self.file_navigation_buttons_clicked(File_Navigation_Commands.FORWARD))
        self.button_backwards.clicked.connect(lambda: self.file_navigation_buttons_clicked(File_Navigation_Commands.BACKWARD))
        self.button_parent_directory.clicked.connect(lambda: self.file_navigation_buttons_clicked(File_Navigation_Commands.UP))
        self.button_refresh.clicked.connect(self.update_file_explorer)

        self.button_tab_backwards_compatibility.clicked.connect(self.open_actual_file_explorer)
        self.button_tab_explorer.clicked.connect(lambda: self.navigation_tabs_clicked("explorer"))
        self.button_tab_media.clicked.connect(lambda: self.navigation_tabs_clicked("media"))
        self.button_tab_settings.clicked.connect(lambda: self.navigation_tabs_clicked("settings"))

        self.title_row.mouseMoveEvent = self.move_window_event
        self.input_status_bar.returnPressed.connect(self.status_bar_enter_pressed)
        self.input_search_bar.returnPressed.connect(self.search_signal_triggered)
        self.search_button.clicked.connect(self.search_signal_triggered)

        self._signal_add_to_file_explorer.connect(self._add_to_file_explorer, Qt.ConnectionType.QueuedConnection)
        self._signal_finished_adding_to_file_explorer.connect(self._finished_adding_to_file_explorer, Qt.ConnectionType.QueuedConnection)

        self._file_system_watcher.directoryChanged.connect(self.folder_change_event)
        self.file_explorer.selectionModel().selectionChanged.connect(self.file_exp_selection_changed)
        
        self.file_explorer.viewport().installEventFilter(self)

    """
    UI updating functions
        * Updates visual elements
    """
    def show_page(self, main_content_index: int):
        page_tuple_data = NamedTuple("page_tuple_data", [("status_bar_read_only", bool),("activate_function", Callable),("function_parameter", Any)])
        
        pages = [
            # INDEX 0: Explorer
            page_tuple_data(status_bar_read_only=False, activate_function=self.input_status_bar.setText, function_parameter=file_explorer_manager.Path_Manager.current_path),
            # INDEX 1: Media
            page_tuple_data(status_bar_read_only=True, activate_function=self.input_status_bar.setText, function_parameter=(self.media_controller.selected_file_name if self.media_controller.selected_file_name else file_explorer_manager.Path_Manager.current_path)),
            # INDEX 2: Settings
            page_tuple_data(status_bar_read_only=True, activate_function=self.input_status_bar.setText, function_parameter="Settings"),
        ]
        page_data = pages[main_content_index]

        self.main_content.setCurrentIndex(main_content_index)
        self.navigation_section.setCurrentIndex(main_content_index)
        
        self.input_status_bar.setReadOnly(page_data.status_bar_read_only)
        if page_data.activate_function is None:
            return
        if page_data.function_parameter is None:
            page_data.activate_function()
        else:
            page_data.activate_function(page_data.function_parameter)

    def update_file_explorer(self) -> None:
        del_objs = self._file_system_watcher.directories()
        if del_objs:
            self._file_system_watcher.removePaths(del_objs)
        self.media_entry_list.clear()
        self._file_exp_table_model.clear_all_entries()

        file_explorer_worker = File_Exp_Worker(self)
        self._thread_pool.start(file_explorer_worker)

        self.input_status_bar.setText(file_explorer_manager.Path_Manager.current_path)
        self.input_search_bar.setText("")
        self.documentation.setText("Click on a file to see potential documentation about file for clarification.")

        self.button_backwards.setEnabled(file_explorer_manager.Path_Manager.can_navigate_backwards())
        self.button_forwards.setEnabled(file_explorer_manager.Path_Manager.can_navigate_forwards())
        self.button_parent_directory.setEnabled(not file_explorer_manager.Path_Manager.is_current_path_drives())

        storage_data = file_explorer_manager.UI_Display_Utility.get_storage_display_data(file_explorer_manager.Path_Manager.current_path_compiled[0])
        self._file_system_watcher.addPath(file_explorer_manager.Path_Manager.current_path)

        self.media_controller.stop_song()
        self.slider_progress.setValue(0)
        self.slider_setting.setValue(self.media_controller.states.stored_volume)
        self.slider_setting.setMaximum(100)

        self.media_controller.states.media_shuffle_enabled = False
        self.button_shuffle.setChecked(self.media_controller.states.media_shuffle_enabled)

        self.progress_bar_storage.setValue(storage_data[0])
        self.display_storage.setText(storage_data[1])
        self.media_controller.clear_display_media()
        #print(file_explorer_manager.Directory_Manager.navigated_paths, file_explorer_manager.Directory_Manager.navigated_paths_index)

    def get_name_and_icon_for_table(self, file: file_explorer_manager.Entry):
        if not file_explorer_manager.Path_Manager.entry_is_drive(file) and self._cached_icons_by_ext.get(file.extension, None) is not None:
            return (file.file_name, QIcon(self._cached_icons_by_ext[file.extension]))
        else:
            icon_provider = QFileIconProvider()
            pixmap_data = icon_provider.icon(QFileInfo(file_explorer_manager.Path_Manager.get_abs_path(file.file_name))).pixmap(32,32)
            pixmap_data = pixmap_data if pixmap_data is not None else QPixmap(file_explorer_manager.Resource_File_Getter.get_path_to_img("default_no_file_icon.png"))
            icon = QIcon(pixmap_data)

            self._cached_icons_by_ext.update({file.extension: icon})
            return (file.file_name, icon)
        
    def set_visible_nav_buttons(self, wish_visible: bool):
        self.button_backwards.setVisible(wish_visible)
        self.button_forwards.setVisible(wish_visible)
        self.button_parent_directory.setVisible(wish_visible)
        self.button_refresh.setVisible(wish_visible)
        self.input_search_bar.setVisible(wish_visible)
        self.search_button.setVisible(wish_visible)

    def display_fullscreen_enabled(self):
        # helper methods for fullscreening
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.button_fullscreen_window.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("fullscreen_2.png")))

    def display_fullscreen_unenabled(self):
        # helper methods for fullscreening
        self.setWindowState(Qt.WindowState.WindowActive)
        self.button_fullscreen_window.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("fullscreen.png")))

    def check_for_window_pos_bounds(self, pos : QPoint):
        screen_area_geometry = QApplication.primaryScreen().geometry()
        screen_area_geometry = (screen_area_geometry.width(), screen_area_geometry.height())

        taskbar_height = get_monitor_taskbar_height()
        # is window at top of screen?
        if pos.y() <= 0:
            return Special_Bounds_Keys.TOP_OF_SCREEN
        # else is window near the taskbar?
        elif pos.y() > screen_area_geometry[1] - taskbar_height - 5:
            return Special_Bounds_Keys.BOTTOM_OF_SCREEN
        # otherwise we're fine..
        else:
            return Special_Bounds_Keys.NO_SPECIALS

    """
    Slots for signals provided by QWidget() objects
    """
    def close_window(self):
        app.exit()

    def minimize_window(self):
        self.setWindowState(Qt.WindowState.WindowMinimized)

    def fullscreen_button_clicked(self):
        if self.isMaximized():
            self.display_fullscreen_unenabled()
        else:
            self.display_fullscreen_enabled()

    def status_bar_enter_pressed(self):
        if not self.input_status_bar.isEnabled():
            return
        input_text = self.input_status_bar.text()
        if input_text == "":
            input_text=file_explorer_manager._default_path
        if input_text == "Drives":
            file_explorer_manager.Path_Manager.update_to_new_path(file_explorer_manager.drives_path_name)
            self.update_file_explorer()
        else:
            input_text = file_explorer_manager.Path_Manager.convert_str_to_path(input_text)
            self.open_entry(input_text)

    def navigation_tabs_clicked(self, tab_button_pressed_name: str):
        tab_buttons = {
            "explorer": {"button": self.button_tab_explorer, "main_content_index": File_Explorer_Pages.EXPLORER, "set_visible_nav_buttons": True},
            "media": {"button": self.button_tab_media, "main_content_index": File_Explorer_Pages.MEDIA, "set_visible_nav_buttons": False},
            "settings": {"button": self.button_tab_settings, "main_content_index": File_Explorer_Pages.SETTINGS, "set_visible_nav_buttons": False},
        }
        tab_button_pressed_data = tab_buttons[tab_button_pressed_name]
        tab_button_pressed: QPushButton = tab_button_pressed_data["button"]

        self.button_tab_explorer.setChecked(False)
        self.button_tab_media.setChecked(False)
        self.button_tab_settings.setChecked(False)
        tab_button_pressed.setChecked(True)

        self.show_page(tab_button_pressed_data["main_content_index"])
        self.set_visible_nav_buttons(tab_button_pressed_data["set_visible_nav_buttons"])

        # just in case for faster trashing
        tab_buttons.clear()
    
    def file_navigation_buttons_clicked(self, navigation_command):
        navigation_command()
        self.update_file_explorer()

    def open_actual_file_explorer(self):
        subprocess_run(file_explorer_manager.Utility.get_open_file_explorer_command())

    def open_entry(self, file_name_inputted: str):
        # note: all drives like C:\, A:\ are folders technically
        full_path = file_explorer_manager.Path_Manager.get_abs_path(file_name_inputted)
        if file_explorer_manager.Path_Manager.path_is_folder(full_path):
            file_explorer_manager.Path_Manager.update_to_new_path(full_path)
            self.update_file_explorer()
        elif file_explorer_manager.Path_Manager.path_is_media(full_path):
            self.navigation_tabs_clicked("media")
            self.media_controller.update_display(full_path, file_name_inputted)
        else:
            file_explorer_manager.Utility.open_file(full_path)

    def file_exp_cell_double_clicked(self, index: QModelIndex):
        entry_name = self._file_exp_proxy_model.data(self._file_exp_proxy_model.index(index.row(), File_Explorer_Keys.NAME))
        self.open_entry(entry_name)

    def file_exp_cell_clicked(self, index: QModelIndex):
        entry_name = self._file_exp_proxy_model.data(self._file_exp_proxy_model.index(index.row(), File_Explorer_Keys.NAME))
        if entry_name:
            path_of_entry = file_explorer_manager.Path_Manager.get_abs_path(entry_name)
            entry_extension = self._file_exp_proxy_model.data(self._file_exp_proxy_model.index(index.row(), File_Explorer_Keys.TYPE))
            description = file_explorer_manager.UI_Display_Utility.get_file_description(path_of_entry, entry_extension)
            self.documentation.setText(description)

    def file_exp_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        selected_rows = self.file_explorer.selectionModel().selectedRows()
        if len(selected_rows) > 1:
            self.documentation.setText(f"{len(selected_rows)} selected entries.")
        elif selected_rows:
            self.file_exp_cell_clicked(selected_rows[0])

    def search_in_directory(self):
        """
        Uses a filtering basic substring algorithm to determine what should be searched in given path.
        """
        search_query = self.input_search_bar.text().lower()

        for row in range(self._file_exp_proxy_model.rowCount()):
            cur_file_name = self._file_exp_proxy_model.data(self._file_exp_proxy_model.index(row, File_Explorer_Keys.NAME)).lower()
            if search_query not in cur_file_name:
                self.file_explorer.hideRow(row)
            else:
                self.file_explorer.showRow(row)
    
    def search_signal_triggered(self):
        self.search_in_directory()

    def folder_change_event(self, dir_where_changed: str):
        """triggers when something inside the folder (we're looking at) changes, even if from windows OS file explorer."""
        if dir_where_changed == file_explorer_manager.Path_Manager.current_path:
            self.update_file_explorer()

    @pyqtSlot(list)
    def _add_to_file_explorer(self, buffered_entries: list[list]):
        if len(buffered_entries) > 0:
            self._file_exp_table_model.add_multi_entries(buffered_entries)
    
    @pyqtSlot()
    def _finished_adding_to_file_explorer(self):
        self.label_extra_information.setText(f"{len(file_explorer_manager.Path_Manager.entry_list_of_path)} items in directory")

    """
    Subclassed Events
        * Events/functions provided by QMainApplication that have been overridden.
        * Or events with event filters.
    """
    def move_window_event(self, event: QEvent):
        # TODO: fix bad positioning at the top.
        if self.isMaximized():
            self.display_fullscreen_unenabled()
            #pos_sum: QPoint = self.pos() + event.globalPosition().toPoint() - self.click_position
            #self.move(QPoint(pos_sum.x(), -7))

        if event.buttons() == Qt.MouseButton.LeftButton:
            new_position : QPoint = self.pos() + event.globalPosition().toPoint() - self.click_position
            # ensure that the window is always apparent, even when near the taskbar, as well as if the window hits the top, it will auto fullscreen.
            special_bounds_key = self.check_for_window_pos_bounds(new_position)
            self._is_window_at_top = False

            if special_bounds_key == Special_Bounds_Keys.TOP_OF_SCREEN:
                self._is_window_at_top = True
                self.move(new_position)
            elif special_bounds_key == Special_Bounds_Keys.NO_SPECIALS:
                self.move(new_position)
            
            self.click_position = event.globalPosition().toPoint()
            event.accept()

    def mousePressEvent(self, event: QEvent):
        self.click_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QEvent):
        if self._is_window_at_top:
            self.display_fullscreen_enabled()

    def resizeEvent(self, event: QEvent):
        # resize the pixmap in media if needed
        if media_manager.Media_Controller.selected_file_name:
            media_type_of_file = self.media_controller.selected_file_type 
            if media_type_of_file == media_manager.Media_File_Types.IMAGE:
                self.media_controller.update_existing_img()
            elif media_type_of_file == media_manager.Media_File_Types.AUDIO:
                self.media_controller.media_sys_metadata_changed()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Control:
            self._ctrl_pressed = True
    
    def keyReleaseEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Control:
            self._ctrl_pressed = False

    def wheelEvent(self, event):
        if not self._ctrl_pressed or not self.media_scroller.underMouse() or self.main_content.currentIndex() != File_Explorer_Pages.MEDIA or not self.media_controller.selected_file_name:
            return
        if self.media_controller.is_selected_file_playable():
            return
        change: int = event.angleDelta().y()//abs(event.angleDelta().y())

        self.slider_setting.setValue(self.slider_setting.value() + change*configuration.Image_Config.change_zoom_by_wheel_amt)
        self.label_setting.setText(f"Zoom: {self.slider_setting.value():,}%")

        self.media_controller.update_existing_img()

    def eventFilter(self, source, event: QEvent):
        if source is not self.file_explorer.viewport():
            return
        if event.type() == QEvent.Type.MouseButtonDblClick and event.buttons() == Qt.MouseButton.LeftButton:
            item_clicked_index = self.file_explorer.indexAt(event.pos())
            if item_clicked_index is not None:
                self.file_exp_cell_double_clicked(item_clicked_index)
        return super().eventFilter(source, event)

def get_monitor_taskbar_height() -> int:
    _height_screen_key = 3

    primary_monitor = MonitorFromPoint((0,0))
    monitor_info = GetMonitorInfo(primary_monitor)
    actual_screen_area = monitor_info.get("Monitor")
    available_screen_area = monitor_info.get("Work")
    return actual_screen_area[_height_screen_key]-available_screen_area[_height_screen_key]
    
def start_application():
    # define all QT variables here

    window = Main_Application()
    window.show()

    sys.exit(app.exec())
