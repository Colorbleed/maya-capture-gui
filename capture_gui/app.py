import json
import logging
import os
import tempfile

import capture
import maya.cmds as cmds

from .vendor.Qt import QtCore, QtWidgets, QtGui
from . import lib
from . import plugin
from .accordion import AccordionWidget

log = logging.getLogger("Capture Gui")


class ClickLabel(QtWidgets.QLabel):
    """A QLabel that emits a clicked signal when clicked upon."""
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        return super(ClickLabel, self).mouseReleaseEvent(event)


class PreviewWidget(QtWidgets.QWidget):
    """
    The playblast image preview widget.

    Upon refresh it will retrieve the options through the function set as
    `options_getter` and make a call to `capture.capture()` for a single
    frame (playblasted) snapshot. The result is displayed as image.
    """

    def __init__(self, options_getter, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Add attributes
        self.initialized = False
        self.options_getter = options_getter
        self.preview = ClickLabel()
        self.preview.setFixedWidth(1280 / 4)
        self.preview.setFixedHeight(720 / 4)

        # region Build
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)
        self.layout.addWidget(self.preview)
        # endregion Build

        # Connect widgets to functions
        self.preview.clicked.connect(self.refresh)

    def refresh(self):
        """Refresh the playblast preview"""

        frame = cmds.currentTime(query=True)

        # When playblasting outside of an undo queue it seems that undoing
        # actually triggers a reset to frame 0. As such we sneak in the current
        # time into the undo queue to enforce correct undoing.
        cmds.currentTime(frame, update=True)

        with lib.no_undo():
            options = self.options_getter()

            tempdir = tempfile.mkdtemp()

            # override settings that are constants for the preview
            options = options.copy()
            options['complete_filename'] = os.path.join(tempdir, "temp.jpg")
            options['width'] = 1280 / 4
            options['height'] = 720 / 4
            options['viewer'] = False
            options['frame'] = frame
            options['off_screen'] = True
            options['format'] = "image"
            options['compression'] = "jpg"
            options['sound'] = None

            fname = capture.capture(**options)
            if not fname:
                log.warning("Preview failed")
                return

            image = QtGui.QPixmap(fname)
            self.preview.setPixmap(image)
            os.remove(fname)

    def showEvent(self, event):
        """Initialize when shown"""
        if not self.initialized:
            self.refresh()

        self.initialized = True
        event.accept()


