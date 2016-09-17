import logging
import math
import os
import tempfile
import capture
from functools import partial

from .vendor.Qt import QtCore, QtWidgets

import maya.cmds as mc
from . import lib

log = logging.getLogger(__name__)

# TODO: Implement way to set "default browse location" override


class Separator(QtWidgets.QFrame):
    """A horizontal line separator looking like a Maya separator"""
    def __init__(self):
        super(Separator, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


class OptionsPlugin(QtWidgets.QWidget):
    """Base class for Option Widgets.

    This is a regular Qt widget that can be added to the capture interface
    as an additional component, like a plugin.

    """

    label = ""
    hidden = False
    options_changed = QtCore.Signal()

    def get_options(self, panel=""):
        """Return the options as set in this plug-in widget.

        This is used to identify the settings to be used for the playblast.
        As such the values should be returned in a way that a call to
        `capture.capture()` would understand as arguments.

        Args:
            panel (str): The active modelPanel of the user. This is passed so
                values could potentially be parsed from the active panel

        Returns:
            dict: The options for this plug-in. (formatted `capture` style)

        """
        return dict()


class CameraWidget(OptionsPlugin):
    """Camera widget.

    Allows to select a camera.

    """
    label = "Camera"

    def __init__(self, parent=None):
        super(CameraWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.cameras = QtWidgets.QComboBox()
        self.cameras.setMinimumWidth(200)

        self.get_active = QtWidgets.QPushButton("Get active")
        self.get_active.setToolTip("Set camera from currently active view")
        self.refresh = QtWidgets.QPushButton("Refresh")
        self.refresh.setToolTip("Refresh the list of cameras")

        self._layout.addWidget(self.cameras)
        self._layout.addWidget(self.refresh)
        self._layout.addWidget(self.get_active)

        self.set_active_cam()

        # Signals
        self.get_active.clicked.connect(self.set_active_cam)
        self.refresh.clicked.connect(self.on_refresh)

        self.cameras.currentIndexChanged.connect(self.options_changed)

    def set_active_cam(self):
        self.on_refresh(reselect=False)
        cam = lib.get_current_camera()
        self.select_camera(cam)

    def select_camera(self, cam):
        if cam:
            # Ensure long name
            cameras = mc.ls(cam, long=True)
            if not cameras:
                return
            cam = cameras[0]

            # Find the index in the list
            for i in range(self.cameras.count()):
                value = str(self.cameras.itemText(i))
                if value == cam:
                    self.cameras.setCurrentIndex(i)
                    return

    def get_options(self, panel=""):
        """Return currently selected camera from combobox."""

        return {
            "camera": str(self.cameras.itemText(self.cameras.currentIndex()))
        }

    def on_refresh(self, reselect=True):

        # Get original selection
        selected_cam = None
        if reselect:
            index = self.cameras.currentIndex()
            if index:
                selected_cam = str(self.cameras.itemText(index))

        # Update the list with available cameras
        self.cameras.clear()

        cam_shapes = mc.ls(type="camera")
        cam_transforms = mc.listRelatives(cam_shapes,
                                          parent=True,
                                          fullPath=True)
        self.cameras.addItems(cam_transforms)

        # If original selection, try to reselect
        if selected_cam:
            self.select_camera(selected_cam)


class ScaleWidget(OptionsPlugin):
    """Scale widget.

    Allows to set scale based on set of options.

    """
    label = "Resolution"

    scale_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(ScaleWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # Scale
        self.scale_mode = QtWidgets.QComboBox()
        self.scale_mode.addItems(["From Window",
                                  "From Render Settings",
                                  "Custom"])
        self.scale_mode.setCurrentIndex(1)  # Default: From render settings
        self.scale_layout = QtWidgets.QHBoxLayout()
        self.width = QtWidgets.QSpinBox()
        self.width.setMinimum(0)
        self.width.setMaximum(99999)
        self.width.setValue(1920)
        self.height = QtWidgets.QSpinBox()
        self.height.setMinimum(0)
        self.height.setMaximum(99999)
        self.height.setValue(1080)

        self.scale_layout.addWidget(self.width)
        self.scale_layout.addWidget(self.height)

        self.scale_result = QtWidgets.QLineEdit()
        self.scale_result.setReadOnly(True)
        self.scale_result.setEnabled(False)

        self._layout.addWidget(self.scale_mode)

        # Percentage
        self.percent_label = QtWidgets.QLabel("Scale")
        self.percent = QtWidgets.QDoubleSpinBox()
        self.percent.setMinimum(0.01)
        self.percent.setValue(1.0)  # default value
        self.percent.setSingleStep(0.05)

        self.percent_presets = QtWidgets.QHBoxLayout()
        self.percent_presets.setSpacing(4)
        for value in [0.25, 0.5, 0.75, 1.0, 2.0]:
            btn = QtWidgets.QPushButton(str(value))
            self.percent_presets.addWidget(btn)
            btn.setFixedWidth(35)
            btn.clicked.connect(partial(self.percent.setValue, value))

        self.percent_layout = QtWidgets.QHBoxLayout()
        self.percent_layout.addWidget(self.percent_label)
        self.percent_layout.addWidget(self.percent)
        self.percent_layout.addLayout(self.percent_presets)

        # Resulting scale display

        self._layout.addWidget(self.scale_mode)
        self._layout.addLayout(self.scale_layout)
        self._layout.addLayout(self.percent_layout)
        self._layout.addWidget(self.scale_result)

        self.on_scale_changed()

        # connect signals
        self.percent.valueChanged.connect(self.options_changed)
        self.scale_mode.currentIndexChanged.connect(self.options_changed)
        self.width.valueChanged.connect(self.options_changed)
        self.height.valueChanged.connect(self.options_changed)

    def on_scale_changed(self):
        """Update the resulting resolution label"""

        options = self.get_options()
        self.scale_result.setText("{0}x{1}".format(int(options["width"]),
                                                   int(options["height"])))

    def get_options(self, panel=""):
        """Return width x height defined by the combination of settings

        Returns:
            tuple: X & Y pixel width to playblast

        """

        # TODO: Implement using of different modes (e.g. from window or custom)

        # width height from render resolution
        width = mc.getAttr("defaultResolution.width")
        height = mc.getAttr("defaultResolution.height")
        scale = [width, height]

        percentage = self.percent.value()
        scale = [math.floor(x * percentage) for x in scale]

        return {
            "width": scale[0],
            "height": scale[1]
        }


class CodecWidget(OptionsPlugin):
    """Codec widget.

    Allows to set format, compression and quality.

    """
    label = "Codec"

    def __init__(self, parent=None):
        super(CodecWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.format = QtWidgets.QComboBox()
        self.compression = QtWidgets.QComboBox()
        self.quality = QtWidgets.QSpinBox()
        self.quality.setMinimum(0)
        self.quality.setMaximum(100)
        self.quality.setValue(100)

        self._layout.addWidget(self.format)
        self._layout.addWidget(self.compression)
        self._layout.addWidget(self.quality)

        self.format.currentIndexChanged.connect(self.on_format_changed)

        self.refresh()

        # Default to format 'qt'
        index = self.format.findText("qt")
        if index != -1:
            self.format.setCurrentIndex(index)

            # Default to compression 'H.264'
            index = self.compression.findText("H.264")
            if index != -1:
                self.compression.setCurrentIndex(index)

    def refresh(self):

        formats = lib.list_formats()
        self.format.clear()
        self.format.addItems(formats)

    def on_format_changed(self):
        """Refresh the available compressions."""

        format = self.format.currentText()
        compressions = lib.list_compressions(format)
        self.compression.clear()
        self.compression.addItems(compressions)

    def get_options(self, panel=""):

        format = self.format.currentText()
        compression = self.compression.currentText()
        quality = self.quality.value()

        return {
            "format": format,
            "compression": compression,
            "quality": quality
        }


class OptionsWidget(OptionsPlugin):
    """Widget for additional options

    For now used to set some default values used internally at Colorbleed.

    """
    label = "Options"

    def __init__(self, parent=None):
        super(OptionsWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.override_viewport = QtWidgets.QCheckBox("Override viewport "
                                                     "settings")
        self.override_viewport.setChecked(True)
        self.high_quality = QtWidgets.QCheckBox()
        self.high_quality.setChecked(True)
        self.high_quality.setText("HQ: Viewport 2.0 + AA")
        self.use_isolate_view = QtWidgets.QCheckBox("Use isolate view from "
                                                    "active panel")
        self.use_isolate_view.setChecked(True)
        self.offscreen = QtWidgets.QCheckBox("Render offscreen")
        self.offscreen.setToolTip("Whether to the playblast view "
                                  "visually on- or off-screen during "
                                  "playblast")
        self.offscreen.setChecked(True)

        self._layout.addWidget(self.override_viewport)
        self._layout.addWidget(self.high_quality)
        self._layout.addWidget(self.use_isolate_view)
        self._layout.addWidget(self.offscreen)

        self.override_viewport.stateChanged.connect(
            self.high_quality.setEnabled)

    def get_options(self, panel=""):

        high_quality = self.high_quality.isChecked()
        override_viewport_options = self.override_viewport.isChecked()
        use_isolate_view = self.use_isolate_view.isChecked()
        offscreen = self.offscreen.isChecked()

        options = dict()

        # Get settings from scene
        view = capture.parse_view(panel)
        scene = capture.parse_active_scene()
        options.update(view)
        options.update(scene)

        # remove parsed information we dont want
        options.pop("camera", None)
        options.pop("start_frame", None)
        options.pop("end_frame", None)

        # override default settings
        options['show_ornaments'] = False
        options['off_screen'] = offscreen
        options['viewer'] = True    # always play video for now

        # override camera options
        options['camera_options']['overscan'] = 1.0
        options['camera_options']['displayFieldChart'] = False
        options['camera_options']['displayFilmGate'] = False
        options['camera_options']['displayFilmOrigin'] = False
        options['camera_options']['displayFilmPivot'] = False
        options['camera_options']['displayGateMask'] = False
        options['camera_options']['displayResolution'] = False
        options['camera_options']['displaySafeAction'] = False
        options['camera_options']['displaySafeTitle'] = False

        # force viewport 2.0 and AA
        if override_viewport_options:
            if high_quality:
                options['viewport_options']['rendererName'] = 'vp2Renderer'
                options['viewport2_options']['multiSampleEnable'] = True
                options['viewport2_options']['multiSampleCount'] = 8

            # Exclude some default things you often don't want to see.
            exclude = ['ikHandles',
                       'locators',
                       'lights',
                       'joints',
                       'manipulators',
                       'nCloths',
                       'follicles',
                       'dimensions',
                       #  'nurbsCurves',
                       'nParticles',
                       'nRigids',
                       'pivots',
                       'grid',
                       'headsUpDisplay',
                       'strokes',
                       'cameras']
            for key in exclude:
                options['viewport_options'][key] = False

        # Get isolate view members of the panel
        if use_isolate_view:
            filter_set = mc.modelEditor(panel, query=True, viewObjects=True)
            isolate = mc.sets(filter_set, q=1) if filter_set else None
            options['isolate'] = isolate

        return options


class TimeWidget(OptionsPlugin):
    """Widget for time based options

    For now used to set some default values used internally at Colorbleed.
    """
    # TODO: Implement time widget UI
    hidden = True

    def get_options(self, panel=""):

        start, end = lib.get_time_slider_range()

        return {
            "start_frame": start,
            "end_frame": end
        }


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

        self.options_getter = options_getter

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        label = QtWidgets.QLabel("Preview")
        font = QtWidgets.QFont()
        font.setBold(True)
        font.setPointSize(8)
        label.setFont(font)
        layout.addWidget(label)

        preview = ClickLabel()
        layout.addWidget(preview)

        preview.clicked.connect(self.refresh)

        self.layout = layout
        self.preview = preview

    def refresh(self):

        frame = mc.currentTime(q=1)

        # When playblasting outside of an undo queue it seems that undoing
        # actually triggers a reset to frame 0. As such we sneak in the current
        # time into the undo queue to enforce correct undoing.
        mc.currentTime(frame, update=True)

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

            fname = capture.capture(**options)

            if not fname:
                log.warning("Preview failed")
                return

            image = QtWidgets.QPixmap(fname)
            self.preview.setPixmap(image)
            os.remove(fname)


class App(QtWidgets.QWidget):
    """The main capture window.

    This hosts a Preview widget along with a list of OptionPlugin widgets that
    each set specific options for capture. The combination of these options
    is used to perform the resulting capture.

    """

    # Signals
    options_changed = QtCore.Signal(dict)
    playblast_start = QtCore.Signal(dict)      # playblast about to start
    playblast_finished = QtCore.Signal(dict)    # playblast finished
    viewer_start = QtCore.Signal(dict)          # viewer about to start

    def __init__(self, parent=None):
        super(App, self).__init__(parent=parent)

        self.setObjectName("CaptureGUI")
        self.setWindowTitle("Capture")

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        # Preview
        self.preview = PreviewWidget(self.get_options)
        self.layout.addWidget(self.preview)
        self.layout.addWidget(Separator())

        self.option_widgets = list()
        for plugin in [TimeWidget,
                       CameraWidget,
                       ScaleWidget,
                       CodecWidget,
                       OptionsWidget]:
            self.add_options_widget(plugin)

        # Buttons
        self.buttonsLayout = QtWidgets.QHBoxLayout()
        self.applyButton = QtWidgets.QPushButton("Capture")
        self.applyCloseButton = QtWidgets.QPushButton("Capture and Close")
        self.buttonsLayout.addWidget(self.applyButton)
        self.buttonsLayout.addWidget(self.applyCloseButton)
        self.applyButton.clicked.connect(self.apply)
        self.applyCloseButton.clicked.connect(self.apply_and_close)
        self.layout.addLayout(self.buttonsLayout)

        # Slots
        self.options_changed.connect(self.preview.refresh)

        self.preview.refresh()

    def add_options_widget(self, plugin):
        """Add and options widget plug-in to the App"""
        widget = plugin()

        if not widget.hidden:
            if plugin.label:
                label = QtWidgets.QLabel(plugin.label)

                font = QtWidgets.QFont()
                font.setBold(True)
                font.setPointSize(8)

                label.setFont(font)
                label.setContentsMargins(0, 0, 0, 0)
                self.layout.addWidget(label)

            self.layout.addWidget(widget)
            self.layout.addWidget(Separator())

        widget.options_changed.connect(self.on_widget_settings_changed)

        self.option_widgets.append(widget)

    def get_options(self):

        panel = lib.get_active_editor()

        # Get settings from widgets
        options = dict()
        for widget in self.option_widgets:
            options.update(widget.get_options(panel))

        return options

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
