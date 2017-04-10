import logging
import os
import tempfile
import capture

from .vendor.Qt import QtCore, QtWidgets, QtGui

import maya.cmds as cmds
from . import lib
from . import widgets

log = logging.getLogger(__name__)


class Separator(QtWidgets.QFrame):
    """A horizontal line separator looking like a Maya separator"""
    def __init__(self):
        super(Separator, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


class SeparatorHeader(QtWidgets.QWidget):
    """A label with a separator line to the right side of it."""

    def __init__(self, header=None, parent=None):
        super(SeparatorHeader, self).__init__(parent=parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        if header is None:
            header = ""

        label = QtWidgets.QLabel(header)
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(8)

        # We disable the label so it becomes Maya's grayed out darker
        # color without overriding the stylesheet so we can rely as much
        # on the styling of Maya as possible.
        label.setEnabled(False)

        label.setFont(font)
        label.setContentsMargins(0, 0, 0, 0)
        label.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                            QtWidgets.QSizePolicy.Maximum)

        separator = Separator()
        separator.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(label)
        layout.addWidget(separator)

        self.label = label


class ClickLabel(QtWidgets.QLabel):
    """A QLabel that emits a clicked signal when clicked upon."""
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):

        self.clicked.emit()
        return super(ClickLabel, self).mouseReleaseEvent(event)


class PreviewWidget(QtWidgets.QWidget):
    """The playblast image preview widget.

    Upon refresh it will retrieve the options through the function set as
    `options_getter` and make a call to `capture.capture()` for a single
    frame (playblasted) snapshot. The result is displayed as image.

    """

    def __init__(self, options_getter, parent=None):
        super(PreviewWidget, self).__init__(parent=parent)

        # Add attributes
        self.options_getter = options_getter
        self.previewstate = True
        self.preview = ClickLabel()

        # region Build
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Preview control buttons
        self.preview_control_hlayout = QtWidgets.QHBoxLayout()
        self.preview_enabled = QtWidgets.QCheckBox("Enable Preview")
        self.get_preview_button = QtWidgets.QPushButton("Preview")
        self.preview_control_hlayout.addWidget(self.preview_enabled)
        self.preview_control_hlayout.addWidget(self.get_preview_button)

        self.setLayout(self.layout)

        self.layout.addWidget(self.preview)
        self.layout.addLayout(self.preview_control_hlayout)
        # endregion Build

        # Connect widgets to functions
        self._connections()

        # Set state of preview
        self.set_preview_state()

    def _connections(self):
        """Build the link between the function and the button"""
        self.preview.clicked.connect(self.refresh)
        self.preview_enabled.toggled.connect(self.set_preview_state)
        self.get_preview_button.clicked.connect(self.get_preview)

    def refresh(self):

        if self.previewstate is False:
            error = ("Cannot show preview due to it being disabled, please"
                     "enable it in the GUI and try again")
            QtGui.QMessageBox.critical(None,
                                       "Preview Disabled",
                                       str(error),
                                       QtGui.QMessageBox.Close)

        frame = cmds.currentTime(query=True)

        # When playblasting outside of an undo queue it seems that undoing
        # actually triggers a reset to frame 0. As such we sneak in the current
        # time into the undo queue to enforce correct undoing.
        cmds.currentTime(frame, update=True)

        with lib.no_undo():
            options = self.options_getter()

            tempdir = tempfile.mkdtemp()

            # override some settings
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


## refractored application
class AppWindow(QtWidgets.QWidget):

    # Signals
    options_changed = QtCore.Signal(dict)
    viewer_start = QtCore.Signal(dict)

    def __init__(self, title, objectname, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Add attributes
        self.option_widgets = []

        # region Set Attributes
        self.setObjectName(objectname)
        self.setWindowTitle(title)

        # Set dialog window flags so the widget can be correctly parented
        # to Maya main window
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)
        self.setProperty("saveWindowPref", True)
        # endregion Set Attributes

        # region Build
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        for widget in[widgets.PresetWidget, widgets.TimeWidget,
                      widgets.CameraWidget, widgets.ScaleWidget,
                      widgets.CodecWidget, widgets.OptionsWidget]:
            self.add_options_widget(widget)
        # endregion Build

    def add_options_widget(self, plugin):
        """Add and options widget plug-in to the App"""
        widget = plugin()
        if not widget.hidden:
            header = SeparatorHeader(plugin.label)
            self.layout.addWidget(header)
            self.layout.addWidget(widget)

        widget.options_changed.connect(self.on_widget_settings_changed)

        self.option_widgets.append(widget)

    def get_options(self):
        """
        Collect all options set of all the widgets listed in the in the
        option_widgets attribute of the main app

        :return: a collection of settings
        :rtype: dict
        """

        panel = lib.get_active_editor()

        # Get settings from widgets
        options = dict()
        for widget in self.option_widgets:
            options.update(widget.get_options(panel))

        return options

