"""
Handles the user interface through QT in Python.
The user interface is already created with a .ui file and is initialized in QT. 
If there are any new UI elements that need to be added, it will be done in this script.

This script also manages the user expereince.

Todo:
    * sorting based on type FIRST then name (only if folder)
        + may implement multi sorting if "you wanted to"
    * right click implementation on files
    * refactor this too it sucks
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
    QProgressBar,
    QFileIconProvider,
)
from PyQt6.QtCore import Qt, QPoint, QFileInfo, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QIcon, QPixmap
import sys
import src.configuration as configuration
import src.file_explorer_manager as file_explorer_manager
import src.backend as backend
from subprocess import run as subprocess_run
from win32api import GetMonitorInfo, MonitorFromPoint

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
    
    # remove the default parameter it doesnt work this method gets initialized before QApp does, it just does.
    def add_entry(self, new_entry_data: list = []):
        if not self._data: return
        row = self.rowCount()
        self.insertRows(row)
        self._data.append(new_entry_data)
        self.layoutChanged.emit()
    
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

class Main_Application(QMainWindow):
    app_ref = None
    window_at_top = False

    def __init__(self, app_reference):
        super().__init__()

        self._file_exp_table_model = File_Explorer_Table_Model()

        Main_Application.app_ref = app_reference
        self.load_ui()
        self.design_layouts()

        self.setup_main_window_functions()
        self.setup_file_explorer_table()

        self.show_explorer_page()

        self.connect_events()

    def design_layouts(self):
        # setup for storage display on status bar
        QStackedLayout_bar_storage = QStackedLayout()
        QStackedLayout_bar_storage.setStackingMode(QStackedLayout.StackingMode.StackAll)
        QStackedLayout_bar_storage.addWidget(self.display_storage)
        QStackedLayout_bar_storage.addWidget(self.progress_bar_storage)
        self.display_storage.raise_()
        self.display_storage.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.bar_storage.setLayout(QStackedLayout_bar_storage)

    #
    # ui setup functions to ensure application runs as expected
    #
    def setup_main_window_functions(self):
        # minimize, fullscreen, quit, move window.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setup_file_explorer_table(self):
        # proper setup here
        self.file_explorer.setModel(self._file_exp_table_model)

        self.file_explorer.horizontalHeader().setFont(self.file_explorer.font())
        self.file_explorer.setColumnWidth(File_Explorer_Keys.NAME, configuration.File_Explorer_Table_Config.NAME_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.DATE_MODIFIED, configuration.File_Explorer_Table_Config.DATE_MODIFIED_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.TYPE, configuration.File_Explorer_Table_Config.TYPE_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.SIZE, configuration.File_Explorer_Table_Config.SIZE_COL_WIDTH)

    def load_ui(self):
        uic.load_ui.loadUi(file_explorer_manager.Resource_File_Getter.get_dir_ui_file(), self)

    def connect_events(self):
        self.button_close_window.clicked.connect(self.close_window)
        self.button_minimize_window.clicked.connect(self.minimize_window)
        self.button_fullscreen_window.clicked.connect(self.fullscreen_button_clicked)

        self.button_backwards.clicked.connect(self.backwards_button_clicked)
        self.button_forwards.clicked.connect(self.forwards_button_clicked)

        self.button_tab_backwards_compatibility.clicked.connect(self.open_file_explorer)
        self.button_tab_explorer.clicked.connect(self.explorer_tab_button_clicked)
        self.button_tab_media.clicked.connect(self.media_tab_button_clicked)
        self.button_tab_settings.clicked.connect(self.settings_tab_button_clicked)

        self.title_row.mouseMoveEvent = self.move_window_event
        self.input_status_bar.returnPressed.connect(self.status_bar_enter_pressed)
        self.input_search_bar.returnPressed.connect(self.search_bar_enter_pressed)
        self.search_button.clicked.connect(self.search_button_clicked)

        self.button_refresh.clicked.connect(self.refresh_button_pressed)
        self.button_parent_directory.clicked.connect(self.up_parent_pressed)

        self.file_explorer.clicked.connect(self.table_cell_clicked)
        self.file_explorer.doubleClicked.connect(self.table_cell_double_clicked)

    #
    # ui functions
    #
    def show_explorer_page(self):
        self.main_content.setCurrentIndex(0)
        self.input_status_bar.setReadOnly(False)
        self.update_file_explorer()

    def show_media_page(self):
        self.main_content.setCurrentIndex(1)
        self.input_status_bar.setReadOnly(True)
        self.input_status_bar.setText(file_explorer_manager.Path_Manager.current_path)

    def show_settings_page(self):
        self.main_content.setCurrentIndex(2)
        self.input_status_bar.setReadOnly(True)
        self.input_status_bar.setText("SETTINGS")

    def update_file_explorer(self):
        self._file_exp_table_model.clear_all_entries()

        files = file_explorer_manager.Path_Manager.get_list_of_entries_in_cur_path()
        row_count = 0
        # TODO: add a multithreader so the files will load one at a time to prevent QT from freezing using Queued Connections.
        for file in files:
            file_name, file_icon = self.get_name_and_icon_for_table(file)
            index = self._file_exp_table_model.index(row_count, File_Explorer_Keys.NAME)

            self._file_exp_table_model.insertRows(row_count)
            self._file_exp_table_model.edit_entry(row_count, File_Explorer_Keys.NAME, file_name)
            self._file_exp_table_model.edit_entry(row_count, File_Explorer_Keys.NAME, QIcon(file_icon), Qt.ItemDataRole.DecorationRole)
            self._file_exp_table_model.edit_entry(row_count, File_Explorer_Keys.DATE_MODIFIED, file.get_date_modified_str())
            self._file_exp_table_model.edit_entry(row_count, File_Explorer_Keys.TYPE, file.extension.strip('.'))
            if not file_explorer_manager.Path_Manager.entry_is_folder(file):
                self._file_exp_table_model.edit_entry(row_count, File_Explorer_Keys.SIZE, file_explorer_manager.UI_Display_Utility.get_size_str(file.size))
            """
            self.file_explorer.insertRow(row_count)

            self.file_explorer.setCellWidget(row_count, File_Explorer_Keys.NAME, self.get_name_and_icon_for_table(file))
            self.file_explorer.setItem(row_count, File_Explorer_Keys.DATE_MODIFIED, QTableWidgetItem(file.get_date_modified_str()))
            self.file_explorer.setItem(row_count, File_Explorer_Keys.TYPE, QTableWidgetItem(file.extension.strip('.')))
            if not file_explorer_manager.Path_Manager.entry_is_folder(file):
                self.file_explorer.setItem(row_count, File_Explorer_Keys.SIZE, QTableWidgetItem(file_explorer_manager.UI_Display_Utility.get_size_str(file.size)))
            """

            
            row_count += 1

        self.input_status_bar.setText(file_explorer_manager.Path_Manager.current_path)
        self.input_search_bar.setText("")
        self.label_extra_information.setText(f"{row_count} items in directory")
        self.documentation.setText("Click on a file to see potential documentation about file for clarification.")

        self.button_backwards.setEnabled(file_explorer_manager.Path_Manager.can_navigate_backwards())
        self.button_forwards.setEnabled(file_explorer_manager.Path_Manager.can_navigate_forwards())
        self.button_parent_directory.setEnabled(not file_explorer_manager.Path_Manager.is_current_path_drives())

        storage_data = file_explorer_manager.UI_Display_Utility.get_storage_display_data(file_explorer_manager.Path_Manager.current_path_compiled[0])
        self.progress_bar_storage.setValue(storage_data[0])
        self.display_storage.setText(storage_data[1])
        #print(file_explorer_manager.Directory_Manager.navigated_paths, file_explorer_manager.Directory_Manager.navigated_paths_index)

    def get_name_and_icon_for_table(self, file: file_explorer_manager.Entry):
        icon_provider = QFileIconProvider()
        pixmap_data = icon_provider.icon(QFileInfo(file_explorer_manager.Path_Manager.get_abs_path(file.file_name))).pixmap(32,32)
        pixmap_data = pixmap_data if pixmap_data is not None else QPixmap(file_explorer_manager.Resource_File_Getter.get_path_to_img("default_no_file_icon.png"))

        return (file.file_name, pixmap_data)
    
    # helpers for fullscreening
    def display_fullscreen_enabled(self):
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.button_fullscreen_window.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("fullscreen_2.png")))

    def display_fullscreen_unenabled(self):
        self.setWindowState(Qt.WindowState.WindowActive)
        self.button_fullscreen_window.setIcon(QIcon(file_explorer_manager.Resource_File_Getter.get_path_to_img("fullscreen.png")))

    # MUST TAKE IN QPOINT
    def check_for_special_bounds(self, pos : QPoint):
        screen_area_geometry = QApplication.primaryScreen().geometry()
        screen_area_geometry = (screen_area_geometry.width(), screen_area_geometry.height())

        taskbar_height = get_taskbar_height()
        # is window at top of screen?
        if pos.y() <= 0:
            return Special_Bounds_Keys.TOP_OF_SCREEN
        # else is window near the taskbar?
        elif pos.y() > screen_area_geometry[1] - taskbar_height - 5:
            return Special_Bounds_Keys.BOTTOM_OF_SCREEN
        # otherwise we're fine..
        else:
            return Special_Bounds_Keys.NO_SPECIALS

    #
    # events
    #
    def close_window(self):
        Main_Application.app_ref.exit()

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
        input_text = file_explorer_manager.Path_Manager.convert_str_to_path(input_text)
        # handle doing
        self.try_open_given_directory(input_text)

    # todo
    def refresh_button_pressed(self):
        self.update_file_explorer()

    def up_parent_pressed(self):
        file_explorer_manager.Path_Manager.navigate_upwards()
        self.update_file_explorer()

    def explorer_tab_button_clicked(self):
        if not self.button_tab_explorer.isChecked():
            self.button_tab_explorer.setChecked(True)
        else:
            self.show_explorer_page()
            self.button_tab_media.setChecked(False)
            self.button_tab_settings.setChecked(False)

            self.button_backwards.setVisible(True)
            self.button_forwards.setVisible(True)
            self.button_parent_directory.setVisible(True)
            self.button_refresh.setVisible(True)
            self.input_search_bar.setVisible(True)
            self.search_button.setVisible(True)

    def media_tab_button_clicked(self):
        if not self.button_tab_media.isChecked():
            self.button_tab_media.setChecked(True)
        else:
            self.show_media_page()
            self.button_tab_explorer.setChecked(False)
            self.button_tab_settings.setChecked(False)

            self.button_backwards.setVisible(False)
            self.button_forwards.setVisible(False)
            self.button_parent_directory.setVisible(False)
            self.button_refresh.setVisible(False)
            self.input_search_bar.setVisible(False)
            self.search_button.setVisible(False)

    def settings_tab_button_clicked(self):
        if not self.button_tab_settings.isChecked():
            self.button_tab_settings.setChecked(True)
        else:
            self.show_settings_page()
            self.button_tab_media.setChecked(False)
            self.button_tab_explorer.setChecked(False)

            self.button_backwards.setVisible(False)
            self.button_forwards.setVisible(False)
            self.button_parent_directory.setVisible(False)
            self.button_refresh.setVisible(False)
            self.input_search_bar.setVisible(False)
            self.search_button.setVisible(False)
    
    def backwards_button_clicked(self):
        if file_explorer_manager.Path_Manager.can_navigate_backwards():
            file_explorer_manager.Path_Manager.navigate_backwards()
            self.update_file_explorer()

    def forwards_button_clicked(self):
        if file_explorer_manager.Path_Manager.can_navigate_forwards():
            file_explorer_manager.Path_Manager.navigate_forwards()
            self.update_file_explorer()

    def move_window_event(self, event):
        if self.isMaximized():
            self.display_fullscreen_unenabled()

        if event.buttons() == Qt.MouseButton.LeftButton:
            new_position : QPoint = self.pos() + event.globalPosition().toPoint() - self.click_position
            # ensure that the window is always apparent, even when near the taskbar, as well as if the window hits the top, it will auto fullscreen.
            special_bounds_key = self.check_for_special_bounds(new_position)
            Main_Application.window_at_top = False

            if special_bounds_key == Special_Bounds_Keys.TOP_OF_SCREEN:
                Main_Application.window_at_top = True
                self.move(new_position)
            elif special_bounds_key == Special_Bounds_Keys.NO_SPECIALS:
                self.move(new_position)
            
            self.click_position = event.globalPosition().toPoint()
            event.accept()

    def open_file_explorer(self):
        subprocess_run(file_explorer_manager.Utility.get_open_file_explorer_command())

    def search_in_directory(self):
        search_query = self.input_search_bar.text().lower()

        for index in range(self.file_explorer.rowCount()):
            if search_query not in self.file_explorer.cellWidget(index, File_Explorer_Keys.NAME).layout().itemAt(1).widget().text().lower():
                self.file_explorer.hideRow(index)
            else:
                self.file_explorer.showRow(index)
    
    def table_cell_double_clicked(self, index: QModelIndex):
        path_of_item = file_explorer_manager.Path_Manager.get_abs_path(self._file_exp_table_model.get_entry_data(index.row(), File_Explorer_Keys.NAME))
        self.try_open_given_directory(path_of_item)

    def table_cell_clicked(self, index: QModelIndex):
        path_of_item = file_explorer_manager.Path_Manager.get_abs_path(self._file_exp_table_model.get_entry_data(index.row(), File_Explorer_Keys.NAME))
        extension_of_item = self._file_exp_table_model.get_entry_data(index.row(), File_Explorer_Keys.TYPE)
        description = file_explorer_manager.UI_Display_Utility.get_file_description(path_of_item, extension_of_item)
        self.documentation.setText(description)

    def try_open_given_directory(self, directory):
        if file_explorer_manager.Path_Manager.path_is_folder(directory):
            file_explorer_manager.Path_Manager.update_to_new_path(directory)
            self.update_file_explorer()
        else:
            file_explorer_manager.Utility.open_file(directory)

    def search_bar_enter_pressed(self):
        self.search_in_directory()
    
    def search_button_clicked(self):
        self.search_in_directory()

    def mousePressEvent(self, event):
        self.click_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if Main_Application.window_at_top:
            self.display_fullscreen_enabled()

def get_taskbar_height():
    _height_screen_key = 3

    primary_monitor = MonitorFromPoint((0,0))
    monitor_info = GetMonitorInfo(primary_monitor)
    actual_screen_area = monitor_info.get("Monitor")
    available_screen_area = monitor_info.get("Work")
    return actual_screen_area[_height_screen_key]-available_screen_area[_height_screen_key]

def start_application():
    app = QApplication([])

    # define all QT variables here

    window = Main_Application(app)
    window.show()

    sys.exit(app.exec())
