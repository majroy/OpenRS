#!/usr/bin/env python
'''
Qt and VTK application to allow for comparing stress with different techniques
-------------------------------------------------------------------------------
0.1 - Inital release
'''
__author__ = "M.J. Roy"
__version__ = "0.1"
__email__ = "matthew.roy@manchester.ac.uk"
__status__ = "Experimental"
__copyright__ = "(c) M. J. Roy, 2021-"

import os, sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import QtGui, QtWidgets, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib import rc
from pkg_resources import Requirement, resource_filename
from OpenRS.open_rs_common import get_file, get_save_file, line_query, generate_axis_actor, generate_sphere, generate_info_actor, xyview, yzview, xzview, flip_visible, make_logo
from OpenRS.model_viewer import read_model_data
from OpenRS.open_rs_hdf5_io import *

def launch(*args, **kwargs):
    '''
    Start Qt/VTK interaction if started independently
    '''
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    app.processEvents()
    
    window = interactor(None) #otherwise specify parent widget
    window.show()
    
    window.iren.Initialize()
    
    if len(args) == 1:
        window.file = args[0]
        interactor.load_h5(window)
    
    ret = app.exec_()
    
    if sys.stdin.isatty() and not hasattr(sys, 'ps1'):
        sys.exit(ret)
    else:
        return window

class main_window(object):
    """
    Generic object containing all UI
    """
    
    def setup(self, MainWindow):
        '''
        Creates Qt interactor
        '''
        
        #if called as a script, then treat as a mainwindow, otherwise treat as a generic widget
        if hasattr(MainWindow,'setCentralWidget'):
            MainWindow.setCentralWidget(self.centralWidget)
        else:
            self.centralWidget=MainWindow
        MainWindow.setWindowTitle("OpenRS - comparer v%s" %__version__)
        
        #create new layout to hold both VTK and Qt interactors
        mainlayout=QtWidgets.QHBoxLayout(self.centralWidget)

        #create VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        
        #create Qt layout to contain interactions
        load_model_box = QtWidgets.QGridLayout()
        
        #create VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(100)
        sizePolicy.setVerticalStretch(100)
        self.vtkWidget.setSizePolicy(sizePolicy)
        
        self.vtkWidget.setMinimumSize(QtCore.QSize(800, 600))
        
        #set fonts
        head_font=QtGui.QFont("Helvetica [Cronyx]",weight=QtGui.QFont.Bold)
        io_font = QtGui.QFont("Helvetica")
        
        dummy_label = QtWidgets.QLabel("Nothing loaded.")
        
        #create point box
        point_box = QtWidgets.QGroupBox('Measurement points')
        point_box_layout = QtWidgets.QVBoxLayout()
        #create tablewidget
        self.point_table = QtWidgets.QTableWidget()
        self.point_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        # self.point_table.setSelectionBehavior(QtWidgets.QTableView().SelectRows)
        #fix number of columns:
        self.point_table.setColumnCount(3)
        self.point_table.setHorizontalHeaderLabels(['X', 'Y', 'Z'])
        self.point_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        #add to box
        point_box_layout.addWidget(self.point_table)
        point_box.setLayout(point_box_layout)
        
        
        lvlayout=QtWidgets.QVBoxLayout()
        lvlayout.addWidget(dummy_label)
        lvlayout.addWidget(point_box)

        lvlayout.addStretch(1)
        
        mainlayout.addWidget(self.vtkWidget)
        mainlayout.addStretch(1)
        mainlayout.addLayout(lvlayout)

        def initialize(self):
            self.vtkWidget.start()

