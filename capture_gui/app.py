# TODO : Add trigger for widgets when accordion is unfolded

import logging
import os
import tempfile
import capture

from .vendor.Qt import QtCore, QtWidgets, QtGui

import maya.cmds as cmds
from . import lib
from . import widgets

log = logging.getLogger(__name__)


# Modification of Blur's Accordion Widget to include a Maya style.
# Also got rid of the need for a pixmap and used QPolygon instead.

class AccordionItem(QtGui.QGroupBox):
    trigger = QtCore.Signal(bool)

    def __init__(self, accordion, title, widget):
        QtGui.QGroupBox.__init__(self, accordion)

        # create the layout
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(6, 12, 6, 6)
        layout.setSpacing(0)
        layout.addWidget(widget)

        self._accordianWidget = accordion
        self._rolloutStyle = 2
        self._dragDropMode = 0

        self.setAcceptDrops(True)
        self.setLayout(layout)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

        # create custom properties
        self._widget = widget
        self._collapsed = False
        self._collapsible = True
        self._clicked = False
        self._customData = {}

        # set common properties
        self.setTitle(title)

    def accordionWidget(self):
        """
            \remarks	grabs the parent item for the accordian widget
            \return		<blurdev.gui.widgets.accordianwidget.AccordianWidget>
        """
        return self._accordianWidget

    def customData(self, key, default=None):
        """
            \remarks	return a custom pointer to information stored with this item
            \param		key			<str>
            \param		default		<variant>	default value to return if the key was not found
            \return		<variant> data
        """
        return self._customData.get(str(key), default)

    def dragEnterEvent(self, event):
        if not self._dragDropMode:
            return

        source = event.source()
        if source != self and source.parent() == self.parent() and isinstance(
                source, AccordionItem):
            event.acceptProposedAction()

    def dragDropRect(self):
        return QtCore.QRect(25, 7, 10, 6)

    def dragDropMode(self):
        return self._dragDropMode

    def dragMoveEvent(self, event):
        if not self._dragDropMode:
            return

        source = event.source()
        if source != self and source.parent() == self.parent() and isinstance(
                source, AccordionItem):
            event.acceptProposedAction()

    def dropEvent(self, event):
        widget = event.source()
        layout = self.parent().layout()
        layout.insertWidget(layout.indexOf(self), widget)
        self._accordianWidget.emitItemsReordered()

    def expandCollapseRect(self):
        return QtCore.QRect(0, 0, self.width(), 20)

    def enterEvent(self, event):
        self.accordionWidget().leaveEvent(event)
        event.accept()

    def leaveEvent(self, event):
        self.accordionWidget().enterEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._clicked and self.expandCollapseRect().contains(event.pos()):
            self.toggleCollapsed()
            event.accept()
        else:
            event.ignore()

        self._clicked = False

    def mouseMoveEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        # handle an internal move

        # start a drag event
        if event.button() == QtCore.Qt.LeftButton and self.dragDropRect().contains(
                event.pos()):
            # create the pixmap
            pixmap = QtGui.QPixmap.grabWidget(self, self.rect())

            # create the mimedata
            mimeData = QtCore.QMimeData()
            mimeData.setText('ItemTitle::%s' % (self.title()))

            # create the drag
            drag = QtGui.QDrag(self)
            drag.setMimeData(mimeData)
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())

            if not drag.exec_():
                self._accordianWidget.emitItemDragFailed(self)

            event.accept()

        # determine if the expand/collapse should occur
        elif event.button() == QtCore.Qt.LeftButton and self.expandCollapseRect().contains(
                event.pos()):
            self._clicked = True
            event.accept()

        else:
            event.ignore()

    def isCollapsed(self):
        return self._collapsed

    def isCollapsible(self):
        return self._collapsible

    def __drawTriangle(self, painter, x, y):

        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 160),
                             QtCore.Qt.SolidPattern)
        if not self.isCollapsed():
            tl, tr, tp = QtCore.QPoint(x + 9, y + 8), QtCore.QPoint(x + 19,
                                                                    y + 8), QtCore.QPoint(
                x + 14, y + 13.0)
            points = [tl, tr, tp]
            triangle = QtGui.QPolygon(points)
        else:
            tl, tr, tp = QtCore.QPoint(x + 11, y + 6), QtCore.QPoint(x + 16,
                                                                     y + 11), QtCore.QPoint(
                x + 11, y + 16.0)
            points = [tl, tr, tp]
            triangle = QtGui.QPolygon(points)

        currentBrush = painter.brush()
        painter.setBrush(brush)
        painter.drawPolygon(triangle)
        painter.setBrush(currentBrush)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(painter.Antialiasing)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)

        x = self.rect().x()
        y = self.rect().y()
        w = self.rect().width() - 1
        h = self.rect().height() - 1
        r = 8

        # draw a rounded style
        if self._rolloutStyle == 2:
            # draw the text
            painter.drawText(x + 33, y + 3, w, 16,
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop,
                             self.title())

            # draw the triangle
            self.__drawTriangle(painter, x, y)

            # draw the borders
            pen = QtGui.QPen(self.palette().color(QtGui.QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)

            painter.drawRoundedRect(x + 1, y + 1, w - 1, h - 1, r, r)

            pen.setColor(self.palette().color(QtGui.QPalette.Shadow))
            painter.setPen(pen)

            painter.drawRoundedRect(x, y, w - 1, h - 1, r, r)

        # draw a square style
        if self._rolloutStyle == 3:
            # draw the text
            painter.drawText(x + 33, y + 3, w, 16,
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop,
                             self.title())

            self.__drawTriangle(painter, x, y)

            # draw the borders
            pen = QtGui.QPen(self.palette().color(QtGui.QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)

            painter.drawRect(x + 1, y + 1, w - 1, h - 1)

            pen.setColor(self.palette().color(QtGui.QPalette.Shadow))
            painter.setPen(pen)

            painter.drawRect(x, y, w - 1, h - 1)

        # draw a Maya style
        if self._rolloutStyle == 4:
            # draw the text
            painter.drawText(x + 33, y + 3, w, 16,
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop,
                             self.title())

            painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

            self.__drawTriangle(painter, x, y)

            # draw the borders - top
            headerHeight = 20

            headerRect = QtCore.QRect(x + 1, y + 1, w - 1, headerHeight)
            headerRectShadow = QtCore.QRect(x - 1, y - 1, w + 1,
                                            headerHeight + 2)

            # Highlight
            pen = QtGui.QPen(self.palette().color(QtGui.QPalette.Light))
            pen.setWidthF(0.4)
            painter.setPen(pen)

            painter.drawRect(headerRect)
            painter.fillRect(headerRect, QtGui.QColor(255, 255, 255, 18))

            # Shadow
            pen.setColor(self.palette().color(QtGui.QPalette.Dark))
            painter.setPen(pen)
            painter.drawRect(headerRectShadow)

            if not self.isCollapsed():
                # draw the lover border
                pen = QtGui.QPen(self.palette().color(QtGui.QPalette.Dark))
                pen.setWidthF(0.8)
                painter.setPen(pen)

                offSet = headerHeight + 3
                bodyRect = QtCore.QRect(x, y + offSet, w, h - offSet)
                bodyRectShadow = QtCore.QRect(x + 1, y + offSet, w + 1,
                                              h - offSet + 1)
                painter.drawRect(bodyRect)

                pen.setColor(self.palette().color(QtGui.QPalette.Light))
                pen.setWidthF(0.4)
                painter.setPen(pen)

                painter.drawRect(bodyRectShadow)

        # draw a boxed style
        elif self._rolloutStyle == 1:
            if self.isCollapsed():
                arect = QtCore.QRect(x + 1, y + 9, w - 1, 4)
                brect = QtCore.QRect(x, y + 8, w - 1, 4)
                text = '+'
            else:
                arect = QtCore.QRect(x + 1, y + 9, w - 1, h - 9)
                brect = QtCore.QRect(x, y + 8, w - 1, h - 9)
                text = '-'

            # draw the borders
            pen = QtGui.QPen(self.palette().color(QtGui.QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)

            painter.drawRect(arect)

            pen.setColor(self.palette().color(QtGui.QPalette.Shadow))
            painter.setPen(pen)

            painter.drawRect(brect)

            painter.setRenderHint(painter.Antialiasing, False)
            painter.setBrush(
                self.palette().color(QtGui.QPalette.Window).darker(120))
            painter.drawRect(x + 10, y + 1, w - 20, 16)
            painter.drawText(x + 16, y + 1,
                             w - 32, 16,
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                             text)
            painter.drawText(x + 10, y + 1,
                             w - 20, 16,
                             QtCore.Qt.AlignCenter,
                             self.title())

        if self.dragDropMode():
            rect = self.dragDropRect()

            # draw the lines
            l = rect.left()
            r = rect.right()
            cy = rect.center().y()

            for y in (cy - 3, cy, cy + 3):
                painter.drawLine(l, y, r, y)

        painter.end()

    def setCollapsed(self, state=True):
        if self.isCollapsible():
            accord = self.accordionWidget()
            accord.setUpdatesEnabled(False)

            self._collapsed = state

            if state:
                self.setMinimumHeight(22)
                self.setMaximumHeight(22)
                self.widget().setVisible(False)
            else:
                self.setMinimumHeight(0)
                self.setMaximumHeight(1000000)
                self.widget().setVisible(True)

            self._accordianWidget.emitItemCollapsed(self)
            accord.setUpdatesEnabled(True)

    def setCollapsible(self, state=True):
        self._collapsible = state

    def setCustomData(self, key, value):
        """
            \remarks	set a custom pointer to information stored on this item
            \param		key		<str>
            \param		value	<variant>
        """
        self._customData[str(key)] = value

    def setDragDropMode(self, mode):
        self._dragDropMode = mode

    def setRolloutStyle(self, style):
        self._rolloutStyle = style

    def showMenu(self):
        if QtCore.QRect(0, 0, self.width(), 20).contains(
                self.mapFromGlobal(QtGui.QCursor.pos())):
            self._accordianWidget.emitItemMenuRequested(self)

    def rolloutStyle(self):
        return self._rolloutStyle

    def toggleCollapsed(self):
        # enable signaling here
        collapse_state = not self.isCollapsed()
        self.setCollapsed(collapse_state)
        return collapse_state

    def widget(self):
        return self._widget


class AccordionWidget(QtGui.QScrollArea):
    itemCollapsed = QtCore.Signal(AccordionItem)
    itemMenuRequested = QtCore.Signal(AccordionItem)
    itemDragFailed = QtCore.Signal(AccordionItem)
    itemsReordered = QtCore.Signal()

    Boxed = 1
    Rounded = 2
    Square = 3
    Maya = 4

    NoDragDrop = 0
    InternalMove = 1

    def __init__(self, parent):

        QtGui.QScrollArea.__init__(self, parent)

        self.setFrameShape(QtGui.QScrollArea.NoFrame)
        self.setAutoFillBackground(False)
        self.setWidgetResizable(True)
        self.setMouseTracking(True)
        # self.verticalScrollBar().setMaximumWidth(10)

        widget = QtGui.QWidget(self)

        # define custom properties
        self._rolloutStyle = AccordionWidget.Rounded
        self._dragDropMode = AccordionWidget.NoDragDrop
        self._scrolling = False
        self._scrollInitY = 0
        self._scrollInitVal = 0
        self._itemClass = AccordionItem

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 6)
        layout.setSpacing(2)
        layout.addStretch(1)

        widget.setLayout(layout)

        self.setWidget(widget)

    def setSpacing(self, spaceInt):
        self.widget().layout().setSpacing(spaceInt)

    def addItem(self, title, widget, collapsed=False):
        self.setUpdatesEnabled(False)
        item = self._itemClass(self, title, widget)
        item.setRolloutStyle(self.rolloutStyle())
        item.setDragDropMode(self.dragDropMode())
        layout = self.widget().layout()
        layout.insertWidget(layout.count() - 1, item)
        layout.setStretchFactor(item, 0)

        if collapsed:
            item.setCollapsed(collapsed)

        self.setUpdatesEnabled(True)
        return item

    def clear(self):
        self.setUpdatesEnabled(False)
        layout = self.widget().layout()
        while layout.count() > 1:
            item = layout.itemAt(0)

            # remove the item from the layout
            w = item.widget()
            layout.removeItem(item)

            # close the widget and delete it
            w.close()
            w.deleteLater()

        self.setUpdatesEnabled(True)

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.mousePressEvent(event)
            return True

        elif event.type() == QtCore.QEvent.MouseMove:
            self.mouseMoveEvent(event)
            return True

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            self.mouseReleaseEvent(event)
            return True

        return False

    def canScroll(self):
        return self.verticalScrollBar().maximum() > 0

    def count(self):
        return self.widget().layout().count() - 1

    def dragDropMode(self):
        return self._dragDropMode

    def indexOf(self, widget):
        """
            \remarks	Searches for widget(not including child layouts).
                        Returns the index of widget, or -1 if widget is not found
            \return		<int>
        """
        layout = self.widget().layout()
        for index in range(layout.count()):
            if layout.itemAt(index).widget().widget() == widget:
                return index
        return -1

    def isBoxedMode(self):
        return self._rolloutStyle == AccordionWidget.Maya

    def itemClass(self):
        return self._itemClass

    def itemAt(self, index):
        layout = self.widget().layout()
        if 0 <= index and index < layout.count() - 1:
            return layout.itemAt(index).widget()
        return None

    def emitItemCollapsed(self, item):
        if not self.signalsBlocked():
            self.itemCollapsed.emit(item)

    def emitItemDragFailed(self, item):
        if not self.signalsBlocked():
            self.itemDragFailed.emit(item)

    def emitItemMenuRequested(self, item):
        if not self.signalsBlocked():
            self.itemMenuRequested.emit(item)

    def emitItemsReordered(self):
        if not self.signalsBlocked():
            self.itemsReordered.emit()

    def enterEvent(self, event):
        if self.canScroll():
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)

    def leaveEvent(self, event):
        if self.canScroll():
            QtGui.QApplication.restoreOverrideCursor()

    def mouseMoveEvent(self, event):
        if self._scrolling:
            sbar = self.verticalScrollBar()
            smax = sbar.maximum()

            # calculate the distance moved for the moust point
            dy = event.globalY() - self._scrollInitY

            # calculate the percentage that is of the scroll bar
            dval = smax * (dy / float(sbar.height()))

            # calculate the new value
            sbar.setValue(self._scrollInitVal - dval)

        event.accept()

    def mousePressEvent(self, event):
        # handle a scroll event
        if event.button() == QtCore.Qt.LeftButton and self.canScroll():
            self._scrolling = True
            self._scrollInitY = event.globalY()
            self._scrollInitVal = self.verticalScrollBar().value()

            QtGui.QApplication.setOverrideCursor(QtCore.Qt.ClosedHandCursor)

        event.accept()

    def mouseReleaseEvent(self, event):
        if self._scrolling:
            QtGui.QApplication.restoreOverrideCursor()

        self._scrolling = False
        self._scrollInitY = 0
        self._scrollInitVal = 0
        event.accept()

    def moveItemDown(self, index):
        layout = self.widget().layout()
        if (layout.count() - 1) > (index + 1):
            widget = layout.takeAt(index).widget()
            layout.insertWidget(index + 1, widget)

    def moveItemUp(self, index):
        if index > 0:
            layout = self.widget().layout()
            widget = layout.takeAt(index).widget()
            layout.insertWidget(index - 1, widget)

    def setBoxedMode(self, state):
        if state:
            self._rolloutStyle = AccordionWidget.Boxed
        else:
            self._rolloutStyle = AccordionWidget.Rounded

    def setDragDropMode(self, dragDropMode):
        self._dragDropMode = dragDropMode

        for item in self.findChildren(AccordionItem):
            item.setDragDropMode(self._dragDropMode)

    def setItemClass(self, itemClass):
        self._itemClass = itemClass

    def setRolloutStyle(self, rolloutStyle):
        self._rolloutStyle = rolloutStyle

        for item in self.findChildren(AccordionItem):
            item.setRolloutStyle(self._rolloutStyle)

    def rolloutStyle(self):
        return self._rolloutStyle

    def takeAt(self, index):
        self.setUpdatesEnabled(False)
        layout = self.widget().layout()
        widget = None
        if 0 <= index and index < layout.count() - 1:
            item = layout.itemAt(index)
            widget = item.widget()

            layout.removeItem(item)
            widget.close()
        self.setUpdatesEnabled(True)
        return widget

    def widgetAt(self, index):
        item = self.itemAt(index)
        if item:
            return item.widget()
        return None

    pyBoxedMode = QtCore.Property('bool', isBoxedMode, setBoxedMode)


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
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Add attributes
        self.options_getter = options_getter
        self.preview = ClickLabel()

        # region Build
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)
        self.layout.addWidget(self.preview)
        # endregion Build

        # Connect widgets to functions
        self.preview.clicked.connect(self.refresh)

        self.refresh()

    def refresh(self):
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


