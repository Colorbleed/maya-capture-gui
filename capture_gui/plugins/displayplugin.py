from capture_gui.vendor.Qt import QtCore, QtWidgets
import capture_gui.plugin
import capture_gui.colorpicker as colorpicker


# region GLOBALS

BACKGROUND_DEFAULT = [0.6309999823570251,
                      0.6309999823570251,
                      0.6309999823570251]

TOP_DEFAULT = [0.5350000262260437,
               0.6169999837875366,
               0.7020000219345093]

BOTTOM_DEFAULT = [0.052000001072883606,
                  0.052000001072883606,
                  0.052000001072883606]

COLORS = {"background": BACKGROUND_DEFAULT,
          "backgroundTop": TOP_DEFAULT,
          "backgroundBottom": BOTTOM_DEFAULT}

LABELS = {"background": "Background",
          "backgroundTop": "Top",
          "backgroundBottom": "Bottom"}
# endregion GLOBALS


class DisplayPlugin(capture_gui.plugin.Plugin):

    """Plugin to apply viewport visibilities and settings"""

    id = "Display Options"
    label = "Display Options"
    section = "config"
    order = 70

    def __init__(self, parent=None):
        super(DisplayPlugin, self).__init__(parent=parent)

        # The color widgets per key
        self._colors = dict()

        self._layout = QtWidgets.QHBoxLayout()
        self.setLayout(self._layout)

        for label, default in COLORS.items():
            self.add_color_picker(label, default)

    def add_color_picker(self, label, default):
        """Create a column with a label and a button to select a color
        
        :param label: the system name for the color type, e.g. : backgroundTop
        :type label: str
        
        :param default: the default color combination to start with
        :type default: list
        
        :return: a color picker instance
        :rtype: colorpicker.ColorPicker
        """

        column = QtWidgets.QVBoxLayout()
        label_widget = QtWidgets.QLabel(LABELS[label])

        color_picker = colorpicker.ColorPicker()
        color_picker.color = default

        column.addWidget(label_widget)
        column.addWidget(color_picker)

        column.setAlignment(label_widget, QtCore.Qt.AlignCenter)

        self._layout.addLayout(column)
        self._colors[label] = color_picker

        return color_picker

    def apply_inputs(self, settings):
        """
        Apply the saved inputs from the inputs configuration
        :param settings: collection of input settings
        :type settings: dict
        
        :return: None 
        """

        for label, widget in self._colors.items():
            default = COLORS.get(label, [0, 0, 0]) # fallback default to black
            value = settings.get(label, default)
            widget.color = value

    def get_inputs(self, as_preset):
        return {label: widget.color for label, widget in self._colors.items()}

    def get_outputs(self):
        return self.get_inputs(False)
