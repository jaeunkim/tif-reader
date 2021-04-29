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
        
        # Connect sockets and signals
        self.load_file_btn.clicked.connect(self.load_file)
        self.load_dir_btn.clicked.connect(self.load_dir)
        self.save_btn.clicked.connect(self.save_file)
        self.clear_data_btn.clicked.connect(self.clear_data)
        
        # Internal 
        self.data_as_np = None
        self.curr_dir = ""
        self.tif_files = []
        self.curr_idx = 0
        self.start_idx = 0
        self.end_idx = -1
        self.step_size = 1
        
        # Setup: loader thread
        self.loader_thread = LoaderThread(self)
        self.files_to_load.connect(self.loader_thread.loader)
        # self.my_thread.loaded_data.connect(self.update_data)
    
    def clear_data(self):
        #TODO check if this actually releases memory
        self.loader_thread.running_flag = False
        self.data_as_np = None
        #TODO clear file list label
        
    def enable_viewers(self, flag):
        #TODO iterate with getattr
        self.image_viewer.setEnabled(flag)
        self.index_navigator.setEnabled(flag)
        self.curr_dir_label.setEnabled(flag)
        self.curr_idx_label.setEnabled(flag)
        self.viewer_options.setEnabled(flag)
        self.load_dir_btn.setEnabled(flag)
        self.load_file_btn.setEnabled(flag)
        self.clear_data_btn.setEnabled(flag)
        self.save_btn.setEnabled(flag)
    
        # "cancel loading" button behaves differently
        self.cancel_loading_btn(not flag)
        
    def show_img(self):            
        self.ax.imshow(self.data_as_np[self.curr_idx], vmin=self.vmin, vmax=self.vmax)
        self.canvas.draw()

    def load_file(self):
        # dialog to choose file
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_to_load, _ = QFileDialog.getOpenFileName(self,"load a .tif file", "",".tif Files(*.tif)", options=options)
        if not file_to_load:
            return  # user pressed "cancel"
        print(file_to_load)
        
        # update info and initiate load
        self.tif_files.append(file_to_load)
        self.curr_dir = os.path.dirname(file_to_load)
        self.curr_dir_label.setText(self.curr_dir)
        self.enable_viewers(False)
        self.files_to_load.emit(list(file_to_load))
        #TODO get signal from thread
        self.tif_files.append(file_to_load)
        self.loader_thread.loader([load_path])

        self.end_idx = np.shape(self.data_as_np)[0] - 1
        self.step_size = 1
        self.enable_viewers(True)
        
    def load_dir(self):
        load_path = QFileDialog.getExistingDirectory(self,"load a directory", "", QFileDialog.ShowDirsOnly)
        
        if not load_path:
            return  # user pressed "cancel"
        
        print(load_path)
        tif_files = glob(load_path + "/" + "*.tif")
        print(tif_files)
        
        # return if this dir does not contain .tif files
        if not tif_files:
            error_dialog = QErrorMessage()
            error_dialog.showMessage('this directory does not contain .tif files')
            return
            
        #self.curr_dir = load_path
        #self.tif_files = tif_files
        
        self.loader_thread.tif_files.append(tif_files)        
        self.loader_thread.loader(self.tif_files)

        
        self.curr_idx = 0
        self.start_idx = 0
        self.end_idx = np.shape(self.data_as_np)[0] - 1
        self.step_size = 1
            
    def save_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        save_path, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","Pickle Files(*.pkl)", options=options)
        if not save_path:
            error_dialog = QErrorMessage()
            error_dialog.showMessage('cannot save here')
            return
        
        print("saving at: ", fileName)
        new_data = self.data_as_np[self.start_idx: self.step_size: self.end_idx+1]
        save_dict = {}
        save_dict["original path"] = str(self.curr_files)
        save_dict["data"] = new_data
        with open(filename, 'wb') as wf:
            pkl.dump(save_dict, wf)
        
    def create_canvas(self, frame):
        fig = plt.Figure(tight_layout=True)
        canvas = FigureCanvas(fig)
        
        toolbar = NavigationToolbar(canvas, self)
        
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        frame.setLayout(layout)
        
        ax = fig.add_subplot(1,1,1)
        
        return toolbar, ax, canvas
    
    def update_data(self, loaded_data):
        stacked_data=[]
                    # try:
            #     stacked_data = np.append(stacked_data, file_content, axis=0)
            #     print("try: ", np.shape(stacked_data))
            # except:
            #     stacked_data = file_content
            #     print("except: ", np.shape(stacked_data))
            
    def imageUpdate(self, recv_data):
        pass
    
    def th_test(self):
        self.loader_thread.running_flag = True
        self.loader_thread.start()
        
        
class LoaderThread(QThread):
    file_loaded = pyqtSignal(int, int)
    done_loading = pyqtSignal(int)
    
    def __init__(self, reader):
        super().__init__()
        self.reader = reader
        self.running_flag = False
                
        ## TIF files handling
        self.tif_files = []
        self.loading_idx = 0
        
    def run(self):
        self.currently_loading_file_idx = 0
        while (self.running_flag and (self.loading_idx <= len(self.tif_files))):
            self.reader.LBL_Log.setText("Loading... File: %02d/%02d"
                                        % (self.loading_idx, len(self.tif_files)))
            self.load_tif_as_np(self.loading_idx)
            self.loading_idx += 1
    
    def load_tif_as_np(self, idx):
        im = Image.open(self.tif_files[idx])
        im_arr = []
        for im_slice in ImageSequence.Iterator(im):
            im_arr.append(np.array(im_slice).T)
        return np.array(im_arr)
    
    def loader(self, tif_list):
        for idx, tif_file in enumerate(tif_list):
            # TODO: if tif img dimensions are different: raggedarray
            file_content = self.load_tif_as_np(tif_file)
            print("file_content shape: ", np.shape(file_content))
            # loaded_data.emit(file_content)
            try:
                self.reader.data_as_np = np.append(self.reader.data_as_np, file_content, axis=0)
                print("try: ", np.shape(self.reader.data_as_np))
            except:
                self.reader.data_as_np = file_content
                print("except: ", np.shape(self.reader.data_as_np))
            self.file_loaded.emit(idx, len(tif_list))
    

if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    TR = TifReader(window_title="TIF Reader v0")
    TR.show()