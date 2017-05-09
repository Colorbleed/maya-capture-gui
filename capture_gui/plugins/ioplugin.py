import os
import logging
from functools import partial

from capture_gui.vendor.Qt import QtCore, QtWidgets
from capture_gui import plugin, lib
from capture_gui import tokens

log = logging.getLogger("IO")


class IoAction(QtWidgets.QAction):

    def __init__(self, parent, filepath):
        super(IoAction, self).__init__(parent)

        action_label = os.path.basename(filepath)

        self.setText(action_label)
        self.setData(filepath)

        # check if file exists and disable when false
        self.setEnabled(os.path.isfile(filepath))

        # get icon from file
        info = QtCore.QFileInfo(filepath)
        icon_provider = QtWidgets.QFileIconProvider()
        self.setIcon(icon_provider.icon(info))

        self.triggered.connect(self.open_object_data)

    def open_object_data(self):
        lib.open_file(self.data())


class IoPlugin(plugin.Plugin):
    """Codec widget.

    Allows to set format, compression and quality.

    """
    id = "IO"
    label = "Save"
    section = "app"
    order = 40

    def __init__(self, parent=None):
        super(IoPlugin, self).__init__(parent=parent)

        self.recent_playblasts = list()

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # region Checkboxes
        checkbox_hlayout = QtWidgets.QHBoxLayout()
        checkbox_hlayout.setContentsMargins(5, 0, 5, 0)
        self.save_file = QtWidgets.QCheckBox(text="Save")
        self.use_default = QtWidgets.QCheckBox(text="Use Default")
        self.open_viewer = QtWidgets.QCheckBox(text="View when finished")
        self.raw_frame_numbers = QtWidgets.QCheckBox(text="Raw frame numbers")
        checkbox_hlayout.addWidget(self.save_file)
        checkbox_hlayout.addWidget(self.use_default)
        checkbox_hlayout.addWidget(self.open_viewer)
        checkbox_hlayout.addWidget(self.raw_frame_numbers)
        checkbox_hlayout.addStretch(True)
        # endregion Checkboxes

        # region Directory
        self.dir_widget = QtWidgets.QWidget()
        dir_hlayout = QtWidgets.QHBoxLayout()
        dir_hlayout.setContentsMargins(0, 0, 0, 0)
        dir_label = QtWidgets.QLabel("Directory :")
        dir_label.setFixedWidth(60)
        self.browse = QtWidgets.QPushButton("Browse")
        self.directory_path = QtWidgets.QLineEdit()
        self.directory_path.setPlaceholderText("Select a directory")
        self.directory_path.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.directory_path.customContextMenuRequested.connect(self.show_token_menu)
        dir_hlayout.addWidget(dir_label)
        dir_hlayout.addWidget(self.directory_path)
        dir_hlayout.addWidget(self.browse)
        self.dir_widget.setLayout(dir_hlayout)
        # endregion Directory

        # region Recent Playblast
        self.play_recent = QtWidgets.QPushButton("Play recent playblast")
        self.recent_menu = QtWidgets.QMenu()
        self.play_recent.setMenu(self.recent_menu)
        # endregion Recent Playblast

        self._layout.addLayout(checkbox_hlayout)
        self._layout.addWidget(self.dir_widget)
        self._layout.addWidget(self.play_recent)

        self.browse.clicked.connect(self.get_save_directory)
        self.use_default.stateChanged.connect(self.toggle_use_default)
        self.save_file.stateChanged.connect(self.toggle_save)

        # set state of save widgets
        self.toggle_save()
        self.toggle_use_default()

    def toggle_save(self):
        """Check to enable copy the playblast to a directory"""

        state = self.save_file.isChecked()
        self.use_default.setEnabled(state)

    def toggle_use_default(self):
        """Toggle if the file name and directory widgets are enabled"""

        state = self.use_default.isChecked()
        self.dir_widget.setVisible(not state)

    def get_save_directory(self):
        """Return file path in which the file will be saved"""

        # Maya's browser return Linux based file paths to ensure Windows is
        # supported we use normpath
        self.directory_path.setText(os.path.normpath(lib.browse()))

    def add_playblast(self, item):
        """
        Add an item to the previous playblast menu
        
        :param item: a collection of file paths of the playblast files
        :type item: str
        
        :return: None 
        """

        if item in self.recent_playblasts:
            log.info("Item already in list")
            return

        if len(self.recent_playblasts) == 5:
            self.recent_playblasts.pop(4)

        self.recent_playblasts.insert(0, item)

        self.recent_menu.clear()
        for playblast in self.recent_playblasts:
            action = IoAction(parent=self, filepath=playblast)
            self.recent_menu.addAction(action)

    def on_playblast_finished(self, options):
        """Take action after the play blast is done"""
        playblast_file = options['filename']
        if not playblast_file:
            return
        self.add_playblast(playblast_file)

    def get_outputs(self):
        """
        Get the output of the widget based on the user's inputs
        
        :return: collection of needed output values
        :rtype: dict
        """

        output = {"filename": None,
                  "raw_frame_numbers": self.raw_frame_numbers.isChecked(),
                  "viewer": self.open_viewer.isChecked()}

        use_default = self.use_default.isChecked()
        save = self.save_file.isChecked()
        # run playblast, don't copy to dir
        if not save:
            return output

        # run playblast, copy file to given directory
        # get directory from inputs
        if not use_default:
            path = self.directory_path.text()
        else:
            # get directory from selected folder and given name
            path = lib.default_output()

        output["filename"] = path

        return output

    def get_inputs(self, as_preset):
        inputs = {"name": self.directory_path.text(),
                  "use_default": self.use_default.isChecked(),
                  "save_file": self.save_file.isChecked(),
                  "open_finished": self.open_viewer.isChecked(),
                  "recent_playblasts": self.recent_playblasts,
                  "raw_frame_numbers": self.raw_frame_numbers.isChecked()}

        if as_preset:
            inputs["recent_playblasts"] = []

        return inputs

    def apply_inputs(self, settings):

        directory = settings.get("name", None)
        use_default = settings.get("use_default", True)
        save_file = settings.get("save_file", True)
        open_finished = settings.get("open_finished", True)
        raw_frame_numbers = settings.get("raw_frame_numbers", False)

        previous_playblasts = settings.get("recent_playblasts", [])

        self.use_default.setChecked(use_default)
        self.save_file.setChecked(save_file)
        self.open_viewer.setChecked(open_finished)
        self.raw_frame_numbers.setChecked(raw_frame_numbers)

        for playblast in reversed(previous_playblasts):
            self.add_playblast(playblast)

        self.directory_path.setText(directory)

    def token_menu(self):
        """
        Build the token menu based on the registered tokens
        
        :returns: Menu
        :rtype: QtWidgets.QMenu
        """
        menu = QtWidgets.QMenu(self)
        registered_tokens = tokens.list_tokens()

        for token, value in registered_tokens.items():
            action = QtWidgets.QAction(value['label'], menu)
            fn = partial(self.directory_path.insert, token)
            action.triggered.connect(fn)
            menu.addAction(action)

        return menu

    def show_token_menu(self, pos):
        """Show custom manu on position of widget"""
        menu = self.token_menu()
        globalpos = QtCore.QPoint(self.directory_path.mapToGlobal(pos))
        menu.exec_(globalpos)
