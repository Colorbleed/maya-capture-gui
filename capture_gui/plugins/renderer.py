import maya.cmds as cmds
from capture_gui.vendor.Qt import QtCore, QtWidgets


import capture_gui.lib as lib
import capture_gui.plugin


class RendererWidget(capture_gui.plugin.Plugin):
    id = "Renderer"
    label = "Renderer"
    section = "config"
    order = 60

    def __init__(self, parent=None):
        super(RendererWidget, self).__init__(parent=parent)

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
