from PyQt6 import uic # allows to load ui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidgetItem,
    QHBoxLayout,
    QLabel,
    QWidget, 
    QSizePolicy,
    QLineEdit,
    QVBoxLayout
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon, QPixmap
import sys
import src.vars_util as vars_util
import src.backend as backend
from subprocess import run as subprocess_run

class Special_Bounds_Keys:
    TOP_OF_SCREEN = 1
    BOTTOM_OF_SCREEN = -1
    NO_SPECIALS = 0

class File_Explorer_Keys:
    NAME = 0
    DATE_MODIFIED = 1
    TYPE = 2
    SIZE = 3

class Main_Application(QMainWindow):
    app_ref = None
    window_at_top = False

    def __init__(self, app_reference):
        super().__init__()

        Main_Application.app_ref = app_reference
        self.load_ui()
        
        self.setup_main_window_functions()
        self.setup_file_explorer_table()

        self.show_explorer_page()

        self.connect_events()

    #
    # ui setup functions to ensure application runs as expected
    #
    def setup_main_window_functions(self):
        # minimize, fullscreen, quit, move window.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setup_file_explorer_table(self):
        # proper setup here
        self.file_explorer.horizontalHeader().setFont(self.file_explorer.font())

        self.file_explorer.setColumnWidth(File_Explorer_Keys.NAME, vars_util.File_Explorer_Config.NAME_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.DATE_MODIFIED, vars_util.File_Explorer_Config.DATE_MODIFIED_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.TYPE, vars_util.File_Explorer_Config.TYPE_COL_WIDTH)
        self.file_explorer.setColumnWidth(File_Explorer_Keys.SIZE, vars_util.File_Explorer_Config.SIZE_COL_WIDTH)

    def load_ui(self):
        uic.load_ui.loadUi(vars_util.Directory_Manager.get_dir_ui_file(vars_util.ui_src_file_name), self)

    def connect_events(self):
        self.button_close_window.clicked.connect(self.close_window)
        self.button_minimize_window.clicked.connect(self.minimize_window)
        self.button_fullscreen_window.clicked.connect(self.fullscreen_button_clicked)

        self.button_tab_backwards_compatibility.clicked.connect(self.open_file_explorer)
        self.button_tab_explorer.clicked.connect(self.explorer_tab_button_clicked)
        self.button_tab_media.clicked.connect(self.media_tab_button_clicked)
        self.button_tab_settings.clicked.connect(self.settings_tab_button_clicked)

        self.title_row.mouseMoveEvent = self.move_window_event
        self.input_status_bar.returnPressed.connect(self.status_bar_enter_pressed)

        self.button_refresh.clicked.connect(self.refresh_button_pressed)
        self.button_parent_directory.clicked.connect(self.up_parent_pressed)

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
        self.input_status_bar.setText(vars_util.Directory_Manager.current_directory)

    def show_settings_page(self):
        self.main_content.setCurrentIndex(2)
        self.input_status_bar.setReadOnly(True)
        self.input_status_bar.setText("SETTINGS")

    def update_file_explorer(self):
        self.file_explorer.clearContents()
        self.file_explorer.setRowCount(0)

        files = backend.file_explorer_management.get_files_in_cur_directory()
        row_count = 0
        for file in files:
            self.file_explorer.insertRow(row_count)

            self.file_explorer.setCellWidget(row_count, File_Explorer_Keys.NAME, self.get_name_and_icon_for_table(file.file_name))
            self.file_explorer.setItem(row_count, File_Explorer_Keys.DATE_MODIFIED, QTableWidgetItem(file.get_date_modified_str()))
            self.file_explorer.setItem(row_count, File_Explorer_Keys.TYPE, QTableWidgetItem(file.extension.strip('.')))
            if not file.point_is_dir():
                self.file_explorer.setItem(row_count, File_Explorer_Keys.SIZE, QTableWidgetItem(file.get_size_str()))
            
            row_count += 1

        self.input_status_bar.setText(vars_util.Directory_Manager.current_directory)
        self.label_extra_information.setText(f"{len(files)} items in directory")

    def get_name_and_icon_for_table(self, name):
        base_widget = QWidget()
        base_layout = QHBoxLayout()

        base_widget.setStyleSheet("QWidget { background: transparent; }")

        file_icon_widget = QLabel("ENOUGH")
        file_icon_widget.setPixmap(QPixmap(vars_util.Directory_Manager.get_dir_image_from_icons("default_no_file_icon.png")))
        file_icon_widget.setScaledContents(True)
        file_icon_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        file_icon_widget.setFixedSize(20,20)

        file_name_widget = QLabel(name)
        file_name_widget.setSizePolicy(QSizePolicy.Policy.Maximum,QSizePolicy.Policy.Ignored)

        base_layout.setContentsMargins(6,0,6,0)
        base_layout.setSpacing(6)
        base_layout.addWidget(file_icon_widget)
        base_layout.addWidget(file_name_widget)
        base_layout.addStretch(1)

        base_widget.setLayout(base_layout)
        return base_widget
    
    # helpers for fullscreening
    def display_fullscreen_enabled(self):
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.button_fullscreen_window.setIcon(QIcon(vars_util.Directory_Manager.get_dir_image_from_icons("fullscreen_2.png")))

    def display_fullscreen_unenabled(self):
        self.setWindowState(Qt.WindowState.WindowActive)
        self.button_fullscreen_window.setIcon(QIcon(vars_util.Directory_Manager.get_dir_image_from_icons("fullscreen.png")))

    # MUST TAKE IN QPOINT
    def check_for_special_bounds(self, pos : QPoint):
        screen_area_geometry = QApplication.primaryScreen().geometry()
        screen_area_geometry = (screen_area_geometry.width(), screen_area_geometry.height())

        taskbar_height = vars_util.Window_Config.get_taskbar_height()
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
            input_text=vars_util.Directory_Manager.default_directory
        input_text = vars_util.convert_to_path_str(input_text)
        # handle doing
        if vars_util.is_dir_given_path(input_text):
            vars_util.Directory_Manager.current_directory = input_text
            vars_util.Directory_Manager.current_directory_path = vars_util.Directory_Manager.split_path_into_list(vars_util.Directory_Manager.current_directory)
            self.update_file_explorer()
        else:
            pass

    # todo
    def refresh_button_pressed(self):
        self.update_file_explorer()

    def up_parent_pressed(self):
        # means we're only looking at the drive
        if len(vars_util.Directory_Manager.current_directory_path) == 1:
            return
        if vars_util.Directory_Manager.current_directory_path[1] == "":
            return
        vars_util.Directory_Manager.current_directory_path.pop()
        vars_util.Directory_Manager.current_directory = vars_util.Directory_Manager.compile_list_into_path(vars_util.Directory_Manager.current_directory_path)

        self.input_status_bar.setText(vars_util.Directory_Manager.current_directory)
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
        subprocess_run(vars_util.get_open_file_explorer_command())

    def mousePressEvent(self, event):
        self.click_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if Main_Application.window_at_top:
            self.display_fullscreen_enabled()

def start_application():
    app = QApplication([])

    # define all QT variables here

    window = Main_Application(app)
    window.show()

    sys.exit(app.exec())
