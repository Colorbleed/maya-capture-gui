import os

from capture_gui.vendor.Qt import QtCore, QtWidgets
from capture_gui import plugin, lib


class IoPlugin(plugin.Plugin):
    """Codec widget.

    Allows to set format, compression and quality.

    """
    id = "IO"
    label = "Save"
    section = "app"
    order = 40

    previous_playblasts = list()

    def __init__(self, parent=None):
        super(IoPlugin, self).__init__(parent=parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # checkbox
        checkbox_hlayout = QtWidgets.QHBoxLayout()
        checkbox_hlayout.setContentsMargins(5, 0, 5, 0)
        self.save_file = QtWidgets.QCheckBox(text="Save")
        self.use_default = QtWidgets.QCheckBox(text="Use Default")
        checkbox_hlayout.addWidget(self.save_file)
        checkbox_hlayout.addWidget(self.use_default)
        checkbox_hlayout.addStretch(True)

        # directory
        self.template_text = "Select a director"
        dir_hlayout = QtWidgets.QHBoxLayout()
        dir_hlayout.setContentsMargins(0, 0, 0, 0)
        dir_label = QtWidgets.QLabel("Directory :")
        self.brows = QtWidgets.QPushButton("Brows")
        self.directory_path = QtWidgets.QLineEdit()
        dir_hlayout.addWidget(dir_label)
        dir_hlayout.addWidget(self.directory_path)
        dir_hlayout.addWidget(self.brows)

        # filename
        filename_hlayout = QtWidgets.QHBoxLayout()
        filename_hlayout.setContentsMargins(0, 0, 0, 0)
        filename_label = QtWidgets.QLabel("File Name :")
        self.filename = QtWidgets.QLineEdit()
        filename_hlayout.addWidget(filename_label)
        filename_hlayout.addWidget(self.filename)

        # previous playblasts collection
        self.playblast_collection = QtWidgets.QPushButton("Play previous playblast")
        self.playblast_collection.setMenu(self._build_collection_menu())

        self._layout.addLayout(checkbox_hlayout)
        self._layout.addLayout(filename_hlayout)
        self._layout.addLayout(dir_hlayout)

        self.brows.clicked.connect(lib.browse)
        self.use_default.stateChanged.connect(self.toggle_use_default)
        self.save_file.stateChanged.connect(self.toggle_save)

        # set state of save widgets
        self.toggle_save()

    def _build_collection_menu(self):

        collection_menu = QtWidgets.QMenu()
        for playblast in self.previous_playblasts:
            name = os.path.basename(playblast)
            menu_item = collection_menu.addAction(name, objectData=playblast)
            if not os.path.exists(playblast):
                menu_item.setEnabled(False)

        return collection_menu

    def toggle_save(self):
        """Check to enable copy the playblast to a directory"""

        state = self.save_file.isChecked()
        self.use_default.setEnabled(state)
        self._set_enabled_save_widgets(state)

    def toggle_use_default(self):
        """Toggle if the file name and directory widgets are enabled"""

        state = self.use_default.isChecked()
        self._set_enabled_save_widgets(not state)

    def _set_enabled_save_widgets(self, state):
        """
        Set enable of the widgets which control the output
        
        :param state: the state of enable
        :type state: bool
        
        :rtype: None
        """

        self.filename.setEnabled(state)
        self.directory_path.setEnabled(state)
        self.brows.setEnabled(state)

    def get_outputs(self):
        """
        Get the output of the widget based on the user's inputs
        
        :return: collection of needed output values
        :rtype: dict
        """

        output = {"filename": None}
        use_default = self.use_default.isChecked()
        save = self.save_file.isChecked()
        # run playblast, don't copy to dir
        if not save:
            return

        # run playblast, copy file to given directory
        # get directory from inputs
        if not use_default:
            directory = self.directory_path.text()
            filename = self.filename.text()
            if filename:
                path = os.path.join(directory, filename)
            else:
                path = directory
        else:
            # get directory from selected folder and given name
            path = lib.default_output()

        output["filename"] = path

        return output

    def get_inputs(self):
        return {"directory": self.directory_path.text(),
                "name": self.filename.text(),
                "use_default": self.use_default.isChecked(),
                "save_file": self.save_file.isChecked()}

    def apply_inputs(self, settings):

        directory = settings.get("directory", None)
        filename = settings.get("name", None)
        use_default = settings.get("use_default", True)
        save_file = settings.get("save_file", True)

        self.filename.setText(filename)
        self.use_default.setChecked(use_default)
        self.save_file.setChecked(save_file)
        if not directory:
            self.directory_path.setPlaceholderText(self.template_text)
            return

        self.directory_path.setText(directory)