class PresetWidget(QtWidgets.QWidget):
    """Preset Widget

    Allows the user to set preferences and create presets to load before 
    capturing.

    """

    preset_loaded = QtCore.Signal(dict)
    config_opened = QtCore.Signal()

    label = "Presets"

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.option_widgets = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        presets = QtWidgets.QComboBox()
        presets.setFixedWidth(200)
        presets.addItem("*")

        # Icons
        icon_path = os.path.join(os.path.dirname(__file__), "resources")
        save_icon = os.path.join(icon_path, "save.png")
        load_icon = os.path.join(icon_path, "import.png")
        config_icon = os.path.join(icon_path, "config.png")

        # Create buttons
        save = QtWidgets.QPushButton()
        save.setIcon(QtWidgets.QIcon(save_icon))
        save.setFixedWidth(30)
        save.setToolTip("Save Preset")
        save.setStatusTip("Save Preset")

        load = QtWidgets.QPushButton()
        load.setIcon(QtWidgets.QIcon(load_icon))
        load.setFixedWidth(30)
        load.setToolTip("Load Preset")
        save.setStatusTip("Load Preset")

        config = QtWidgets.QPushButton()
        config.setIcon(QtWidgets.QIcon(config_icon))
        config.setFixedWidth(30)
        config.setToolTip("Preset configuration")
        config.setStatusTip("Preset configuration")

        layout.addWidget(presets)
        layout.addWidget(save)
        layout.addWidget(load)
        layout.addWidget(config)

        self.config = config
        self.load = load
        self.save = save
        self.presets = presets

        # Signals
        save.clicked.connect(self.save_preset)
        load.clicked.connect(self.import_preset)
        config.clicked.connect(self.config_opened)
        presets.currentIndexChanged.connect(self.load_active_preset)

    def import_preset(self):
        """Load preset files to override output values"""

        filters = "Text file (*.json)"
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                            "Open preference file",
                                                            "/home",
                                                            filters)
        if not filename:
            return

        # create new entry in combobox
        self.add_preset(filename)

        # read file
        return self.load()

    def load_active_preset(self):
        """Load the active preset.
        
        :return: collection of preset inputs
        :rtype: dict
        """
        filename = self.presets.currentText()
        if filename == "*":
            return {}

        preset = lib.load_json(filename)

        # Emit preset load signal
        self.preset_loaded.emit(preset)

        return preset

    def add_preset(self, filename):
        """
        Add the filename to the preset list and set the index to the filename
        :param filename: the filename of the preset loaded
        :type filename: str
        
        :return: None 
        """
        self.presets.blockSignals(True)
        item_index = 0
        item_count = self.presets.count()
        if item_count > 1:
            current_items = [self.presets.itemText(i)
                             for i in range(item_count)]

            # get index of the item from the combobox
            if filename not in current_items:
                self.presets.addItem(filename)

            item_index = self.presets.findText(filename)
        else:
            self.presets.addItem(filename)
            item_index += 1

        # select item
        self.presets.setCurrentIndex(item_index)
        self.presets.blockSignals(False)

    def save_preset(self, inputs):
        """Save inputs to a file"""

        filters = "Text file (*.json)"
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                            "Save preferences",
                                                            "",
                                                            filters)
        if not filename:
            return

        with open(filename, "w") as f:
            json.dump(inputs, f, sort_keys=True,
                      indent=4, separators=(',', ': '))

        return filename

    def get_presets(self):
        """Return all currently listed presets"""
        configurations = [self.presets.itemText(i) for
                          i in range(self.presets.count())]

        return configurations

    def get_preset(self, filename):

        assert filename in self.get_presets()

        # if filename not in self.get_presets():
        #     self.preset_list.addItem(filename)
        idx = self.presets.findText(filename)
        self.presets.setCurrentIndex(idx)

    def apply_inputs(self, settings):
        """Apply saved settings of previous session

        :param settings: collection of settings based on widget label
        :type settings: dict

        :return: None 
        """
        sorted_widgets = dict((widget.label, widget) for
                              widget in self.option_widgets)

        # iterate over the sorted widgets to apply the settings
        for label, widget in sorted_widgets.items():
            widget_settings = settings.get(label, None)
            if widget_settings:
                widget.apply_inputs(widget_settings)


