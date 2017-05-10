from capture_gui.vendor.Qt import QtCore, QtWidgets


class ColorPicker(QtWidgets.QPushButton):
    """Custom color pick button to store and retrieve color values"""

    def __init__(self):
        QtWidgets.QPushButton.__init__(self)

        self.clicked.connect(self.get_color_value)
        self._color = None

        self.color = [255, 255, 255]

    # region properties
    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, values):
        """Set the color value and update the stylesheet
        
        :param values: the color values; red, green, blue
        :type values: list
        
        :return: None
        """
        self._color = values
        self.setStyleSheet("background: rgb({},{},{})".format(*values))

    # endregion properties

    def get_color_value(self):
        """Get the RGB values from the selected color
        
        :return: the red, green and blue values
        :rtype: list
        """
        colors = QtWidgets.QColorDialog.getColor()
        if not colors:
            return
        self.color = [colors.red(), colors.green(), colors.blue()]