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
from OpenRS.open_rs_common import get_file, get_save_file, line_query, generate_axis_actor, generate_info_actor, xyview, yzview, xzview, flip_visible, make_logo
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
        MainWindow.setWindowTitle("OpenRS - model viewer v%s" %__version__)
        
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
        
        #make display layout
        display_label = QtWidgets.QLabel("Display")
        display_label.setFont(head_font)
        #buttons
        self.load_button = QtWidgets.QPushButton('Load')
        self.load_label = QtWidgets.QLabel("Nothing loaded.")
        self.load_label.setWordWrap(True)
        self.load_label.setFont(io_font)
        #make combo box for components
        self.component_cb = QtWidgets.QComboBox()
        self.component_cb.addItems(['S11', 'S22', 'S33'])
        self.component_cb.setEnabled(False)
        
        #make contour layout
        contour_layout = QtWidgets.QGridLayout()
        contour_label = QtWidgets.QLabel("Contours")
        contour_label.setFont(head_font)
        min_contour_label = QtWidgets.QLabel("Min:")
        self.min_contour = QtWidgets.QDoubleSpinBox()
        self.min_contour.setMinimum(-100000)
        self.min_contour.setMaximum(100000)
        max_contour_label = QtWidgets.QLabel("Max:")
        self.max_contour = QtWidgets.QDoubleSpinBox()
        self.max_contour.setMinimum(-100000)
        self.max_contour.setMaximum(100000)
        num_contour_label = QtWidgets.QLabel("Interval:")
        self.num_contour = QtWidgets.QSpinBox()
        self.num_contour.setMinimum(3)
        self.num_contour.setMaximum(20)
        self.num_contour.setValue(5)
        self.update_contours_button = QtWidgets.QPushButton('Update')
        self.update_contours_button.setEnabled(False)
        contour_layout.addWidget(contour_label,0,0,1,6)
        contour_layout.addWidget(min_contour_label,1,0,1,1)
        contour_layout.addWidget(self.min_contour,1,1,1,1)
        contour_layout.addWidget(max_contour_label,1,2,1,1)
        contour_layout.addWidget(self.max_contour,1,3,1,1)
        contour_layout.addWidget(num_contour_label,1,4,1,1)
        contour_layout.addWidget(self.num_contour,1,5,1,1)
        contour_layout.addWidget(self.update_contours_button,1,6,1,1)
        
        
        # line extraction from surface
        extract_box = QtWidgets.QGridLayout()
        extract_data_label = QtWidgets.QLabel("Extract")
        extract_data_label.setFont(head_font)
        # x, y, z of first point
        point1_x_label = QtWidgets.QLabel("x0:")
        self.point1_x_coord = QtWidgets.QDoubleSpinBox()
        self.point1_x_coord.setMinimum(-100000)
        self.point1_x_coord.setMaximum(100000)
        point1_y_label = QtWidgets.QLabel("y0:")
        self.point1_y_coord = QtWidgets.QDoubleSpinBox()
        self.point1_y_coord.setMinimum(-100000)
        self.point1_y_coord.setMaximum(100000)
        point1_z_label = QtWidgets.QLabel("z0:")
        self.point1_z_coord = QtWidgets.QDoubleSpinBox()
        self.point1_z_coord.setMinimum(-100000)
        self.point1_z_coord.setMaximum(100000)

        # x, y, z of second point
        point2_x_label = QtWidgets.QLabel("x1:")
        self.point2_x_coord = QtWidgets.QDoubleSpinBox()
        self.point2_x_coord.setMinimum(-100000)
        self.point2_x_coord.setMaximum(100000)
        point2_y_label = QtWidgets.QLabel("y1:")
        self.point2_y_coord = QtWidgets.QDoubleSpinBox()
        self.point2_y_coord.setMinimum(-100000)
        self.point2_y_coord.setMaximum(100000)
        point2_z_label = QtWidgets.QLabel("z1:")
        self.point2_z_coord = QtWidgets.QDoubleSpinBox()
        self.point2_z_coord.setMinimum(-100000)
        self.point2_z_coord.setMaximum(100000)
        
        interval_label=QtWidgets.QLabel("Interval:")
        self.extract_interval=QtWidgets.QSpinBox()
        self.extract_interval.setValue(50)
        self.extract_interval.setMinimum(3)
        self.extract_interval.setMaximum(1000)
        
        self.extract_button = QtWidgets.QPushButton('Extract')
        self.extract_button.setEnabled(False)
        self.export_button = QtWidgets.QPushButton('Export')
        self.export_button.setEnabled(False)
        
        #create figure canvas etc

        #plot
        #matplotlib finds non-default fonts only with TeX enabled, this is prohibitive from a performance standpoint
        # rc('font',**{'family':'sans-serif','sans-serif':['helvetica']})
        # rc('text', usetex=True)
        self.figure = plt.figure(figsize=(4,4))
        #changes the background of the plot, otherwise white
        # self.figure.patch.set_facecolor((242/255,242/255,242/255))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(QtCore.QSize(400, 500))

        #add everything to the extract box
        extract_box.addWidget(extract_data_label,0,0,1,6)
        extract_box.addWidget(point1_x_label,1,0,1,1)
        extract_box.addWidget(self.point1_x_coord,1,1,1,1)
        extract_box.addWidget(point1_y_label,1,2,1,1)
        extract_box.addWidget(self.point1_y_coord,1,3,1,1)
        extract_box.addWidget(point1_z_label,1,4,1,1)
        extract_box.addWidget(self.point1_z_coord,1,5,1,1)
        extract_box.addWidget(point2_x_label,2,0,1,1)
        extract_box.addWidget(self.point2_x_coord,2,1,1,1)
        extract_box.addWidget(point2_y_label,2,2,1,1)
        extract_box.addWidget(self.point2_y_coord,2,3,1,1)
        extract_box.addWidget(point2_z_label,2,4,1,1)
        extract_box.addWidget(self.point2_z_coord,2,5,1,1)
        extract_box.addWidget(interval_label,3,0,1,1)
        extract_box.addWidget(self.extract_interval,3,1,1,1)
        extract_box.addWidget(self.extract_button,3,2,1,2)
        extract_box.addWidget(self.export_button,3,4,1,2)
        extract_box.addWidget(self.canvas,4,0,1,6)

        load_model_box.addWidget(display_label,0,0,1,1)
        load_model_box.addWidget(self.load_button,0,1,1,1)
        load_model_box.addWidget(self.component_cb,0,2,1,1)
        load_model_box.addWidget(self.load_label,1,0,1,3)

        
        frame_style = QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken
        
        lvlayout=QtWidgets.QVBoxLayout()
        lvlayout.addLayout(load_model_box)
        horiz_line1 = QtWidgets.QFrame()
        horiz_line1.setFrameStyle(frame_style)
        lvlayout.addWidget(horiz_line1)
        lvlayout.addLayout(contour_layout)
        horiz_line2 = QtWidgets.QFrame()
        horiz_line2.setFrameStyle(frame_style)
        lvlayout.addWidget(horiz_line2)
        lvlayout.addLayout(extract_box)
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
        self.ren = vtk.vtkRenderer()
        colors = vtk.vtkNamedColors()
        self.ren.SetBackground(colors.GetColor3d("aliceblue"))

        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()
        style=vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)
        self.iren.AddObserver("KeyPressEvent", self.keypress)
        self.iren.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.ren.GetActiveCamera().ParallelProjectionOn()
        
        self.file = None #overwritten at launch
        make_logo(self.ren)
        
        self.ui.load_button.clicked.connect(self.load_vtu)
        self.ui.component_cb.currentIndexChanged.connect(self.reset_model)
        self.ui.extract_button.clicked.connect(self.extract)
        self.ui.export_button.clicked.connect(self.export)
        self.ui.update_contours_button.clicked.connect(self.draw_model)
    
    def write_h5(self):
        '''
        method which writes to an hdf5 file if there is anything to write
        '''
        if self.file is None:
            self.file = initialize_HDF5()
        
        #itinerary from this interactor is just the model. If there is an existing unstructured grid, then nothing needs to be written
        if hasattr(self,'active_vtu') and isinstance(self.active_vtu, str):
            w = HDF5vtkug_writer()
            reader = vtk.vtkXMLUnstructuredGridReader()
            reader.SetFileName(self.active_vtu)
            reader.Update()
            w.SetInputConnection(reader.GetOutputPort())
            w.SetFileName(self.file)
            w.Update()
            self.info_actor = generate_info_actor(self.ren,'Saved to data file.')
            with h5py.File(self.file, 'r+') as f:
                f.attrs['date_modified'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        else:
            return

    def reset_model(self):
        '''
        Clears variable which triggers an update redrawing the model with the relevant component ranges.
        '''
        del self.vtu_output
        self.draw_model()

    def draw_model(self):
        '''
        Main method which updates the display of the model.
        '''
        self.component = self.ui.component_cb.currentText()
        #clear all actors
        self.ren.RemoveAllViewProps()
        if hasattr(self,'active_vtu') and not hasattr(self,'vtu_output'):
            mesh_actor, self.vtu_output, self.mesh_lut, r = read_model_data(\
            self.active_vtu, \
            self.component, \
            None, None)
            #update contour limits
            self.ui.min_contour.setValue(r[0])
            self.ui.max_contour.setValue(r[1])
            self.ui.update_contours_button.setEnabled(True)
            self.ui.extract_button.setEnabled(True)
            self.ui.export_button.setEnabled(True)
        elif hasattr(self,'vtu_output'):
            mesh_actor, self.vtu_output, _, _ = read_model_data(\
            self.active_vtu, \
            self.component, \
            self.mesh_lut, \
            (self.ui.min_contour.value(),self.ui.max_contour.value()))
        else:
            return
        
        #create scale bar
        scalar_bar_widget = vtk.vtkScalarBarWidget()
        scalarBarRep = scalar_bar_widget.GetRepresentation()
        scalarBarRep.GetPositionCoordinate().SetValue(0.01,0.01)
        scalarBarRep.GetPosition2Coordinate().SetValue(0.09,0.9)
        sb_actor=scalar_bar_widget.GetScalarBarActor()

        sb_actor.SetNumberOfLabels(self.ui.num_contour.value())

        sb_actor.SetLookupTable(self.mesh_lut)
        sb_actor.SetTitle('MPa')


        #attempt to change scalebar properties [ineffective]
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
        sb_actor.GetLabelTextProperty().SetColor(0,0,0)
        sb_actor.GetTitleTextProperty().SetColor(0,0,0)
        sb_actor.GetLabelTextProperty().SetFontSize(1)
        sb_actor.GetTitleTextProperty().SetFontSize(1)
        sb_actor.SetLabelFormat("%.1f")

        self.ren.AddActor(mesh_actor)
        self.ren.AddActor(sb_actor)
        self.axis_actor = generate_axis_actor(self.vtu_output,self.ren)
        self.ren.AddActor(self.axis_actor)
        
        scalar_bar_widget.SetInteractor(self.iren)
        scalar_bar_widget.On()
        self.ren.ResetCamera()
        
        self.ui.vtkWidget.update()
        QtWidgets.QApplication.processEvents()

    def extract(self):
        '''
        Get points from ui, call line_query and plot data on matplotlib canvas
        '''
        if not hasattr(self,'vtu_output'):
            return
        
        p1 = [self.ui.point1_x_coord.value(), self.ui.point1_y_coord.value(), self.ui.point1_z_coord.value()]
        p2 = [self.ui.point2_x_coord.value(), self.ui.point2_y_coord.value(), self.ui.point2_z_coord.value()]
        self.q = line_query(self.vtu_output,p1,p2,self.ui.extract_interval.value(),self.component)
        self.x = range(len(self.q))
        self.ui.figure.clear()
        QtWidgets.QApplication.processEvents()
        ax = self.ui.figure.add_subplot(111)
        ax.scatter(self.x,self.q)
        ax.set_ylabel("%s (MPa)"%self.component)
        ax.set_xlabel("Point number")
        ax.grid(b=True, which='major', color='#666666', linestyle='-')
        ax.minorticks_on()
        ax.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        self.ui.figure.tight_layout()
        self.ui.canvas.draw()
        
        #remove any line actor currently present
        if hasattr(self,'line_actor'):
            self.ren.RemoveActor(self.line_actor)
        self.ui.vtkWidget.update()
        
        #draw a line on the interactor
        line = vtk.vtkLineSource()
        line.SetResolution(self.ui.extract_interval.value())
        line.SetPoint1(p1)
        line.SetPoint2(p2)
        line.Update()
        
        sphere1 = vtk.vtkSphereSource()
        sphere1.SetCenter(p1)
        sphere1.Update()
        
        sphere2 = vtk.vtkSphereSource()
        sphere2.SetCenter(p2)
        sphere2.Update()
        
        appendFilter = vtk.vtkAppendPolyData()
        appendFilter.AddInputData(sphere1.GetOutput())
        appendFilter.AddInputData(line.GetOutput())
        appendFilter.AddInputData(sphere2.GetOutput())
        appendFilter.Update()
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(appendFilter.GetOutput())
        self.line_actor = vtk.vtkActor()
        self.line_actor.SetMapper(mapper)
        colors = vtk.vtkNamedColors()
        self.line_actor.GetProperty().SetColor(colors.GetColor3d("Violet"))
        self.ren.AddActor(self.line_actor)
        self.ui.export_button.setEnabled(True)
        
        self.ui.vtkWidget.update()
        
    def export(self):
        """
        Collects data from ui, writes to a valid file
        """
        
        fileo, _ = get_save_file('*.csv')
        if fileo is None:
            return
        
        np.savetxt(fileo,
        np.column_stack((self.x,self.q)), 
        delimiter=',',
        header = "%s\nPoint number, %s (MPa)"%(self.active_vtu,self.component))

    def load_vtu(self):
        """
        Method to return a valid vtu file
        """
        
        filep,startdir=get_file('*.vtu')
        if filep is None:
            return
        if not(os.path.isfile(filep)):
            print('Data file invalid.')
            return
        
        self.active_vtu = filep
        self.ui.load_label.setText(filep)
        #call draw_model
        self.ui.component_cb.setEnabled(True)
        self.draw_model()
        self.info_actor = generate_info_actor(self.ren,'Loaded model from VTU file.')
            
    def load_h5(self):
        
        if self.file is None:
            self.file, _ = get_file("*.OpenRS")
        
        if self.file is not None:
            #check the file has a populated model object
            with h5py.File(self.file, 'r') as f:
                if "model/piece0" not in f:
                    self.info_actor = generate_info_actor(self.ren,'Model data could not be loaded.')
                    return
        
        #otherwise read it
        r = HDF5vtkug_reader()
        r.SetFileName(self.file)
        r.Update()
        self.active_vtu = r.GetOutputDataObject(0).GetBlock(0)
        self.ui.load_label.setText(self.file)
        #call draw_model
        self.ui.component_cb.setEnabled(True)
        self.draw_model()
        self.info_actor = generate_info_actor(self.ren,'Loaded model from data file.')
                

    def keypress(self, obj, event):
        '''
        VTK interactor-specific listener for keypresses
        '''
        key = obj.GetKeySym()
        
        if key =="1":
            xyview(self.ren)
        elif key =="2":
            yzview(self.ren)
        elif key =="3":
            xzview(self.ren)
        elif key == "Up":
            self.ren.GetActiveCamera().Roll(30)
        elif key == "Down":
            self.ren.GetActiveCamera().Roll(-30)
        elif key == "w": #debug
            self.write_h5()
        elif key == "l": #debug
            self.load_h5()

        elif key=="i":
            im = vtk.vtkWindowToImageFilter()
            writer = vtk.vtkPNGWriter()
            colors = vtk.vtkNamedColors()
            self.ren.SetBackground(colors.GetColor3d("white"))
            im.SetInput(self.ui.vtkWidget._RenderWindow)
            im.Update()
            writer.SetInputConnection(im.GetOutputPort())
            writer.SetFileName("OpenRS_capture.png")
            writer.Write()
            self.ren.SetBackground(colors.GetColor3d("aliceblue"))
            self.info_actor = generate_info_actor(self.ren,'Image saved.')
        
        elif key=="r":
            flip_visible(self.axis_actor)
        
        self.ren.ResetCamera()
        self.ui.vtkWidget.update()

    def on_mouse_move(self, obj, event):
        if hasattr(self,'info_actor'):
            self.ren.RemoveActor(self.info_actor)
        else:
            pass

def read_model_data(vtu, component, lut, range):
    '''
    Read an unstructured grid from an XML formated vtu file, or operate on a ug object, setting the output to be a 'component'. If not specified, generate a lookup table and range based on the specified component, otherwise, use the lookup table specified with the given range.
    '''
    #If read is true, then vtuname is a VTU file
    if type(vtu) is str:
        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(vtu)
        reader.Update()
        output = reader.GetOutput()
    else: #coming from hdf5reader
        output = vtu
        
    output.GetPointData().SetActiveScalars(component)
    
    if lut is None or range is None:
        #build lookup table according to field
        lut = vtk.vtkLookupTable()
        lut.SetHueRange(0.667, 0)
        lut.Build()
        range = output.GetScalarRange()
    

    # map data set
    mesh_mapper = vtk.vtkDataSetMapper()
    mesh_mapper.SetInputData(output)
    mesh_mapper.SetScalarRange(range)
    mesh_mapper.SetLookupTable(lut)


    # Create the Actor
    actor = vtk.vtkActor()
    actor.SetMapper(mesh_mapper)
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetLineWidth(0)

    return actor, output, lut, range

if __name__ == "__main__":
    if len(sys.argv)>1:
        launch(sys.argv[1])
    else:
        launch()