class App(QtWidgets.QWidget):
    """
    The main application in which the widgets are placed
    """

    # Signals
    options_changed = QtCore.Signal(dict)
    viewer_start = QtCore.Signal(dict)

    # Attribues

    application_sections = ["config", "app"]

    def __init__(self, title, objectname, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Settings
        self.settingfile = self._ensure_config_exist()
        self.plugins = {
            "app": list(),
            "config": list()
        }

        # region Set Attributes
        self.setObjectName(objectname)
        self.setWindowTitle(title)

        # Set dialog window flags so the widget can be correctly parented
        # to Maya main window
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)
        self.setProperty("saveWindowPref", True)
        # endregion Set Attributes

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Add accordion widget (Maya attribute editor style)
        self.widgetlibrary = AccordionWidget(self)
        self.widgetlibrary.setRolloutStyle(AccordionWidget.Maya)

        # Add separate widgets
        self.widgetlibrary.addItem("Preview",
                                   PreviewWidget(self.get_outputs),
                                   collapsed=True)

        self.presetwidget = PresetWidget()
        self.widgetlibrary.addItem("Presets", self.presetwidget)

        # add plug-in widgets
        for widget in plugin.discover():
            self.add_plugin(widget)

        self.layout.addWidget(self.widgetlibrary)

        # add standard buttons
        self.apply_button = QtWidgets.QPushButton("Capture")
        self.close_apply_button = QtWidgets.QPushButton("Capture And Close")
        self.default_buttons = QtWidgets.QHBoxLayout()
        self.default_buttons.setContentsMargins(5, 5, 5, 5)
        self.default_buttons.addWidget(self.apply_button)
        self.default_buttons.addWidget(self.close_apply_button)

        self.layout.addLayout(self.default_buttons)

        self.apply_inputs(self._read_widget_inputs())

        # default actions
        self.apply_button.clicked.connect(self.capture)
        self.close_apply_button.clicked.connect(self.capture_close)

        # signals and slots
        self.presetwidget.config_opened.connect(self.advanced_configuration)
        self.presetwidget.preset_loaded.connect(self.apply_inputs)
        self.presetwidget.save.clicked.connect(self.save_preset)

    def capture(self):
        options = self.get_outputs()
        capture.capture(options)

    def capture_close(self):
        self.capture()
        self.close()

    def advanced_configuration(self):
        """Show the advanced configuration"""

        dialog = QtWidgets.QDialog(self)
        dialog.setModal(True)
        dialog.setWindowTitle("Capture - Preset Configuration")

        config_layout = QtWidgets.QVBoxLayout()
        for widget in self.plugins["config"]:
            groupwidget = QtWidgets.QGroupBox(widget.label)
            group_layout = QtWidgets.QVBoxLayout()
            group_layout.addWidget(widget)
            groupwidget.setLayout(group_layout)
            config_layout.addWidget(groupwidget)

        dialog.setLayout(config_layout)
        dialog.show()

    def add_plugin(self, plugin):
        """Add an options widget plug-in to the UI"""

        if plugin.section not in self.application_sections:
            log.warning("{}'s section is invalid: "
                        "{}".format(plugin.label, plugin.section))
            return

        widget = plugin()
        widget.options_changed.connect(self.on_widget_settings_changed)

        # Add to plug-ins in its section
        self.plugins[widget.section].append(widget)

        # Implement additional settings depending on section
        if widget.section == "app":

            if not widget.hidden:
                item = self.widgetlibrary.addItem(widget.label, widget)

                # connect label change behaviour
                widget.label_changed.connect(item.setTitle)

    def get_outputs(self):
        """Return the settings for a capture as currently set in the Application.

        :return: a collection of settings
        :rtype: dict
        """

        # Get settings from widgets
        outputs = dict()
        for widget in self._get_plugin_widgets():
            outputs.update(widget.get_outputs())

        return outputs

    def on_widget_settings_changed(self):
        self.options_changed.emit(self.get_outputs)
        self.presetwidget.presets.setCurrentIndex(1)

    # configuration related functions

    def _ensure_config_exist(self):
        """Create the configuration file if it does not exist yet.
        
        :return: filepath of the configuration file
        :rtype: unicode
        
        """

        userdir = os.path.expanduser("~")
        capturegui_dir = os.path.join(userdir, "CaptureGUI")
        capturegui_inputs = os.path.join(capturegui_dir, "capturegui.json")
        if not os.path.exists(capturegui_dir):
            os.makedirs(capturegui_dir)

        if not os.path.isfile(capturegui_inputs):
            config = open(capturegui_inputs, "w")
            config.close()

        return capturegui_inputs

    def _store_widget_inputs(self):
        """Store all used widget settings in the local json file"""

        inputs = dict()
        config_widgets = self._get_plugin_widgets()
        for widget in config_widgets:
            settings = widget.get_inputs()
            if not isinstance(settings, dict):
                print("Settings are not a dictionary, "
                      "function only supports dictionaries for now")
                return

            inputs[widget.id] = settings

        with open(self.settingfile, "w") as f:
            log.debug("Writing JSON file: {0}".format(f))
            json.dump(inputs, f, sort_keys=True,
                      indent=4, separators=(',', ': '))

    def _read_widget_inputs(self):
        """Read the stored widget inputs"""
        inputs = {}
        if not os.path.isfile(self.settingfile):
            return inputs

        try:
            with open(self.settingfile, "r") as f:
                log.debug("Reading JSON file: {0}".format(f))
                inputs = json.load(f)
        except ValueError as error:
            log.error(str(error))

        return inputs

    def _get_plugin_widgets(self):
        """List all plug-in widgets.
        
        :return: The plug-in widgets in *all* sections
        :rtype: list
        
        """

        widgets = list()
        for section in self.plugins.values():
            widgets.extend(section)

        return widgets

    def apply_inputs(self, inputs):
        """Apply all the settings of the widgets
        
        :param inputs: collection of input values based on the GUI
        :type inputs: dict
        
        :return: None 
        """
        if not inputs:
            return

        sorted_widgets = dict((widget.id, widget) for
                              widget in self._get_plugin_widgets())

        # iterate over the sorted widgets to apply the settings
        for widget_id, widget in sorted_widgets.items():
            widget_inputs = inputs.get(widget_id, None)
            if not widget_inputs:
                continue
            widget.apply_inputs(widget_inputs)

    def save_preset(self):
        """Save the inputs of all the plugins in a preset"""

        inputs = self.get_outputs()
        filename = self.presetwidget.save_preset(inputs)

        self.presetwidget.get_preset(filename)

    # override close event to ensure the input are stored

    def closeEvent(self, event):
        """
        Custom close event to write the settings
        :param event: 
        :return: 
        """

        self._store_widget_inputs()
        event.accept()
