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
        
        # Internal 
        self.data_as_np = None
        self.curr_dir = ""
        self.curr_files = []
        self.curr_idx = -1
        self.start_idx = -1
        self.end_idx = -1
        self.step_size = -1
        
        # Setup: loader thread
        self.my_thread = LoaderThread(self)
        self.tif_arr = self.my_thread.tif_arr
        self.files_to_load.connect(self.my_thread.loader)
        self.my_thread.loaded_data.connect(self.update_data)
    
    def enable_viewers(self, flag):
        #TODO iterate with getattr
        self.image_viewer.setEnabled(flag)
        self.index_navigator.setEnabled(flag)
        self.curr_dir_label.setEnabled(flag)
        self.curr_idx_label.setEnabled(flag)
        self.viewer_options.setEnabled(flag)
        self.load_dir_btn.setEnabled(flag)
        self.load_file_btn.setEnabled(flag)
        self.save_btn.setEnabled(flag)

    def load_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        load_path, _ = QFileDialog.getOpenFileName(self,"load a .tif file", "",".tif Files(*.tif)", options=options)
        if not load_path:
            return  # user pressed "cancel"
        print(load_path)
        
        # start loading
        self.enable_viewers(False)
        self.files_to_load.emit(list(load_path))
        # self.data_as_np = self.load_tif_as_np(load_path)
        self.curr_dir = os.path.dirname(load_path)
        print(curr_dir)
        self.curr_files = [load_path]
        self.curr_idx = 0
        self.start_idx = 0
        self.end_idx = np.shape(self.data_as_np)[0] - 1
        self.step_size = 1
        self.enable_viewers(True)
        
    def load_dir(self):
        load_path = QFileDialog.getExistingDirectory(self,"load a directory", "", QFileDialog.ShowDirsOnly)
        
        if not load_path:
            return  # user pressed "cancel"
        
        print(load_path)
        tif_list = glob(load_path + "/" + "*.tif")
        print(tif_list)
        
        # return if this dir does not contain .tif files
        if not tif_list:
            error_dialog = QErrorMessage()
            error_dialog.showMessage('this directory does not contain .tif files')
            return
            
        self.curr_dir = load_path
        self.curr_files = tif_list
        
        stacked_data = np.array([])
        
        
        self.data_as_np = stacked_data
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
        
class LoaderThread(QThread):
    loaded_data = pyqtSignal(np.ndarray)
    
    def __init__(self, reader):
        super().__init__()
        self.tif_arr = []
        self.reader = reader
    
    def load_tif_as_np(self, tif_file):
        im = Image.open(tif_file)
        im_arr = []
        for im_slice in ImageSequence.Iterator(im):
            im_arr.append(np.array(im_slice))  #.T?
        return np.array(im_arr)
    
    def loader(self, tif_list):
        for tif_file in tif_list:
            # TODO: if tif img dimensions are different: raggedarray
            file_content = self.load_tif_as_np(tif_file)
            print("file_content shape: ", np.shape(file_content))
            loaded_data.emit(file_content)
            # try:
            #     stacked_data = np.append(stacked_data, file_content, axis=0)
            #     print("try: ", np.shape(stacked_data))
            # except:
            #     stacked_data = file_content
            #     print("except: ", np.shape(stacked_data))
    

if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    TR = TifReader(window_title="TIF Reader v0")
    TR.show()