class interactor(QtWidgets.QWidget):
    '''
    Inherits most properties from Qwidget, but primes the VTK window, and ties functions and methods to interactors defined in main_window
    '''
    def __init__(self,parent):
        super(interactor, self).__init__(parent)
        self.ui = main_window()
        self.ui.setup(self)
        
        #set viewports
        upperViewport = [0, 0, 1, 1]
        # lowerViewport = [0.8, 0.0, 1, 0.2]
        lowerViewport = [0.8, 0.0, 1, 0.38]
        self.main_ren = vtk.vtkRenderer()
        self.sub_ren = vtk.vtkRenderer()
        colors = vtk.vtkNamedColors()
        self.main_ren.SetBackground(colors.GetColor3d("aliceblue"))
        self.sub_ren.SetBackground(colors.GetColor3d("aliceblue"))
        self.main_ren.SetViewport(upperViewport)
        self.sub_ren.SetViewport(lowerViewport)

        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.main_ren)
        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.sub_ren)
        

        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()
        style=vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)
        self.iren.AddObserver("KeyPressEvent", self.keypress)
        self.iren.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.main_ren.GetActiveCamera().ParallelProjectionOn()
        self.sub_ren.SetActiveCamera(self.main_ren.GetActiveCamera())
        self.file = None #overwritten at launch
        make_logo(self.main_ren)
        
        self.ui.point_table.itemDoubleClicked.connect(self.double_click)
    
    def double_click(self,item):
        print('item:',item.text(), item)
        #change model opacity to 50% if the transparency isn't already set
        if self.mesh_actor.GetProperty().GetOpacity() == 1.0: #it's just loaded
            self.mesh_actor.GetProperty().SetOpacity(0.5)
        #point location is the info in the row, which is the main index of mdata
        #draw a circle there with some arbitrary radius and put it on the main_ren
        self.radius = 4
        active_meas_pnt = generate_sphere(self.mdata[item.row()],self.radius,(1,1,1))
        # print(self.mdata[item.row()])
        self.main_ren.AddActor(active_meas_pnt)
        
        self.update_volume(self.radius,self.mdata[item.row()])
        
        self.ui.vtkWidget.update()
        
    def load_h5(self):
        if self.file is None:
            self.file, _ = get_file("*.OpenRS")
        
        if self.file is not None:
            #check the file has a populated model object
            with h5py.File(self.file, 'r') as f:
                if "model_data/piece0" not in f:
                    self.display_info('Model data could not be loaded.')
                try:
                    self.mdata = f['measurement_points/points'][()].tolist()
                except:
                    self.display_info('No measurement points could be loaded.')
            r = HDF5vtkug_reader()
            r.SetFileName(self.file)
            r.Update()
            self.active_vtu = r.GetOutputDataObject(0).GetBlock(0)
            # self.ui.load_label.setText(self.file)
            #call draw_model
            self.draw_model()
            self.display_info('Loaded model from data file.')
        self.ui.vtkWidget.update() #for display of info_actor
        self.update_measurement_table()

    def update_measurement_table(self):
        self.ui.point_table.setRowCount(len(self.mdata))
        
        
        for i in range(len(self.mdata)):
            for j in range(3): ##number of columns
                item = QtWidgets.QTableWidgetItem(str(self.mdata[i][j]))
                self.ui.point_table.setItem(i,j,item)
    
        #update size automatically
        # self.ui.point_table.resizeColumnsToContents()
    
    def update_volume(self,r,c):
        '''
        Updates inset active volume with an extract filter, assumes sphere with radius r and centre c (tuple)
        '''
        self.sub_ren.RemoveAllViewProps()
        
        
        geo = vtk.vtkSphere()
        geo.SetRadius(r)
        geo.SetCenter(c)

        extract = vtk.vtkExtractGeometry()
        extract.ExtractInsideOn()
        extract.SetInputDataObject(self.active_vtu)
        extract.SetImplicitFunction(geo)
        extract.Update()
        
        # q4 = v2n(extract.GetOutput().GetPointData().GetArray('S11'))
        
        extract_mapper = vtk.vtkDataSetMapper()
        extract_mapper.SetInputData(extract.GetOutput())
        extract_mapper.SetScalarRange(self.active_vtu.GetScalarRange())
        extract_mapper.SetLookupTable(self.mesh_lut)
        

        extract_actor = vtk.vtkActor()
        extract_actor.SetMapper(extract_mapper)
        
        self.sub_ren.AddActor(extract_actor)
        self.sub_ren.ResetCamera()
        self.ui.vtkWidget.update()
        
    def draw_model(self):

        #clear all actors
        self.main_ren.RemoveAllViewProps()
        self.mesh_actor, _, self.mesh_mapper, self.mesh_lut, range = read_model_data(\
        self.active_vtu, \
        'S11', None, False)

        
        
        #create scale bar
        scalar_bar_widget = vtk.vtkScalarBarWidget()
        scalarBarRep = scalar_bar_widget.GetRepresentation()
        scalarBarRep.GetPositionCoordinate().SetValue(0.01,0.01)
        scalarBarRep.GetPosition2Coordinate().SetValue(0.09,0.9)
        self.sb_actor=scalar_bar_widget.GetScalarBarActor()

        # self.sb_actor.SetNumberOfLabels(self.ui.num_contour.value())

        self.sb_actor.SetLookupTable(self.mesh_lut)
        self.sb_actor.SetTitle('MPa')


        #attempt to change scalebar properties
        propT = vtk.vtkTextProperty()
        propL = vtk.vtkTextProperty()
        propT.SetColor(0,0,0)
        propL.SetColor(0,0,0)
        propT.SetFontFamilyToArial()
        # propT.ItalicOff()
        propT.BoldOn()
        propL.BoldOff()
        propL.SetFontSize(1)
        propT.SetFontSize(1)
        self.sb_actor.GetLabelTextProperty().SetColor(0,0,0)
        self.sb_actor.GetTitleTextProperty().SetColor(0,0,0)
        self.sb_actor.GetLabelTextProperty().SetFontSize(1)
        self.sb_actor.GetTitleTextProperty().SetFontSize(1)
        self.sb_actor.SetLabelFormat("%.1f")

        self.main_ren.AddActor(self.mesh_actor)
        self.sub_ren.AddActor(self.mesh_actor)
        self.main_ren.AddActor(self.sb_actor)
        self.axis_actor = generate_axis_actor(self.active_vtu,self.main_ren)
        self.main_ren.AddActor(self.axis_actor)
        
        scalar_bar_widget.SetInteractor(self.iren)
        scalar_bar_widget.On()
        self.main_ren.ResetCamera()
        
        self.ui.vtkWidget.update()

    def keypress(self, obj, event):
        '''
        VTK interactor-specific listener for keypresses
        '''
        key = obj.GetKeySym()
        
        if key =="1":
            xyview(self.main_ren)
            xyview(self.sub_ren)
        elif key =="2":
            yzview(self.main_ren)
            yzview(self.sub_ren)
        elif key =="3":
            xzview(self.main_ren)
            xzview(self.sub_ren)
        elif key == "Up":
            self.main_ren.GetActiveCamera().Roll(30)
            self.sub_ren.GetActiveCamera().Roll(30)
        elif key == "Down":
            self.main_ren.GetActiveCamera().Roll(-30)
            self.sub_ren.GetActiveCamera().Roll(-30)
        elif key == "w": #debug
            self.write_h5()
        elif key == "l": #debug
            self.load_h5()

        elif key=="i":
            im = vtk.vtkWindowToImageFilter()
            writer = vtk.vtkPNGWriter()
            colors = vtk.vtkNamedColors()
            self.main_ren.SetBackground(colors.GetColor3d("white"))
            im.SetInput(self.ui.vtkWidget._RenderWindow)
            im.Update()
            writer.SetInputConnection(im.GetOutputPort())
            writer.SetFileName("OpenRS_capture.png")
            writer.Write()
            self.main_ren.SetBackground(colors.GetColor3d("aliceblue"))
            self.display_info('Image saved.')
        
        elif key=="r":
            flip_visible(self.axis_actor)
        
        self.main_ren.ResetCamera()
        self.sub_ren.ResetCamera()
        self.ui.vtkWidget.update()

    def on_mouse_move(self, obj, event):
        if hasattr(self,'info_actor'):
            self.main_ren.RemoveActor(self.info_actor)
        else:
            pass

    def display_info(self,msg):
        '''
        Checks if there's an info_actor and removes it before displaying another one
        '''
        if hasattr(self,'info_actor'):
            self.main_ren.RemoveActor(self.info_actor)
        self.info_actor = generate_info_actor(msg,self.main_ren)
        self.main_ren.AddActor(self.info_actor)
            
