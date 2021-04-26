#!/usr/bin/env python3

import sys
from PyQt5 import QtWidgets, QtCore, uic, QtGui
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from scipy.interpolate import interp1d
import xlrd  # reading xls files
import numpy as np
import os
from plot_utilities import *

## Switch to using white background and black foreground
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class ChannelCalibration:
    def __init__(self):
        self.useOhms = True
        self.R_offset = 0.0
        self.R_scale = 1.0
        # Reference points (can recalibrate using only single one)
        self.X1 = None
        self.X2 = None
        self.T1 = None
        self.T2 = None

        curve_raw = np.loadtxt("Pt100_curve.dat", skiprows=1)
        self.TR_curve = interp1d(curve_raw[:, 0], curve_raw[:, 1])
        self.RT_curve = interp1d(curve_raw[:, 1], curve_raw[:, 0])

    def getCurveR(self, T):
        return self.TR_curve(T)

    def getCurveT(self, R):
        return self.RT_curve(R)

    def evaluateR(self, file_value):
        if self.useOhms:
            return (file_value + self.R_offset) * self.R_scale
        R = self.getCurveR(file_value)
        return (R + self.R_offset) * self.R_scale

    def evaluateT(self, file_value):
        return self.getCurveT(self.evaluateR(file_value))

    def __calibrateBy1Point(self, x, T):
        self.R_scale = 1.0
        if self.useOhms:
            self.R_offset = self.getCurveR(T) - x
        else:
            self.R_offset = self.getCurveR(T) - self.getCurveR(x)

    def calibrateByPoints(self):
        if (self.X1 is None or self.T1 is None) and (self.X2 is None or self.T2 is None):
            self.R_offset = 0.0
            self.R_scale = 1.0
            return
        if not(self.X1 is None or self.T1 is None) and not(self.X2 is None or self.T2 is None):
            if (self.X1 == self.X2) or (self.T1 == self.T2):
                self.__calibrateBy1Point(self.X1, self.T1)
                return
            R1 = self.X1
            R2 = self.X2
            if not self.useOhms:
                R1 = self.getCurveR(self.X1)
                R2 = self.getCurveR(self.X2)
            RT1 = self.getCurveR(self.T1)
            RT2 = self.getCurveR(self.T2)
            self.R_scale = (RT1 - RT2) / (R1 - R2)
            self.R_offset = RT1 - self.R_scale * R1  # == RT2 - self.R_scale * R2
            return
        if not(self.X1 is None) and not(self.T1 is None):
            self.__calibrateBy1Point(self.X1, self.T1)
            return
        if not(self.X2 is None) and not(self.T2 is None):
            self.__calibrateBy1Point(self.X2, self.T2)
            return