## Old application
class App(QtWidgets.QWidget):
    """The main capture window.

    This hosts a Preview widget along with a list of OptionPlugin widgets that
    each set specific options for capture. The combination of these options
    is used to perform the resulting capture.

    """

    # Signals
    options_changed = QtCore.Signal(dict)
    playblast_start = QtCore.Signal(dict)       # playblast about to start
    playblast_finished = QtCore.Signal(dict)    # playblast finished
    viewer_start = QtCore.Signal(dict)          # viewer about to start

    WINDOW_OBJECT = "CaptureGUI"
    WINDOW_TITLE = "Capture"

    def __init__(self, parent=None):
        super(App, self).__init__(parent=parent)

        self.setObjectName(self.WINDOW_OBJECT)
        self.setWindowTitle(self.WINDOW_TITLE)

        # Set dialog window flags so the widget can be correctly parented
        # to Maya main window
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)

        # Makes Maya perform magic which makes the window stay
        # on top in OS X and Linux. As an added bonus, it'll
        # make Maya remember the window position
        self.setProperty("saveWindowPref", True)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        # Don't allow resizing to force minimum size
        self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        # Preview
        self.preview = PreviewWidget(self.get_options)
        self.layout.addWidget(self.preview)

        self.option_widgets = list()
        for widget in[widgets.PresetWidget, widgets.TimeWidget,
                      widgets.CameraWidget, widgets.ScaleWidget,
                      widgets.CodecWidget, widgets.OptionsWidget]:
            self.add_options_widget(widget)

        # Buttons
        self.buttonsLayout = QtWidgets.QHBoxLayout()
        self.applyButton = QtWidgets.QPushButton("Capture")
        self.applyCloseButton = QtWidgets.QPushButton("Capture and Close")
        self.buttonsLayout.addWidget(self.applyButton)
        self.buttonsLayout.addWidget(self.applyCloseButton)
        self.applyButton.clicked.connect(self.apply)
        self.applyCloseButton.clicked.connect(self.apply_and_close)
        self.layout.addLayout(self.buttonsLayout)

    def add_options_widget(self, plugin):
        """Add and options widget plug-in to the App"""
        widget = plugin()

        if not widget.hidden:
            header = SeparatorHeader(plugin.label)
            self.layout.addWidget(header)
            self.layout.addWidget(widget)

        widget.options_changed.connect(self.on_widget_settings_changed)

        self.option_widgets.append(widget)

    def get_options(self):
        """
        Collect all options set of all the widgets listed in the in the
        option_widgets attribute of the main app
        
        :return: a collection of settings
        :rtype: dict
        """

        panel = lib.get_active_editor()

        # Get settings from widgets
        options = dict()
        for widget in self.option_widgets:
            options.update(widget.get_options(panel))

        return options

    def set_preview_state(self):
        preview_state = self.preview_enabled.isChecked()
        self.preview.previewstate = preview_state
        self.preview.setVisible(preview_state)

    def apply(self, *args):

        filename = lib._browse(None)

        # Return if playblast was cancelled
        if filename is None:
            return

        options = self.get_options()

        self.playblast_start.emit(options)

        # Perform capture
        options['filename'] = filename
        options['filename'] = lib._capture(options)

        self.playblast_finished.emit(options)
        filename = options['filename']  # get filename after callbacks

        # Show viewer
        if options['viewer']:
            if filename and os.path.exists(filename):
                self.viewer_start.emit(options)
                lib.open_file(filename)
            else:
                raise RuntimeError("Can't open playblast because file "
                                   "doesn't exist: {0}".format(filename))

        return filename

    def apply_and_close(self, *args):
        """Perform a capture and close only when there is a resulting path"""

        filename = self.apply()
        if filename:
            self.close()

    def on_widget_settings_changed(self):
        options = self.get_options()
        self.options_changed.emit(options)

    def get_preview(self):
        self.preview.refresh()

    def show_presets(self):
        presetwindow = PresetsWindow(self)
        presetwindow.show()


class PresetsWindow(QtWidgets.QWidget):
    """
    The advanced preset widget.
    
    This widget is used to adjust the advanced presets of the tool and remove
    the rarely used settings from the user's view. This improves the usability
    of the interface
    """

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Set inherited attributes
        self.setWindowTitle("Advanced Presets")
        self.setObjectName("Presets")

        # Custom attributes
        self.option_widgets = []

        # Add layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setSizeConstraint(0, 0, 0, 0)

        # Advanced option widgets
        self.add_options_widget(widgets.CodecWidget)
        self.add_options_widget(widgets.OptionsWidget)

        # Buttons
        self.button_hlayout = QtWidgets.QHBoxLayout()
        self.save_presets_button = QtWidgets.QPushButton("Save Settings")
        self.close_button = QtWidgets.QPushButton("Close")

        self.button_hlayout.addWidget(self.save_presets_button)
        self.button_hlayout.addWidget(self.close_button)

        # Create connections
        self._connections()

    def _connections(self):
        self.close_button.clicked.connect(self.close)
        # self.save_presets_button.clicked.connect(self.)

    def add_options_widget(self, plugin):
        """Add and options widget plug-in to the App"""
        widget = plugin()

        if not widget.hidden:
            header = SeparatorHeader(plugin.label)
            self.layout.addWidget(header)
            self.layout.addWidget(widget)

        widget.options_changed.connect(self.on_widget_settings_changed)
        self.option_widgets.append(widget)
