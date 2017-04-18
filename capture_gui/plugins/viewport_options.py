from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture
import capture_gui.lib as lib
import capture_gui.plugin

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


class ViewportOptionWidget(capture_gui.plugin.Plugin):
    """Widget for additional options

    For now used to set some default values used internally at Colorbleed.

    """
    id = "Viewport Options"
    label = "Viewport Options"
    section = "config"
    order = 70

    show_types_list = []

    def __init__(self, parent=None):
        super(ViewportOptionWidget, self).__init__(parent=parent)

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

