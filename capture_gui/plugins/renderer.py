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

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create list of renderers
        self.renderers = QtWidgets.QComboBox()
        self.renderers.addItems(self.get_renderers())

        layout.addWidget(self.renderers)

    def get_renderers(self):
        active_editor = lib.get_active_editor()
        return cmds.modelEditor(active_editor, query=True, rendererList=True)

    def get_inputs(self):

        return {
            "rendererName": self.renderers.currentText()
        }

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments
        
        Returns:
            dict: Plugin outputs
            
        """
        return {
            "viewport_options": {
                "rendererName": self.renderers.currentText()
            }
        }

    def apply_inputs(self, inputs):
        """
        Apply previous settings or settings from a preset

        Args:
            inputs (dict): Plugin input settings

        Returns:
            None
            
        """
        renderer = inputs.get("renderer", "vp2Renderer")
        index = self.renderers.findText(renderer)
        self.renderers.setCurrentIndex(index)
