from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture_gui.plugin

OBJECT_TYPES = ['cameras',
                'dimensions',
                'grid',
                'follicles',
                'ikHandles',
                'joints',
                'locators',
                'lights',
                'manipulators',
                'nCloths',
                'nParticles',
                'nRigids',
                'nurbsCurves',
                'nurbsSurfaces'
                'pivots',
                'planes',
                'polyMeshes',
                'headsUpDisplay',
                'strokes',
                'subdivSurfaces']


class ViewportPlugin(capture_gui.plugin.Plugin):
    """Plugin to apply viewport visibilities and settings"""
    id = "Viewport Options"
    label = "Viewport Options"
    section = "config"
    order = 70

    def __init__(self, parent=None):
        super(ViewportPlugin, self).__init__(parent=parent)

        self.show_types_list = list()

        self.setObjectName(self.label)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        self.override_viewport = QtWidgets.QCheckBox("Override viewport "
                                                     "settings")
        self.override_viewport.setChecked(True)

        # region Show
        self.show_types_button = QtWidgets.QPushButton("Show")
        self.show_types_button.setFixedWidth(150)
        self.show_types_menu = self._build_show_menu()
        self.show_types_button.setMenu(self.show_types_menu)

        # endregion Show

        # region Checkboxes
        self.high_quality = QtWidgets.QCheckBox()
        self.high_quality.setText("Force Viewport 2.0 + AA")
        # endregion Checkboxes

        self._layout.addWidget(self.override_viewport)
        self._layout.addWidget(self.show_types_button)
        self._layout.addWidget(self.high_quality)

        # signals
        self.high_quality.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.on_toggle_override)

    def _build_show_menu(self):
        """Build the menu to select which object types are shown in the output.
        
        Returns:
            QtGui.QMenu: The visibilities "show" menu.
            
        """

        menu = QtWidgets.QMenu(self)
        menu.setWindowTitle("Show")
        menu.setFixedWidth(150)
        menu.setTearOffEnabled(True)

        # Show all check
        toggle_all = QtWidgets.QAction(menu, text="All")
        toggle_none = QtWidgets.QAction(menu, text="None")
        menu.addAction(toggle_all)
        menu.addAction(toggle_none)
        menu.addSeparator()

        for obj_type in OBJECT_TYPES:
            action = QtWidgets.QAction(menu, text=obj_type)
            action.setCheckable(True)

            # Add to menu and list of instances
            menu.addAction(action)
            self.show_types_list.append(action)

        # connect signals
        toggle_all.triggered.connect(self.toggle_all_visbile)
        toggle_none.triggered.connect(self.toggle_all_hide)

        return menu

    def on_toggle_override(self):
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
                  "override_viewport_options": self.override_viewport.isChecked()}

        inputs.update(self.get_show_inputs())

        return inputs

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

        self.high_quality.setChecked(high_quality)
        self.override_viewport.setChecked(override_viewport)
        self.show_types_button.setEnabled(override_viewport)

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

        outputs['viewport_options'] = dict()
        outputs['viewport2_options'] = dict()

        if override_viewport_options and high_quality:
            # force viewport 2.0 and AA
            outputs['viewport_options']['rendererName'] = 'vp2Renderer'
            outputs['viewport2_options']['multiSampleEnable'] = True
            outputs['viewport2_options']['multiSampleCount'] = 8

        # Viewport visibility settings
        if override_viewport_options:
            show_per_type = self.get_show_inputs()
            outputs['viewport_options'].update(show_per_type)
        else:
            for obj in self.show_types_list:
                outputs['viewport_options'][obj.text()] = True

        return outputs
