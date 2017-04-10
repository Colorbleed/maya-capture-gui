import sys
import math
from functools import partial

import maya.cmds as mc
from .vendor.Qt import QtCore, QtWidgets
import capture

from . import lib


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
        cam = lib.get_current_camera()
        self.on_refresh(camera=cam)

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

        idx = self.cameras.currentIndex()
        camera = str(self.cameras.itemText(idx)) if idx != -1 else None

        return {
            "camera": camera
        }

    def on_refresh(self, camera=None):
        """Refresh the camera list with all current cameras in scene.

        A currentIndexChanged signal is only emitted for the cameras combobox
        when the camera is different at the end of the refresh.

        Args:
            camera (str): When name of camera is passed it will try to select
                the camera with this name after the refresh.

        Returns:
            None

        """

        cam = self.get_options()['camera']

        # Get original selection
        if camera is None:
            index = self.cameras.currentIndex()
            if index != -1:
                camera = str(self.cameras.itemText(index))

        self.cameras.blockSignals(True)

        # Update the list with available cameras
        self.cameras.clear()

        cam_shapes = mc.ls(type="camera")
        cam_transforms = mc.listRelatives(cam_shapes,
                                          parent=True,
                                          fullPath=True)
        self.cameras.addItems(cam_transforms)

        # If original selection, try to reselect
        self.select_camera(camera)

        self.cameras.blockSignals(False)

        # If camera changed emit signal
        if cam != self.get_options()['camera']:
            idx = self.cameras.currentIndex()
            self.cameras.currentIndexChanged.emit(idx)


class ScaleWidget(OptionsPlugin):
    """Scale widget.

    Allows to set scale based on set of options.

    """
    label = "Resolution"

    scale_changed = QtCore.Signal()

    ScaleWindow = "From Window"
    ScaleRenderSettings = "From Render Settings"
    ScaleCustom = "Custom"

    def __init__(self, parent=None):
        super(ScaleWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # Scale
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.ScaleWindow,
                            self.ScaleRenderSettings,
                            self.ScaleCustom])
        self.mode.setCurrentIndex(1)  # Default: From render settings

        # Custom width/height
        self.resolution = QtWidgets.QWidget()
        self.resolution.setContentsMargins(0, 0, 0, 0)
        resolution_layout = QtWidgets.QHBoxLayout()
        resolution_layout.setContentsMargins(0, 0, 0, 0)
        resolution_layout.setSpacing(0)

        self.resolution.setLayout(resolution_layout)
        self.width = QtWidgets.QSpinBox()
        self.width.setMinimum(0)
        self.width.setMaximum(99999)
        self.width.setValue(1920)
        self.height = QtWidgets.QSpinBox()
        self.height.setMinimum(0)
        self.height.setMaximum(99999)
        self.height.setValue(1080)

        resolution_layout.addWidget(self.width)
        resolution_layout.addWidget(self.height)

        self.scale_result = QtWidgets.QLineEdit()
        self.scale_result.setReadOnly(True)

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
        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.resolution)
        self._layout.addLayout(self.percent_layout)
        self._layout.addWidget(self.scale_result)

        # refresh states
        self.on_mode_changed()
        self.on_scale_changed()

        # connect signals
        self.mode.currentIndexChanged.connect(self.on_mode_changed)
        self.mode.currentIndexChanged.connect(self.on_scale_changed)
        self.percent.valueChanged.connect(self.on_scale_changed)
        self.width.valueChanged.connect(self.on_scale_changed)
        self.height.valueChanged.connect(self.on_scale_changed)

    def on_mode_changed(self):
        """Update the width/height enabled state when mode changes"""

        if self.mode.currentText() != self.ScaleCustom:
            self.width.setEnabled(False)
            self.height.setEnabled(False)
            self.resolution.hide()
        else:
            self.width.setEnabled(True)
            self.height.setEnabled(True)
            self.resolution.show()

    def on_scale_changed(self):
        """Update the resulting resolution label"""

        options = self.get_options()

        label = "Result: {0}x{1}".format(int(options["width"]),
                                         int(options["height"]))

        self.scale_result.setText(label)

    def get_options(self, panel=""):
        """Return width x height defined by the combination of settings

        Returns:
            dict: width and height key values

        """
        mode = self.mode.currentText()

        if mode == self.ScaleCustom:
            width = self.width.value()
            height = self.height.value()

        elif mode == self.ScaleRenderSettings:
            # width height from render resolution
            width = mc.getAttr("defaultResolution.width")
            height = mc.getAttr("defaultResolution.height")

        elif mode == self.ScaleWindow:
            # width height from active view panel size

            if not panel:
                # No panel would be passed when updating in the UI as such
                # the resulting resolution can't be previewed. But this should
                # never happen when starting the capture.
                width = 0
                height = 0
            else:
                width = mc.control(panel, q=True, width=True)
                height = mc.control(panel, q=True, height=True)

        else:
            raise NotImplementedError("Unsupported scale mode: "
                                      "{0}".format(mode))

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
        self.quality.setToolTip("Compression quality percentage")

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
        self.show_curves = QtWidgets.QCheckBox("\t\t\t Show NURBS Curves")
        self.show_curves.setChecked(False)
        self.high_quality = QtWidgets.QCheckBox()
        self.high_quality.setChecked(True)
        self.high_quality.setText("\t\t\t HQ: Viewport 2.0 + AA")
        self.use_isolate_view = QtWidgets.QCheckBox("Use isolate view from "
                                                    "active panel")
        self.use_isolate_view.setChecked(True)
        self.offscreen = QtWidgets.QCheckBox("Render offscreen")
        self.offscreen.setToolTip("Whether to the playblast view "
                                  "visually on- or off-screen during "
                                  "playblast")
        self.offscreen.setChecked(True)

        self._layout.addWidget(self.override_viewport)
        self._layout.addWidget(self.show_curves)
        self._layout.addWidget(self.high_quality)
        self._layout.addWidget(self.use_isolate_view)
        self._layout.addWidget(self.offscreen)

        # signals
        self.use_isolate_view.stateChanged.connect(self.options_changed)
        self.high_quality.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.options_changed)
        self.show_curves.stateChanged.connect(self.options_changed)

        self.override_viewport.stateChanged.connect(
            self.high_quality.setEnabled)

        self.override_viewport.stateChanged.connect(
            self.show_curves.setEnabled)

    def get_options(self, panel=""):
        show_curves = self.show_curves.isChecked()
        high_quality = self.high_quality.isChecked()
        override_viewport_options = self.override_viewport.isChecked()
        use_isolate_view = self.use_isolate_view.isChecked()
        offscreen = self.offscreen.isChecked()

        options = dict()

        # use settings from active panel
        view = capture.parse_view(panel)
        options.update(view)
        options.pop("camera", None)

        # use active sound track
        scene = capture.parse_active_scene()
        options['sound'] = scene['sound']

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
                       'nurbsCurves',
                       'nParticles',
                       'nRigids',
                       'pivots',
                       'grid',
                       'headsUpDisplay',
                       'strokes',
                       'cameras']
            if show_curves:
                exclude.remove('nurbsCurves')
            for key in exclude:
                options['viewport_options'][key] = False

        # Get isolate view members of the panel
        if use_isolate_view:
            filter_set = mc.modelEditor(panel, query=True, viewObjects=True)
            isolate = mc.sets(filter_set, q=1) if filter_set else None
            options['isolate'] = isolate

        return options