class CalibrationDialog(QDialog):
    def __init__(self, parent=None):
        super(CalibrationDialog, self).__init__(parent)

        uic.loadUi('calibration.ui', self)
        self.data = [ChannelCalibration(), ChannelCalibration(), ChannelCalibration(), ChannelCalibration()]
        self.temp_data = [ChannelCalibration(), ChannelCalibration(), ChannelCalibration(), ChannelCalibration()]  # Temporary data until Ok is pressed

        self.buttonOhms1.toggled.connect(self.toggled_1_Ohms)
        self.buttonKelvin1.toggled.connect(self.toggled_1_Ohms)
        self.buttonOhms2.toggled.connect(self.toggled_2_Ohms)
        self.buttonKelvin2.toggled.connect(self.toggled_2_Ohms)
        self.buttonOhms3.toggled.connect(self.toggled_3_Ohms)
        self.buttonKelvin3.toggled.connect(self.toggled_3_Ohms)
        self.buttonOhms4.toggled.connect(self.toggled_4_Ohms)
        self.buttonKelvin4.toggled.connect(self.toggled_4_Ohms)

        self.RoffsetEdit1.editingFinished.connect(self.updateR1offset)
        self.RscaleEdit1.editingFinished.connect(self.updateR1scale)
        self.RoffsetEdit2.editingFinished.connect(self.updateR2offset)
        self.RscaleEdit2.editingFinished.connect(self.updateR2scale)
        self.RoffsetEdit3.editingFinished.connect(self.updateR3offset)
        self.RscaleEdit3.editingFinished.connect(self.updateR3scale)
        self.RoffsetEdit4.editingFinished.connect(self.updateR4offset)
        self.RscaleEdit4.editingFinished.connect(self.updateR4scale)

        self.calX1_1.editingFinished.connect(self.updateCalX1_1)
        self.calX2_1.editingFinished.connect(self.updateCalX2_1)
        self.calT1_1.editingFinished.connect(self.updateCalT1_1)
        self.calT2_1.editingFinished.connect(self.updateCalT2_1)
        self.calX1_2.editingFinished.connect(self.updateCalX1_2)
        self.calX2_2.editingFinished.connect(self.updateCalX2_2)
        self.calT1_2.editingFinished.connect(self.updateCalT1_2)
        self.calT2_2.editingFinished.connect(self.updateCalT2_2)
        self.calX1_3.editingFinished.connect(self.updateCalX1_3)
        self.calX2_3.editingFinished.connect(self.updateCalX2_3)
        self.calT1_3.editingFinished.connect(self.updateCalT1_3)
        self.calT2_3.editingFinished.connect(self.updateCalT2_3)
        self.calX1_4.editingFinished.connect(self.updateCalX1_4)
        self.calX2_4.editingFinished.connect(self.updateCalX2_4)
        self.calT1_4.editingFinished.connect(self.updateCalT1_4)
        self.calT2_4.editingFinished.connect(self.updateCalT2_4)

        self.calApply1.clicked.connect(self.applyPoints1)
        self.calApply2.clicked.connect(self.applyPoints2)
        self.calApply3.clicked.connect(self.applyPoints3)
        self.calApply4.clicked.connect(self.applyPoints4)

        self.RoffsetEdit1.setText(str(self.data[0].R_offset))
        self.RscaleEdit1.setText(str(self.data[0].R_scale))
        self.RoffsetEdit2.setText(str(self.data[1].R_offset))
        self.RscaleEdit2.setText(str(self.data[1].R_scale))
        self.RoffsetEdit3.setText(str(self.data[2].R_offset))
        self.RscaleEdit3.setText(str(self.data[2].R_scale))
        self.RoffsetEdit4.setText(str(self.data[3].R_offset))
        self.RscaleEdit4.setText(str(self.data[3].R_scale))

    def applyPoints1(self):
        self.temp_data[0].calibrateByPoints()
        self.RoffsetEdit1.setText(str(self.temp_data[0].R_offset))
        self.RscaleEdit1.setText(str(self.temp_data[0].R_scale))

    def applyPoints2(self):
        self.temp_data[1].calibrateByPoints()
        self.RoffsetEdit2.setText(str(self.temp_data[1].R_offset))
        self.RscaleEdit2.setText(str(self.temp_data[1].R_scale))

    def applyPoints3(self):
        self.temp_data[2].calibrateByPoints()
        self.RoffsetEdit3.setText(str(self.temp_data[2].R_offset))
        self.RscaleEdit3.setText(str(self.temp_data[2].R_scale))

    def applyPoints4(self):
        self.temp_data[3].calibrateByPoints()
        self.RoffsetEdit4.setText(str(self.temp_data[3].R_offset))
        self.RscaleEdit4.setText(str(self.temp_data[3].R_scale))

    def applyCalibration(self, toT, device, vals):
        if device > 3 or device < 0 :
            raise IndexError("Calibration: device index is out of range [0, 3]")
        out_vals = []
        for v in vals:
            if toT:
                out_vals.append(self.data[device].evaluateT(v))
            else:
                out_vals.append(self.data[device].evaluateR(v))
        return out_vals


    def tryTextToFloat(self, text):
        try:
            val = float(text)
            return val
        except ValueError:
            self.statusLine.setText("Input value must be numerical type!")
            return None

    def __update_ref_point(self, index, qEdit, field):
        self.statusLine.setText("")
        text = getattr(self, qEdit).text()
        if "" == text:
            setattr(self.temp_data[index], field, None)
            return
        val = self.tryTextToFloat(text)
        if val is None:
            if getattr(self.temp_data[index], field) is None:
                getattr(self, qEdit).setText("")
            else:
                getattr(self, qEdit).setText(str(getattr(self.temp_data[index], field)))
        else:
            setattr(self.temp_data[index], field, val)

    def updateCalX1_1(self):
        self.__update_ref_point(0, "calX1_1", "X1")  # data index, widget name, data member name

    def updateCalX2_1(self):
        self.__update_ref_point(0, "calX2_1", "X2")  # data index, widget name, data member name

    def updateCalT1_1(self):
        self.__update_ref_point(0, "calT1_1", "T1")  # data index, widget name, data member name

    def updateCalT2_1(self):
        self.__update_ref_point(0, "calT2_1", "T2")  # data index, widget name, data member name

    def updateCalX1_2(self):
        self.__update_ref_point(1, "calX1_2", "X1")  # data index, widget name, data member name

    def updateCalX2_2(self):
        self.__update_ref_point(1, "calX2_2", "X2")  # data index, widget name, data member name

    def updateCalT1_2(self):
        self.__update_ref_point(1, "calT1_2", "T1")  # data index, widget name, data member name

    def updateCalT2_2(self):
        self.__update_ref_point(1, "calT2_2", "T2")  # data index, widget name, data member name

    def updateCalX1_3(self):
        self.__update_ref_point(2, "calX1_3", "X1")  # data index, widget name, data member name

    def updateCalX2_3(self):
        self.__update_ref_point(2, "calX2_3", "X2")  # data index, widget name, data member name

    def updateCalT1_3(self):
        self.__update_ref_point(2, "calT1_3", "T1")  # data index, widget name, data member name

    def updateCalT2_3(self):
        self.__update_ref_point(2, "calT2_3", "T2")  # data index, widget name, data member name

    def updateCalX1_4(self):
        self.__update_ref_point(3, "calX1_4", "X1")  # data index, widget name, data member name

    def updateCalX2_4(self):
        self.__update_ref_point(3, "calX2_4", "X2")  # data index, widget name, data member name

    def updateCalT1_4(self):
        self.__update_ref_point(3, "calT1_4", "T1")  # data index, widget name, data member name

    def updateCalT2_4(self):
        self.__update_ref_point(3, "calT2_4", "T2")  # data index, widget name, data member name

    def __update_cal_pars(self, index, qEdit, field):
        self.statusLine.setText("")
        text = getattr(self, qEdit).text()
        val = self.tryTextToFloat(text)
        if val is None:
            getattr(self, qEdit).setText(str(getattr(self.temp_data[index], field)))
        else:
            setattr(self.temp_data[index], field, val)

    def updateR1offset(self):
        self.__update_cal_pars(0, "RoffsetEdit1", "R_offset")

    def updateR1scale(self):
        self.__update_cal_pars(0, "RscaleEdit1", "R_scale")

    def updateR2offset(self):
        self.__update_cal_pars(1, "RoffsetEdit2", "R_offset")

    def updateR2scale(self):
        self.__update_cal_pars(1, "RscaleEdit2", "R_scale")

    def updateR3offset(self):
        self.__update_cal_pars(2, "RoffsetEdit3", "R_offset")

    def updateR3scale(self):
        self.__update_cal_pars(2, "RscaleEdit3", "R_scale")

    def updateR4offset(self):
        self.__update_cal_pars(3, "RoffsetEdit4", "R_offset")

    def updateR4scale(self):
        self.__update_cal_pars(3, "RscaleEdit4", "R_scale")

    def toggled_1_Ohms(self):
        self.statusLine.setText("")
        self.temp_data[0].useOhms = self.buttonOhms1.isChecked()

    def toggled_1_Kelvin(self):
        self.statusLine.setText("")
        self.temp_data[0].useOhms = self.buttonOhms1.isChecked()

    def toggled_2_Ohms(self):
        self.statusLine.setText("")
        self.temp_data[1].useOhms = self.buttonOhms2.isChecked()

    def toggled_1_Kelvin(self):
        self.statusLine.setText("")
        self.temp_data[1].useOhms = self.buttonOhms2.isChecked()

    def toggled_3_Ohms(self):
        self.statusLine.setText("")
        self.temp_data[2].useOhms = self.buttonOhms3.isChecked()

    def toggled_3_Kelvin(self):
        self.statusLine.setText("")
        self.temp_data[2].useOhms = self.buttonOhms3.isChecked()

    def toggled_4_Ohms(self):
        self.statusLine.setText("")
        self.temp_data[3].useOhms = self.buttonOhms4.isChecked()

    def toggled_4_Kelvin(self):
        self.statusLine.setText("")
        self.temp_data[3].useOhms = self.buttonOhms4.isChecked()

    def accept(self):
        self.data = self.temp_data.copy()
        self.statusLine.setText("")
        super().accept()

    def reject(self):
        self.temp_data = self.data.copy()
        self.statusLine.setText("")
        super().reject()


