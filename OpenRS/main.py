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

import sys,os,ctypes
from PyQt5 import QtCore, QtGui, QtWidgets
import vtk
import importlib.resources
from OpenRS.open_rs_common import get_file, get_save_file, translate_amphyon_vtp
import OpenRS.model_viewer as mv
import OpenRS.point_selector as ps
from OpenRS.flexure_widget import modeling_widget
from OpenRS.open_rs_hdf5_io import *

class main_window(QtWidgets.QMainWindow):
    '''
    Need to create a inherited version of a QMainWindow to override the closeEvent method to finalize any tabs before garbage collection when running more than one vtkWidget.
    '''
    def __init__(self, app):
        super().__init__()
        
        ico = importlib.resources.files('OpenRS') / 'meta/OpenRS_icon.png'
        with importlib.resources.as_file(ico) as path:
            self.setWindowIcon(QtGui.QIcon(path.__str__()))
        self.setWindowTitle("OpenRS - main v%s" %__version__)
        if os.name == 'nt':
            myappid = 'OpenRS.main.%s'%__version__ # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid) #windows taskbar icon
        
        screen = QtWidgets.QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setMinimumSize(QtCore.QSize(int(2*rect.width()/3), int(7*rect.height()/8)))
        
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
        
        util_menu = self.menubar.addMenu('&Utilities')
        flexure_button = QtWidgets.QAction('Flexure model', self)
        flexure_button.setStatusTip('Opens FEA flexure calculation dialog')
        flexure_button.triggered.connect(self.launch_modeling)
        amphyon_translate_button = QtWidgets.QAction('Translate Amphyon file ...', self)
        amphyon_translate_button.setStatusTip('Translates Amphyon-formatted output text file into OpenRS/ParaView format.')
        amphyon_translate_button.triggered.connect(self.launch_translate_amphyon)
        
        #add actions to menubar
        file_menu.addAction(load_button)
        file_menu.addAction(save_button)
        file_menu.addAction(save_as_button)
        file_menu.addAction(exit_button)
        util_menu.addAction(flexure_button)
        util_menu.addAction(amphyon_translate_button)

        #add menubar to window
        self.setMenuBar(self.menubar)
        
        #add a status bar
        self.statusbar = QtWidgets.QStatusBar(self)
        # self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        
        self.tabWidget.setCurrentIndex(0)
        self.setCentralWidget(self.tabWidget)
        self.initialize_all()
    
    def center(self):
        frame = self.frameGeometry()
        center = QtWidgets.QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())
    
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
        file, _ = get_save_file('*.OpenRS')
        
        if file is None:
            return
        
        #test to see if it is a different file
        if file != self.file:
            self.file = initialize_HDF5(file)
        else:
            self.file = file
        
        self.setWindowTitle("%s  -  OpenRS v%s" %(self.file,__version__))
        self.psui.file = self.file
        self.mvui.file = self.file
        self.mvui.write_h5()
        self.psui.write_h5()

    def launch_modeling(self):
        self.mw = modeling_widget(self)
    
    def launch_translate_amphyon(self):
        translate_amphyon_vtp(None,None)
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    
    app_main_window = main_window(app)
    app_main_window.center()
    app_main_window.show()
    
    
    sys.exit(app.exec_())