# def read_model_data(vtu, component, mesh_mapper, edges):
    # '''
    # Read an unstructured grid from an XML formated vtu file, or operate on a ug object, setting the output to be a 'component'. If not specified, generate a lookup table and range on the incoming mapper.
    # '''
    # #If read is true, then vtuname is a VTU file
    # if type(vtu) is str:
        # reader = vtk.vtkXMLUnstructuredGridReader()
        # reader.SetFileName(vtu)
        # reader.Update()
        # output = reader.GetOutput()
    # else: #coming from hdf5reader
        # output = vtu
        
    # output.GetPointData().SetActiveScalars(component)
    # if mesh_mapper is None:
        # #build lookup table according to field
        # lut = vtk.vtkLookupTable()
        # lut.SetHueRange(0.667, 0)
        # lut.Build()
        # range = output.GetScalarRange()

        # # map data set
        # mesh_mapper = vtk.vtkDataSetMapper()
        # mesh_mapper.SetInputData(output)
        # mesh_mapper.SetScalarRange(range)
        # mesh_mapper.SetLookupTable(lut)


    # # else use the passed mesh_mapper to create the actor
    # actor = vtk.vtkActor()
    # actor.SetMapper(mesh_mapper)
    # if edges:
        # actor.GetProperty().EdgeVisibilityOn()
    # else:
        # actor.GetProperty().EdgeVisibilityOff()
    # actor.GetProperty().SetLineWidth(0)

    # return actor, output, mesh_mapper, lut, range

if __name__ == "__main__":
    if len(sys.argv)>1:
        launch(sys.argv[1])
    else:
        launch()