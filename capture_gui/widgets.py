import sys
import math
from functools import partial

import maya.cmds as cmds
import maya.OpenMaya as om
from .vendor.Qt import QtCore, QtWidgets
import capture

from . import lib

OBJECT_TYPES = ['ikHandles',
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


class OptionsPlugin(QtWidgets.QWidget):
    """Base class for Option Widgets.

    This is a regular Qt widget that can be added to the capture interface
    as an additional component, like a plugin.

    """

    id = ""
    label = ""
    section = ""
    hidden = False
    options_changed = QtCore.Signal()
    label_changed = QtCore.Signal(str)

    def get_outputs(self):
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

    def get_inputs(self):
        """
        Get all the widget's child settings
        :return: 
        """
        return dict()

    def apply_inputs(self, settings):
        """
        Parse a dictionary of settings and set the widget's settings to the 
        stored values
        :param settings: 
        :return: None 
        """
        pass


class CameraWidget(OptionsPlugin):
    """Camera widget.

    Allows to select a camera.

    """
    id = "Camera"
    label = ""
    section = "app"

    def __init__(self, parent=None):
        super(CameraWidget, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.cameras = QtWidgets.QComboBox()
        self.cameras.setMinimumWidth(200)

        self.get_active = QtWidgets.QPushButton("Get active")
        self.get_active.setToolTip("Set camera from currently active view")
        self.refresh = QtWidgets.QPushButton("Refresh")
        self.refresh.setToolTip("Refresh the list of cameras")

        self._layout.addWidget(self.cameras)
        self._layout.addWidget(self.get_active)
        self._layout.addWidget(self.refresh)

        self.set_active_cam()

        # Signals
        self.get_active.clicked.connect(self.set_active_cam)
        self.refresh.clicked.connect(self.on_refresh)

        self.cameras.currentIndexChanged.connect(self.options_changed)
        self.options_changed.connect(self.on_update_label)

        # Force update of the label
        self.on_update_label()

    def set_active_cam(self):
        cam = lib.get_current_camera()
        self.on_refresh(camera=cam)

    def select_camera(self, cam):
        if cam:
            # Ensure long name
            cameras = cmds.ls(cam, long=True)
            if not cameras:
                return
            cam = cameras[0]

            # Find the index in the list
            for i in range(self.cameras.count()):
                value = str(self.cameras.itemText(i))
                if value == cam:
                    self.cameras.setCurrentIndex(i)
                    return

    def get_outputs(self):
        """Return currently selected camera from combobox."""

        idx = self.cameras.currentIndex()
        camera = str(self.cameras.itemText(idx)) if idx != -1 else None

        return {"camera": camera}

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

        cam = self.get_outputs()['camera']

        # Get original selection
        if camera is None:
            index = self.cameras.currentIndex()
            if index != -1:
                camera = self.cameras.currentText()

        self.cameras.blockSignals(True)

        # Update the list with available cameras
        self.cameras.clear()

        cam_shapes = cmds.ls(type="camera")
        cam_transforms = cmds.listRelatives(cam_shapes,
                                            parent=True,
                                            fullPath=True)
        self.cameras.addItems(cam_transforms)

        # If original selection, try to reselect
        self.select_camera(camera)

        self.cameras.blockSignals(False)

        # If camera changed emit signal
        if cam != self.get_outputs()['camera']:
            idx = self.cameras.currentIndex()
            self.cameras.currentIndexChanged.emit(idx)

    def on_update_label(self):

        cam = self.cameras.currentText()
        cam = cam.rsplit("|", 1)[-1]  # ensure short name
        self.label = "Camera ({0})".format(cam)

        self.label_changed.emit(self.label)


class ScaleWidget(OptionsPlugin):
    """Scale widget.

    Allows to set scale based on set of options.

    """
    id = "Resolution"
    label = ""
    section = "app"

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
        resolution_layout.setSpacing(6)

        self.resolution.setLayout(resolution_layout)
        width_label = QtWidgets.QLabel("Width")
        width_label.setFixedWidth(40)
        self.width = QtWidgets.QSpinBox()
        self.width.setMinimum(0)
        self.width.setMaximum(99999)
        self.width.setValue(1920)
        heigth_label = QtWidgets.QLabel("Height")
        heigth_label.setFixedWidth(40)
        self.height = QtWidgets.QSpinBox()
        self.height.setMinimum(0)
        self.height.setMaximum(99999)
        self.height.setValue(1080)

        resolution_layout.addWidget(width_label)
        resolution_layout.addWidget(self.width)
        resolution_layout.addWidget(heigth_label)
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

    def _get_output_resolution(self):

        options = self.get_outputs()
        return int(options["width"]), int(options["height"])

    def on_scale_changed(self):
        """Update the resulting resolution label"""

        width, height = self._get_output_resolution()
        label = "Result: {0}x{1}".format(width, height)

        self.scale_result.setText(label)

        # Update label
        self.label = "Resolution ({0}x{1})".format(width, height)
        self.label_changed.emit(self.label)

    def get_outputs(self):
        """Return width x height defined by the combination of settings

        Returns:
            dict: width and height key values

        """
        mode = self.mode.currentText()
        panel = lib.get_active_editor()

        if mode == self.ScaleCustom:
            width = self.width.value()
            height = self.height.value()

        elif mode == self.ScaleRenderSettings:
            # width height from render resolution
            width = cmds.getAttr("defaultResolution.width")
            height = cmds.getAttr("defaultResolution.height")

        elif mode == self.ScaleWindow:
            # width height from active view panel size
            if not panel:
                # No panel would be passed when updating in the UI as such
                # the resulting resolution can't be previewed. But this should
                # never happen when starting the capture.
                width = 0
                height = 0
            else:
                width = cmds.control(panel, query=True, width=True)
                height = cmds.control(panel, query=True, height=True)
        else:
            raise NotImplementedError("Unsupported scale mode: "
                                      "{0}".format(mode))

        scale = [width, height]
        percentage = self.percent.value()
        scale = [math.floor(x * percentage) for x in scale]

        return {"width": scale[0], "height": scale[1]}

    def get_inputs(self):
        return {"mode": self.mode.currentText(),
                "width": self.width.value(),
                "height": self.height.value(),
                "percent": self.percent.value()}

    def apply_inputs(self, settings):
        # get value else fall back to default values
        mode = settings.get("mode", self.ScaleRenderSettings)
        width = int(settings.get("width", 1920))
        height = int(settings.get("height", 1080))
        percent = float(settings.get("percent", 1.0))

        # set values
        self.mode.setCurrentIndex(self.mode.findText(mode))
        self.width.setValue(width)
        self.height.setValue(height)
        self.percent.setValue(percent)


class CodecWidget(OptionsPlugin):
    """Codec widget.

    Allows to set format, compression and quality.

    """
    id = "Codec"
    label = ""
    section = "config"

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

    def get_outputs(self):
        """
        Get all the options from the widget
        
        :return: dictionary with the settings
        :rtype: dict
        """

        return {"format": self.format.currentText(),
                "compression": self.compression.currentText(),
                "quality": self.quality.value()}

    def get_inputs(self):
        # a bit redundant but it will work when iterating over widgets
        # so we don't have to write an exception
        return self.get_outputs()

    def apply_inputs(self, settings):
        codec_format = settings.get("format", 0)
        compr = settings.get("compression", 4)
        quality = settings.get("quality", 100)

        self.format.setCurrentIndex(self.format.findText(codec_format))
        self.compression.setCurrentIndex(self.compression.findText(compr))
        self.quality.setValue(int(quality))


class ViewportOptionWidget(OptionsPlugin):
    """Widget for additional options

    For now used to set some default values used internally at Colorbleed.

    """
    id = "Viewport Options"
    label = ""
    section = "config"

    show_types_list = []

    def __init__(self, parent=None):
        OptionsPlugin.__init__(self, parent=parent)

        self.setObjectName(self.label)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        viewport_output_layout = QtWidgets.QHBoxLayout()
        self.override_viewport = QtWidgets.QCheckBox("Override viewport "
                                                     "settings")
        self.override_viewport.setChecked(True)

        # Visibility of object types
        # region Show
        self.inputs = {}

        self.show_types_button = None
        self.show_types_menu = None
        self.toggle_all = None
        self.toggle_none = None
        show_button = self.show_menu()

        viewport_output_layout.addWidget(show_button)
        viewport_output_layout.addWidget(self.override_viewport)
        # endregion Show

        # region Checkboxes
        ## Remove setChecked(bool) of widgets to enswure ini file can
        ## take over, testings this atm
        self.high_quality = QtWidgets.QCheckBox()
        self.high_quality.setText("\t\t\t HQ: Viewport 2.0 + AA")
        self.use_isolate_view = QtWidgets.QCheckBox("Use isolate view from "
                                                    "active panel")
        self.offscreen = QtWidgets.QCheckBox("Render offscreen")
        self.offscreen.setToolTip("Whether to the playblast view "
                                  "visually on- or off-screen during "
                                  "playblast")

        # endregion Checkboxes

        self._layout.addLayout(viewport_output_layout)
        self._layout.addWidget(self.high_quality)
        self._layout.addWidget(self.offscreen)

        # signals
        self.connections()

    def connections(self):
        """Link actions to widgets"""
        self.use_isolate_view.stateChanged.connect(self.options_changed)
        self.high_quality.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.toggle_override)

    def show_menu(self):
        """
        Build the menu to select which items are shown in the capture
        :return: a QPushButton instance with a menu
        :rtype: QtGui.QPushButton
        """

        # create the menu button
        self.show_types_button = QtWidgets.QPushButton("Show")
        self.show_types_menu = QtWidgets.QMenu(self)
        self.show_types_menu.setWindowTitle("Show")
        self.show_types_button.setFixedWidth(150)
        self.show_types_menu.setFixedWidth(150)
        self.show_types_menu.setTearOffEnabled(True)

        # Show all check
        self.toggle_all = QtWidgets.QAction(self.show_types_menu, text="All")
        self.toggle_none = QtWidgets.QAction(self.show_types_menu, text="None")
        self.show_types_menu.addAction(self.toggle_all)
        self.show_types_menu.addAction(self.toggle_none)
        self.show_types_menu.addSeparator()

        # create checkbox for
        for obj_type in OBJECT_TYPES:
            # create checkbox for object type
            action = QtWidgets.QAction(self.show_types_menu, text=obj_type)
            action.setCheckable(True)
            # add to menu and list of instances
            self.show_types_list.append(action)
            self.show_types_menu.addAction(action)

        self.show_types_button.setMenu(self.show_types_menu)
        self.toggle_all.triggered.connect(self.toggle_all_visbile)
        self.toggle_none.triggered.connect(self.toggle_all_hide)

        return self.show_types_button

    def toggle_override(self):
        """Enable or disable show menu when override is checked"""
        state = self.override_viewport.isChecked()
        self.show_types_button.setEnabled(state)
        self.high_quality.setEnabled(state)

    def toggle_all_visbile(self):
        """
        Set all object types off or on depending on the state
        :return: None
        """
        for objecttype in self.show_types_list:
            objecttype.setChecked(True)

    def toggle_all_hide(self):
        """
        Set all object types off or on depending on the state
        :return: None
        """
        for objecttype in self.show_types_list:
            objecttype.setChecked(False)

    def get_show_inputs(self):
        """
        Return checked state of show menu items
        :return: 
        """

        show_inputs = {}
        # get all checked objects
        for action in self.show_types_list:
            show_inputs[action.text()] = action.isChecked()

        return show_inputs

    def get_inputs(self):
        """
        Return the widget options
        :return: dictionary with all the settings of the widgets 
        """
        inputs = {"high_quality": self.high_quality.isChecked(),
                  "override_viewport_options": self.override_viewport.isChecked(),
                  "use_isolate_view": self.use_isolate_view.isChecked(),
                  "offscreen": self.offscreen.isChecked()}

        inputs.update(self.get_show_inputs())

        return inputs

    def _copy_inputs(self, inputs):
        self.inputs = inputs.copy()

    def apply_inputs(self, inputs):
        """
        Apply the settings which can be adjust by the user or presets
        :param inputs: a collection of settings
        :type inputs: dict
        
        :return: None
        """
        # get input values directly from input given
        override_viewport = inputs.get("override_viewport_options", True)
        high_quality = inputs.get("high_quality", True)
        use_isolate_view = inputs.get("use_isolate_view", False)
        offscreen = inputs.get("offscreen", False)

        self.high_quality.setChecked(high_quality)
        self.override_viewport.setChecked(override_viewport)
        self.show_types_button.setEnabled(override_viewport)
        self.use_isolate_view.setChecked(use_isolate_view)
        self.offscreen.setChecked(offscreen)

        for action in self.show_types_list:
            action.setChecked(inputs.get(action.text(), True))

    def get_outputs(self):
        """
        Retrieve all settings of each available sub widgets
        :return: 
        """

        outputs = dict()

        high_quality = self.high_quality.isChecked()
        override_viewport_options = self.override_viewport.isChecked()
        offscreen = self.offscreen.isChecked()

        # use settings from active panel
        panel = lib.get_active_editor()
        view = capture.parse_view(panel)
        outputs.update(view)
        outputs.pop("camera", None)

        # use active sound track
        scene = capture.parse_active_scene()
        outputs['sound'] = scene['sound']

        # override default settings
        outputs['show_ornaments'] = False
        outputs['off_screen'] = offscreen
        outputs['viewer'] = True  # always play video for now

        # override camera options
        outputs['camera_options']['overscan'] = 1.0
        outputs['camera_options']['displayFieldChart'] = False
        outputs['camera_options']['displayFilmGate'] = False
        outputs['camera_options']['displayFilmOrigin'] = False
        outputs['camera_options']['displayFilmPivot'] = False
        outputs['camera_options']['displayGateMask'] = False
        outputs['camera_options']['displayResolution'] = False
        outputs['camera_options']['displaySafeAction'] = False
        outputs['camera_options']['displaySafeTitle'] = False

        # force viewport 2.0 and AA
        if override_viewport_options:
            if high_quality:
                outputs['viewport_options']['rendererName'] = 'vp2Renderer'
            outputs['viewport2_options']['multiSampleEnable'] = True
            outputs['viewport2_options']['multiSampleCount'] = 8

        # Exclude some default things you often don't want to see.
        if self.override_viewport.isChecked:
            for obj in self.show_types_list:
                outputs['viewport_options'][obj.text()] = obj.isChecked()
        else:
            for obj in self.show_types_list:
                outputs['viewport_options'][obj.text()] = True

        return outputs

    def _store_widget_inputs(self):
        self.inputs.update(self.get_show_inputs())

    def closeEvent(self, event):
        self._store_widget_inputs()
        event.accept()


class TimeWidget(OptionsPlugin):
    """Widget for time based options

    This does not emit options changed signals because the time settings does
    not influence the visual representation of the preview snapshot.

    """

    id = "Time Range"
    label = ""
    section = "app"

    RangeTimeSlider = "Time Slider"
    RangeStartEnd = "Start/End"
    CurrentFrame = "CurrentFrame"

    def __init__(self, parent=None):
        super(TimeWidget, self).__init__(parent=parent)

        self._event_callbacks = list()

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.RangeTimeSlider,
                            self.RangeStartEnd,
                            self.CurrentFrame])

        self.start = QtWidgets.QSpinBox()
        self.start.setRange(-sys.maxint, sys.maxint)
        self.end = QtWidgets.QSpinBox()
        self.end.setRange(-sys.maxint, sys.maxint)

        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.start)
        self._layout.addWidget(self.end)

        self.on_mode_changed()  # force enabled state refresh
        self.mode.currentIndexChanged.connect(self.on_mode_changed)

        self._register_callbacks()

    def _register_callbacks(self):
        """
        Register callbacks to ensure Capture GUI reacts to changes in
        the Maya GUI in regards to time slider and current frame
        :return: None
        """
        # this avoid overriding the ids on re-run
        currentframe = om.MEventMessage.addEventCallback("timeChanged",
                                                         lambda
                                                             x: self.on_mode_changed())

        timerange = om.MEventMessage.addEventCallback("playbackRangeChanged",
                                                      lambda
                                                          x: self.on_mode_changed())

        self._event_callbacks.append(currentframe)
        self._event_callbacks.append(timerange)

    def _remove_callbacks(self):
        """Remove callbacks when closing widget"""
        for callback in self._event_callbacks:
            om.MEventMessage.removeCallback(callback)

    def on_mode_changed(self):
        """
        Update the GUI when the user updated the time range or settings
        
        :param currentframe: frame number when time has been changed
        :type currentframe: float
        
        :return: None 
        """

        mode = self.mode.currentText()
        if mode == self.RangeTimeSlider:
            start, end = lib.get_time_slider_range()
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            mode_values = int(start), int(end)

        elif mode == self.RangeStartEnd:
            self.start.setEnabled(True)
            self.end.setEnabled(True)
            mode_values = self.start.value(), self.end.value()
        else:
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            mode_values = "({})".format(int(lib.get_current_frame()))

        # Update label
        self.label = "Time Range {}".format(mode_values)
        self.label_changed.emit(self.label)

    def get_outputs(self, panel=""):
        """
        Get the options of the Time Widget
        :param panel: 
        :return: the settings in a dictionary
        :rtype: dict
        """

        mode = self.mode.currentText()

        if mode == self.RangeTimeSlider:
            start, end = lib.get_time_slider_range()

        elif mode == self.RangeStartEnd:
            start = self.start.value()
            end = self.end.value()

        elif mode == self.CurrentFrame:
            frame = lib.get_current_frame()
            start = frame
            end = frame

        else:
            raise NotImplementedError("Unsupported time range mode: "
                                      "{0}".format(mode))

        return {"start_frame": start,
                "end_frame": end}

    def get_inputs(self):
        return {"time": self.mode.currentText(),
                "start_frame": self.start.value(),
                "end_frame": self.end.value()}

    def apply_inputs(self, settings):
        # get values
        mode = self.mode.findText(settings.get("mode", self.RangeTimeSlider))
        startframe = settings.get("start_frame", 1)
        endframe = settings.get("end_frame", 120)

        # set values
        self.mode.setCurrentIndex(mode)
        self.start.setValue(int(startframe))
        self.end.setValue(int(endframe))

    def closeEvent(self, event):
        self._remove_callbacks()
        event.accept()


