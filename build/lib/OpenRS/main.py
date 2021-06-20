#!/usr/bin/env python
'''
Qt, VTK and matplotlib application to allow for viewing and querying residual stress fields. 
-------------------------------------------------------------------------------
0.1 - Inital release
'''

__author__ = "M.J. Roy"
__version__ = "0.1"
__email__ = "matthew.roy@manchester.ac.uk"
__status__ = "Experimental"
__copyright__ = "(c) M. J. Roy, 2021-"

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import vtk
from pkg_resources import Requirement, resource_filename
import OpenRS.model_viewer as mv
import OpenRS.point_selector as ps
from OpenRS.open_rs_common import get_file, get_save_file
from OpenRS.open_rs_hdf5_io import *

class main_window(QtWidgets.QMainWindow):
    '''
    Need to create a inherited version of a QMainWindow to override the closeEvent method to finalise any tabs before garbage collection when running more than one vtkWidget.
    '''
    def __init__(self, parent=None):
        super(main_window, self).__init__(parent)
        
        self.setWindowIcon(QtGui.QIcon(resource_filename("OpenRS","meta/OpenRS_icon.png")))
        self.setWindowTitle("OpenRS - main v%s" %__version__)
        
        self.file = None #active OpenRS datafile
        
        self.tabWidget = QtWidgets.QTabWidget()

        self.mvtab = QtWidgets.QWidget(self.tabWidget)
        self.tabWidget.addTab(self.mvtab, "Model viewer")
        self.pstab = QtWidgets.QWidget(self.tabWidget)
        self.tabWidget.addTab(self.pstab, "Point selector")
        self.setCentralWidget(self.tabWidget)

        #make menubar
        self.menubar = QtWidgets.QMenuBar(self)
        file_menu = self.menubar.addMenu('&File')

        load_button = QtWidgets.QAction('Load', self)
        load_button.setShortcut('Ctrl+L')
        load_button.setStatusTip('Load OpenRS data file')
        load_button.triggered.connect(self.populate)

        save_button = QtWidgets.QAction('Save', self)
        save_button.setShortcut('Ctrl+S')
        save_button.setStatusTip('Save all to OpenRS data file')
        save_button.triggered.connect(self.save_all)

        save_as_button = QtWidgets.QAction('Save As...', self)
        save_as_button.setStatusTip('Save all to new OpenRS data file')
        save_as_button.triggered.connect(self.save_as)
        
        exit_button = QtWidgets.QAction('Exit', self)
        exit_button.setShortcut('Ctrl+Q')
        exit_button.setStatusTip('Exit application')
        exit_button.triggered.connect(self.close)
        
        #add actions to menubar
        file_menu.addAction(load_button)
        file_menu.addAction(save_button)
        file_menu.addAction(save_as_button)
        file_menu.addAction(exit_button)

        #add menubar to window
        self.setMenuBar(self.menubar)
        
        #add a status bar
        self.statusbar = QtWidgets.QStatusBar(self)
        # self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        
        self.tabWidget.setCurrentIndex(0)
        
        self.initialize_all()
        
    def closeEvent(self, event):
        '''
        Need to finalize all VTK widgets otherwise openGL errors abound
        '''
        self.mvui.ui.vtkWidget.close()
        self.psui.ui.vtkWidget.close()
        self.psui.ui.sgv.vtkWidget.close()

        
    def setup_mv(self):
        '''
        create an instance of the model viewer interactor with current main_window as parent.
        '''
        lhLayout = QtWidgets.QHBoxLayout(self.mvtab)
        self.mvui=mv.interactor(self.tabWidget)
        self.mvui.iren.Initialize()
        lhLayout.addWidget(self.mvui)
        
    def setup_ps(self):
        '''
        create an instance of the point_selector interactor with current main_window as parent.
        '''
        lhLayout = QtWidgets.QHBoxLayout(self.pstab)
        self.psui=ps.interactor(self.tabWidget)
        self.psui.iren.Initialize()
        lhLayout.addWidget(self.psui)

    def initialize_all(self):
        self.setup_mv()
        self.setup_ps()

    def populate(self):
        '''
        Gets an OpenRS file, calls load_h5 methods
        '''

        self.file, _ = get_file('*.OpenRS')
            
        if self.file is not None:
            self.setWindowTitle("%s  -  OpenRS v%s" %(self.file,__version__))
            self.psui.file = self.file
            self.mvui.file = self.file
            self.mvui.load_h5()
            self.psui.load_h5()
            
    def save_all(self):
        '''
        Saves to current file, gets one if it doesn't exist
        '''
        if self.file is None:
            self.file = initialize_HDF5()
        
        if self.file is not None:
            self.setWindowTitle("%s  -  OpenRS v%s" %(self.file,__version__))
            self.psui.file = self.file
            self.mvui.file = self.file
            self.mvui.write_h5()
            self.psui.write_h5()
            
    def save_as(self):
        '''
        Saves to current file, gets one if it doesn't exist
        '''
        self.file, _ = get_save_file('*.OpenRS')
        
        if self.file is not None:
            self.setWindowTitle("%s  -  OpenRS v%s" %(self.file,__version__))
            self.psui.file = self.file
            self.mvui.file = self.file
            self.mvui.write_h5()
            self.psui.write_h5()

        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    #debug vtk errors
    # fow = vtk.vtkFileOutputWindow();
    # fow.SetFileName("vtk_errors.txt");
    # ow = vtk.vtkOutputWindow()
    # ow.SetInstance(fow)
    
    app_main_window = main_window()
    app_main_window.show()
    
    
    sys.exit(app.exec_())