class FileDialog(QDialog):
    def __init__(self, parent=None):
        super(FileDialog, self).__init__(parent)

        uic.loadUi('file_browser.ui', self)
        self.data1 = {}  # {"filename", ["status", x1s, y1s, x2s, y2s, ..., yns]}
        self.data2 = {}
        self.temp_data1 = {}  # Temporary data until Ok is pressed
        self.temp_data2 = {}
        self.fbOpenBrowser1.clicked.connect(self.select_files1)
        self.fbOpenBrowser2.clicked.connect(self.select_files2)
        self.fbAddFile1.clicked.connect(self.add_files1)
        self.fbAddFile2.clicked.connect(self.add_files2)


    def select_files1(self):
        files = QFileDialog.getOpenFileNames(self, "Select Files",
                                             os.path.dirname(os.path.realpath(__file__)), "Lakeshore Files (*.xls)")
        text = ""
        for fn in files[0]:
            text += fn + ";"
        text = text[:-1]
        if text:
            self.fbLineEdit1.setText(text)

    def select_files2(self):
        files = QFileDialog.getOpenFileNames(self, "Select Files",
                os.path.dirname(os.path.realpath(__file__)), "Pressure Files (*.csv)")
        text = ""
        for fn in files[0]:
            text += fn + ";"
        text = text[:-1]
        if text:
            self.fbLineEdit2.setText(text)

    def parse_lakeshore_file(self, filename):
        try:
            n_sensors = 4
            book = xlrd.open_workbook(filename)
            sh = book.sheet_by_index(0)
            start_time = sh.cell_value(rowx=1, colx=1)  # B2 cell, "Thu Jan 21 14:04:03 NOVT 2021"

            start_time = start_time.split(" ")[3]  # "14:04:03"
            start_time = timestr_to_seconds(start_time)

            if sh.nrows < 5:
                raise IndexError("Empty data")
            xs, ys = [], []
            for s in range(n_sensors):
                xs.append([])
                ys.append([])
            for rx in range(4, sh.nrows):
                x = sh.cell_value(rowx=rx, colx=0)  # in milliseconds
                try:
                    x = float(x)
                except ValueError:
                    continue
                x = start_time + 0.001 * x  # in seconds
                for s in range(n_sensors):
                    y = sh.cell_value(rowx=rx, colx=(1 + s))
                    try:
                        y = float(y)
                    except ValueError:
                        continue
                    xs[s].append(x)
                    ys[s].append(y)
            result = ["Ok"]
            for s in range(n_sensors):
                result.append(np.array(xs[s]))
                result.append(np.array(ys[s]))
            self.fbStatusLine.setText("Loaded '" + filename + "'")
            return result

        except:
            self.fbStatusLine.setText("Error for '" + filename + "'")
            print("Error while opening file '", filename, "':", sys.exc_info()[0])
            return ["Failed"]

    def parse_pressure_file(self, filename):
        line_n = 0
        n_sensors = 4  # In reality there is always only 1 sensor in this file type
        xs, ys = [], []
        for s in range(n_sensors):
            xs.append([])
            ys.append([])
        with open(filename, "r", encoding="iso-8859-1") as file:
            for line in file:
                line_n += 1
                if line_n < 3:  # Header
                    continue
                line = line.replace(",", ".")
                values = line.split(';')
                p, t = 0, 0
                try:
                    p = float(values[0])
                    t = values[2].split(" ")
                    t = timestr_to_seconds(t[1])
                    if t is None:
                        continue
                except ValueError:
                    continue
                xs[0].append(t)
                ys[0].append(p)

        if not xs[0]:
            self.fbStatusLine.setText("Error for '" + filename + "'")
            print("Error while opening file '", filename, "'")
            return ["Failed"]
        result = ["Ok"]
        for s in range(n_sensors):
            result.append(np.array(xs[s]))
            result.append(np.array(ys[s]))
        self.fbStatusLine.setText("Loaded '" + filename + "'")
        return result

    def update_file_list(self):
        """Displays currently loaded files"""
        file_list = []
        for i in self.temp_data1.items():
            if i[1][0] != "Failed":
                if i[0] not in file_list:
                    file_list.append(i[0])
        file_list_text = ""
        for i in file_list:
            file_list_text += i + "\n"
        self.fbFilesList1.setPlainText(file_list_text)

        file_list = []
        for i in self.temp_data2.items():
            if i[1][0] != "Failed":
                if i[0] not in file_list:
                    file_list.append(i[0])
        file_list_text = ""
        for i in file_list:
            file_list_text += i + "\n"
        self.fbFilesList2.setPlainText(file_list_text)

    def add_files1(self):
        text = self.fbLineEdit1.text()
        filenames = text.split(';')
        for fn in filenames:
            self.temp_data1[fn] = self.parse_lakeshore_file(fn)
        self.fbLineEdit1.setText("")
        self.update_file_list()

    def add_files2(self):
        text = self.fbLineEdit2.text()
        filenames = text.split(';')
        for fn in filenames:
            self.temp_data2[fn] = self.parse_pressure_file(fn)
        self.fbLineEdit2.setText("")
        self.update_file_list()

    def accept(self):
        self.data1 = self.temp_data1.copy()
        self.data2 = self.temp_data2.copy()
        self.fbStatusLine.setText("")
        super().accept()

    def reject(self):
        self.temp_data1 = self.data1.copy()
        self.temp_data2 = self.data2.copy()
        self.fbStatusLine.setText("")
        self.update_file_list()
        super().reject()