class RendererWidget(OptionsPlugin):

    id = "Renderer"
    label = ""
    section = "config"

    def __init__(self, parent=None):
        OptionsPlugin.__init__(self, parent=parent)

        self._layout = QtWidgets.QVBoxLayout()
        self.setLayout(self._layout)

        # Create list of renderers
        self.renderers = QtWidgets.QComboBox()
        self.renderers.addItems(self.get_renderers())
        self.use_isolate_view = QtWidgets.QCheckBox("Use Isolate View")

        self._layout.addWidget(self.renderers)
        self._layout.addWidget(self.use_isolate_view)

    def get_renderers(self):
        active_editor = lib.get_active_editor()
        return cmds.modelEditor(active_editor, query=True, rendererList=True)

    def get_outputs(self):
        """
        Get widget current inputs
        :return: collection if current inputs
        :rtype: dict
        """
        outputs = {}
        if self.use_isolate_view.isChecked:
            panel = lib.get_active_editor()
            filter_set = cmds.modelEditor(panel, query=True, viewObjects=True)
            isolate = cmds.sets(filter_set, query=True) if filter_set else None
            outputs["isolate"] = isolate

        return outputs

    def apply_inputs(self, settings):
        """
        Apply previous settings or settings from a preset
        
        :param settings: collection if inputs
        :type settings: dict
        
        :return: 
        """
        # get values from settings
        isolate = settings.get("isolate", False)
        renderer = settings.get("rendererName", "vp2Renderer")

        # apply settings in widget
        self.renderers.setCurrentIndex(self.renderers.findText(renderer))
        self.use_isolate_view.setChecked(isolate)
