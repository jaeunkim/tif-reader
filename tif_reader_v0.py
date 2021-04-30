# -*- coding: utf-8 -*-
"""
Created on Tue Apr 27 17:14:57 2021

@author: QCP75
"""
import os, socket, threading, random
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PIL import Image, ImageSequence
from glob import glob
import time

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)
uifile = dirname + '/tif_reader_v0.ui'
Ui_Form, QtBaseClass = uic.loadUiType(uifile)


class TifReader(QtWidgets.QWidget, Ui_Form):
    files_to_load = pyqtSignal(list)
    
    def __init__(self, window_title="", parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.setWindowTitle(window_title)
        
        # Plot
        self.toolbar, self.ax, self.canvas = self.create_canvas(self.image_viewer)
        
        # Currently available files table
        self.curr_files_table.setColumnCount(2)
        column_headers = ["file path", "shape"]
        self.curr_files_table.setHorizontalHeaderLabels(column_headers)
        
        # Connect sockets and signals
        self.load_file_btn.clicked.connect(self.load_file)
        self.load_dir_btn.clicked.connect(self.load_dir)
        self.save_btn.clicked.connect(self.save_file)
        self.clear_data_btn.clicked.connect(self.clear_data)
        self.cancel_loading_btn.clicked.connect(self.cancel_loading)
        
        # Internal 
        self.data_as_np = None
        self.curr_dir = ""
        self.curr_files = []
        self.curr_idx = 0
        self.start_idx = 0
        self.end_idx = -1
        self.step_size = 1
        self.num_loaded_files = 0
        self.num_files_to_load = 0
        
        # Setup: loader thread
        self.loader_thread = LoaderThread()
        self.files_to_load.connect(self.loader_thread.update_work_list)
        self.loader_thread.loaded_file_contents.connect(self.update_data)
        self.loader_thread.finished.connect(self.done_loading)
        self.loader_thread.running_flag = False
    
    def clear_data(self):
        #TODO check if this actually releases memory
        self.loader_thread.running_flag = False
        self.loader_thread.work_list = []
        self.data_as_np = None
        self.curr_files = []
        self.num_loaded_files = 0
        #TODO clear file list label
        
    def cancel_loading(self):
        self.loader_thread.running_flag = False
        
    def enable_viewers(self, flag):
        #TODO iterate with getattr
        self.image_viewer.setEnabled(flag)
        self.index_navigator.setEnabled(flag)
        self.curr_dir_label.setEnabled(flag)
        self.flip_horizontally_cbox.setEnabled(flag)
        self.flip_vertically_cbox.setEnabled(flag)
        self.load_dir_btn.setEnabled(flag)
        self.load_file_btn.setEnabled(flag)
        self.clear_data_btn.setEnabled(flag)
        self.save_btn.setEnabled(flag)
    
        # "cancel loading" button behaves differently
        self.cancel_loading_btn.setEnabled(not flag)
    
    def done_loading(self):
        self.loader_thread.running_flag = False
        self.enable_viewers(True)
        self.show_img()
        self.num_loaded_files = 0
        self.num_files_to_load = 0
        
        if not len(self.loader_thread.work_list):
            self.log_label.setText("Finished Loading")
        else:
            self.log_label.setText("Aborted Loading")
        
        self.start_idx = 0
        self.step_size = 1
        self.end_idx = np.shape(self.data_as_np)[0] - 1
        self.reflect_new_idx_range()
        
    def reflect_new_idx_range(self):
        self.start_idx_ledit.setText(str(self.start_idx))
        self.step_size_ledit.setText(str(self.step_size))
        self.end_idx_ledit.setText(str(self.end_idx))
        self.idx_scroll.setRange(self.start_idx, self.end_idx)
        self.idx_scroll.setSingleStep(self.step_size)
        self.curr_idx_label.setText(str(self.curr_idx))
        
    def show_img(self):
        img = self.data_as_np[self.curr_idx]
        
        if self.flip_horizontally_cbox.isChecked():
            img = np.flip(img, 1)
        if self.flip_vertically_cbox.isChecked():
            img = np.flip(img, 0)
        
        #TODO let user choose vmin and vmax (where?)
        #self.ax.imshow(img, vmin=self.vmin, vmax=self.vmax)
        self.ax.imshow(img)
        self.canvas.draw()

    def load_file(self):
        # dialog to choose a file
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_to_load, _ = QFileDialog.getOpenFileName(self,"load a .tif file", "",".tif Files(*.tif)", options=options)
        if not file_to_load:
            return  # user pressed "cancel"
        print("GUI, file_to_load: ", file_to_load)
        
        # update info
        self.curr_dir = os.path.dirname(file_to_load)
        self.curr_dir_label.setText(self.curr_dir)
        
        # initiate loading
        self.enable_viewers(False)
        if not self.loader_thread.running_flag:
            self.loader_thread.running_flag = True
            self.loader_thread.start()
        self.log_label.append("Loading...")
        self.files_to_load.emit([file_to_load])
        
    def load_dir(self):
        # dialog to choose a directory
        dir_to_load = QFileDialog.getExistingDirectory(self,"load a directory",
                                                     "", QFileDialog.ShowDirsOnly)
        if not dir_to_load:
            return  # user pressed "cancel"
        print(dir_to_load)
        
        # return if this dir does not contain .tif files
        tif_files = glob(dir_to_load + "/" + "*.tif")
        print(tif_files)
        if not tif_files:
            error_dialog = QErrorMessage()
            error_dialog.showMessage('this directory does not contain .tif files')
            return
        
        # update info
        self.curr_dir = dir_to_load
        self.curr_dir_label.setText(self.curr_dir)
        
        # initiate loading
        self.enable_viewers(False)
        if not self.loader_thread.running_flag:
            self.loader_thread.running_flag = True
            self.loader_thread.start()
        self.log_label.append("Loading...")
        self.files_to_load.emit(tif_files)
        self.num_files_to_load = len(tif_files)
            
    def save_file(self):
        # dialog to choose a save location
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        save_path, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","Pickle Files(*.pkl)", options=options)
        if not save_path:
            error_dialog = QErrorMessage()
            error_dialog.showMessage('cannot save here')
            return
        
        # trim data and save
        print("saving at: ", fileName)
        trimmed_data = self.data_as_np[self.start_idx: self.end_idx+1: self.step_size]
        save_dict = {}
        save_dict["original path & shape"] = self.curr_files
        save_dict["data"] = trimmed_data
        with open(filename, 'wb') as wf:
            pkl.dump(save_dict, wf)
        
    def create_canvas(self, frame):
        fig = plt.Figure(tight_layout=True)
        ax = fig.add_subplot(1,1,1)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        frame.setLayout(layout)
        
        return toolbar, ax, canvas
    
    def update_data(self, loaded_file_name, loaded_file_contents):
        # TODO trim loaded_file_contents
        try:
            self.data_as_np = np.append(self.data_as_np, loaded_file_contents, axis=0)
            print("shape of data (try block): ", np.shape(self.data_as_np))
        except:
            self.data_as_np = loaded_file_contents
            print("shape of data (except block): ", np.shape(self.data_as_np))
        
        # show loading progress
        self.num_loaded_files = self.num_loaded_files + 1
        self.log_label.append("Loaded file: %d/%d\n" % 
                             (self.num_loaded_files, self.num_files_to_load))
        
        # show available files
        self.curr_files.append([loaded_file_name, np.shape(loaded_file_contents)])
        self.update_curr_files_table()
        
    def update_curr_files_table(self):
        num_files = len(self.curr_files)
        self.curr_files_table.setRowCount(num_files)
        
        for i in range(num_files):
            file_path = QTableWidgetItem(str(self.curr_files[i][0]))
            data_shape = QTableWidgetItem(str(self.curr_files[i][1]))
            self.curr_files_table.setItem(i, 0, file_path)
            self.curr_files_table.setItem(i, 1, data_shape)
            
        self.curr_files_table.resizeColumnsToContents()
        self.curr_files_table.resizeRowsToContents()
        
    def scrolled(self):
        self.curr_idx = self.idx_scroll.value()
        self.show_img()
        self.curr_idx_label.setText(str(self.curr_idx))
    
    def adjust_idx_range(self):
        # retrieve new values
        self.start_idx = int(self.start_idx_ledit.text())
        self.step_size = int(self.step_size_ledit.text())
        self.end_idx = int(self.end_idx_ledit.text())
        
        # validate current index
        curr_idx_valid_flag = ((self.start_idx <= self.curr_idx) 
                               and (self.curr_idx <= self.end_idx))
        
        if not curr_idx_valid_flag:
            self.curr_idx = self.start_idx

        self.reflect_new_idx_range()
        self.show_img()
        
class LoaderThread(QThread):
    loaded_file_contents = pyqtSignal(str, np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running_flag = False
                
        ## TIF files handling
        self.work_list = []
        
    def run(self):
        while (self.running_flag and len(self.work_list)):
            print("thread running, work_list: ", self.work_list)
            file_to_load = self.work_list.pop(0)
            self.loaded_file_contents.emit(file_to_load, self.load_tif_as_np(file_to_load))
        
    # def update_running_flag(self, flag):
    #     self.running_flag = True
        
    def update_work_list(self, work_list):
        self.work_list.extend(work_list)
        print("updated work_list: ", work_list)
    
    def load_tif_as_np(self, file_name):
        print("loading at thread: ", file_name)
        im = Image.open(file_name)
        im_arr = []
        for im_slice in ImageSequence.Iterator(im):
            im_arr.append(np.array(im_slice).T)
        return np.array(im_arr)

    
if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    TR = TifReader(window_title="TIF Reader v0")
    TR.show()