class PresetWidget(OptionsPlugin):

    label = "Presets"
    presetfile = None

    def __init__(self, parent=None):
        OptionsPlugin.__init__(self, parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.preset_combobox = QtWidgets.QComboBox()
        self.preset_combobox.setFixedWidth(200)

        # buttons
        save_icon = self.style().standardIcon(getattr(QtWidgets.QStyle,
                                                      "SP_DriveFDIcon"))
        load_icon = self.style().standardIcon(getattr(QtWidgets.QStyle,
                                                      "SP_DirOpenIcon"))
        customize_icon = self.style().standardIcon(getattr(QtWidgets.QStyle,
                                                           "SP_FileDialogListView"))

        self.preset_save = QtWidgets.QPushButton()
        self.preset_save.setIcon(save_icon)
        self.preset_save.setFixedWidth(30)
        self.preset_load = QtWidgets.QPushButton()
        self.preset_load.setIcon(load_icon)
        self.preset_load.setFixedWidth(30)
        self.preset_customize = QtWidgets.QPushButton()
        self.preset_customize.setIcon(customize_icon)
        self.preset_customize.setFixedWidth(30)

        self._layout.addWidget(self.preset_combobox)
        self._layout.addWidget(self.preset_save)
        self._layout.addWidget(self.preset_load)
        self._layout.addWidget(self.preset_customize)

        self.preset_load.clicked.connect(self.load_presets)

    def load_presets(self):
        filename, _ = QtWidgets.QFileDialog(self,
                                            "Load Preset",
                                            r"C:\Users\User")

        return lib.load_json(filename)


class TimeWidget(OptionsPlugin):
    """Widget for time based options

    This does not emit options changed signals because the time settings does
    not influence the visual representation of the preview snapshot.

    """

    label = "Time Range"

    RangeTimeSlider = "Time Slider"
    RangeStartEnd = "Start/End"

    def __init__(self, parent=None):
        super(TimeWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.RangeTimeSlider, self.RangeStartEnd])

        self.start = QtWidgets.QSpinBox()
        self.start.setRange(-sys.maxint, sys.maxint);
        self.end = QtWidgets.QSpinBox()
        self.end.setRange(-sys.maxint, sys.maxint);

        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.start)
        self._layout.addWidget(self.end)

        self.on_mode_changed()  # force enabled state refresh
        self.mode.currentIndexChanged.connect(self.on_mode_changed)

    def on_mode_changed(self):

        mode = self.mode.currentText()

        if mode == self.RangeTimeSlider:
            start, end = lib.get_time_slider_range()

            self.start.setEnabled(False)
            self.start.setValue(start)
            self.end.setEnabled(False)
            self.end.setValue(end)

        elif mode == self.RangeStartEnd:
            self.start.setEnabled(True)
            self.end.setEnabled(True)

    def get_options(self, panel=""):

        mode = self.mode.currentText()

        if mode == self.RangeTimeSlider:
            start, end = lib.get_time_slider_range()

        elif mode == self.RangeStartEnd:
            start = self.start.value()
            end = self.end.value()

        else:
            raise NotImplementedError("Unsupported time range mode: "
                                      "{0}".format(mode))

        return {
            "start_frame": start,
            "end_frame": end
        }