class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        uic.loadUi('plot_window.ui', self)

        self.plt1 = self.graphW1.getPlotItem()
        axis1 = DateAxisItem(orientation='bottom')
        axis1.attachToPlotItem(self.plt1)
        self.plt1.showGrid(x=True, y=True, alpha=0.3)
        self.plt1.enableAutoRange(x=True, y=True)
        #self.data_item1 = self.plt1.plot(np.random.normal(size=100), pen=(200, 200, 200), symbolBrush=(255, 0, 0), symbolPen='w')

        self.plt2 = self.graphW2.getPlotItem()
        axis2 = DateAxisItem(orientation='bottom')
        axis2.attachToPlotItem(self.plt2)
        self.plt2.showGrid(x=True, y=True, alpha=0.3)
        self.plt2.enableAutoRange(x=True, y=True)
        #self.data_item2 = self.plt2.plot(np.random.normal(size=100), pen=(200, 200, 200), symbolBrush=(255, 0, 0), symbolPen='c')

        self.cursor_v1 = pg.InfiniteLine(angle=90, movable=False, pen=(0, 0, 0))
        self.cursor_h1 = pg.InfiniteLine(angle=0, movable=False, pen=(0, 0, 0))
        self.cursor_v2 = pg.InfiniteLine(angle=90, movable=False, pen=(0, 0, 0))
        self.cursor_h2 = pg.InfiniteLine(angle=0, movable=False, pen=(0, 0, 0))
        self.plt1.addItem(self.cursor_v1, ignoreBounds=True)
        self.plt1.addItem(self.cursor_h1, ignoreBounds=True)
        self.plt2.addItem(self.cursor_v2, ignoreBounds=True)
        self.plt2.addItem(self.cursor_h2, ignoreBounds=True)

        self.plt2.setXLink(self.plt1)

        self.filesButton.clicked.connect(self.open_dialog)
        self.dia = FileDialog(self)
        self.dia.accepted.connect(self.update_graphs)
        self.dia.rejected.connect(self.update_graphs)

        self.calibrationButton.clicked.connect(self.open_calibration_dialog)
        self.calib_dia = CalibrationDialog(self)
        self.calib_dia.accepted.connect(self.update_graphs)
        self.calib_dia.rejected.connect(self.update_graphs)
        self.plotRawCheckbox.stateChanged.connect(self.update_graphs)
        self.plotTCheckbox.stateChanged.connect(self.update_graphs)

        # Regretfully, there is no rangeChanged or similar signal for axes, so use these signals instead
        # to align Y axes of two independent plots. It's still a little buggy.
        # Probably the proper way is subclassing from AxisItem
        self.plt1.getAxis('left').widthChanged.connect(self.align_axes)
        self.plt1.getViewBox().sigYRangeChanged.connect(self.align_axes)
        self.plt2.getAxis('left').widthChanged.connect(self.align_axes)
        self.plt2.getViewBox().sigYRangeChanged.connect(self.align_axes)

        self.plt1.scene().sigMouseMoved.connect(self.mouse_moved_plt1)
        self.plt2.scene().sigMouseMoved.connect(self.mouse_moved_plt2)

    def open_dialog(self):
        self.dia.show()

    def open_calibration_dialog(self):
        self.calib_dia.show()

    def align_axes(self):
        self.plt1.getAxis('left').setWidth()  # Auto width
        self.plt2.getAxis('left').setWidth()  # Auto width
        w1 = self.plt1.getAxis('left').maximumWidth()
        w2 = self.plt2.getAxis('left').maximumWidth()
        w = max(self.plt1.getAxis('left').maximumWidth(), self.plt2.getAxis('left').maximumWidth())
        self.plt1.getAxis('left').setWidth(w)
        self.plt2.getAxis('left').setWidth(w)

    def update_graphs(self):
        color_scheme = [(255, 0, 0), (0, 0, 255), (0, 255, 0), (30, 30, 30)]
        self.plt1.clear()
        for i in self.dia.data1.items():
            ncol = len(i[1])
            if ncol < 3:
                continue
            for col in range((ncol - 1) // 2):
                ts = i[1][col*2 + 1]
                ys = i[1][col*2 + 2]
                if self.plotRawCheckbox.isChecked():
                    self.plt1.plot(ts, ys, pen=color_scheme[col])
                else:
                    ys = self.calib_dia.applyCalibration(self.plotTCheckbox.isChecked(), col, ys)
                    self.plt1.plot(ts, ys, pen=color_scheme[col])

        self.plt2.clear()
        for i in self.dia.data2.items():
            ncol = len(i[1])
            if ncol < 3:
                continue
            for col in range((ncol - 1) // 2):
                self.plt2.plot(i[1][col * 2 + 1], i[1][col * 2 + 2], pen=color_scheme[col])

        self.plt1.addItem(self.cursor_v1, ignoreBounds=True)
        self.plt1.addItem(self.cursor_h1, ignoreBounds=True)
        self.plt2.addItem(self.cursor_v2, ignoreBounds=True)
        self.plt2.addItem(self.cursor_h2, ignoreBounds=True)

    def mouse_moved_plt1(self, coords):
        mouse_point = self.plt1.getViewBox().mapSceneToView(coords)
        ss = second_to_timestr(mouse_point.x(), "{H:02d}:{M:02d}:{s:06.3F}")
        self.statusbar.showMessage("x1=" + ss+", y1=" + '{0:.6g}'.format(mouse_point.y()))
        if self.plt1.sceneBoundingRect().contains(coords):
            self.cursor_v1.setPos(mouse_point.x())
            self.cursor_h1.setPos(mouse_point.y())
            self.cursor_v2.setPos(mouse_point.x())

    def mouse_moved_plt2(self, coords):
        mouse_point = self.plt2.getViewBox().mapSceneToView(coords)
        ss = second_to_timestr(mouse_point.x(), "{H:02d}:{M:02d}:{s:06.3F}")
        self.statusbar.showMessage("x2=" + ss + ", y2=" + '{0:.6g}'.format(mouse_point.y()))
        if self.plt2.sceneBoundingRect().contains(coords):
            self.cursor_v2.setPos(mouse_point.x())
            self.cursor_h2.setPos(mouse_point.y())
            self.cursor_v1.setPos(mouse_point.x())


if __name__ == '__main__':
    from sys import argv, exit

    app = QApplication(argv)
    win = MyWindow()
    win.show()
    exit(app.exec_())