class App(QtWidgets.QWidget):

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

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Add accordion widget (Maya attribute editor style)
        self.widgetlibrary = AccordionWidget(self)
        self.widgetlibrary.setRolloutStyle(AccordionWidget.Maya)

        # Add widgets
        self.widgetlibrary.addItem("Preview",
                                   PreviewWidget(self.get_options),
                                   collapsed=True)

        for widget in [widgets.PresetWidget, widgets.TimeWidget,
                       widgets.CameraWidget, widgets.ScaleWidget]:
            self.add_options_widget(widget)

        self.layout.addWidget(self.widgetlibrary)

        self.apply_button = QtWidgets.QPushButton("Capture")
        self.close_apply_button = QtWidgets.QPushButton("Capture And Close")

        # add standard buttons
        self.default_buttons = QtWidgets.QHBoxLayout()
        self.default_buttons.setContentsMargins(5, 5, 5, 5)
        self.default_buttons.addWidget(self.apply_button)
        self.default_buttons.addWidget(self.close_apply_button)

        self.layout.addLayout(self.default_buttons)

    def add_options_widget(self, plugin):
        """Add and options widget plug-in to the App"""
        widget = plugin()
        if not widget.hidden:
            self.widgetlibrary.addItem(plugin.label, widget)
        widget.options_changed.connect(self.on_widget_settings_changed)
        self.option_widgets.append(widget)

    def get_options(self):
        """
        Collect all options set of all the widgets listed in the in the
        option_widgets attribute of the main app

        :return: a collection of settings
        :rtype: dict
        """

        # panel = lib.get_active_editor()

        # Get settings from widgets
        options = dict()
        for widget in self.option_widgets:
            options.update(widget.get_options())

        return options

    def on_widget_settings_changed(self):
        options = self.get_options()
        self.options_changed.emit(options)
