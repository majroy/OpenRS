import os, sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import QtGui, QtWidgets, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

vtuname1 = r'examples\U_elastic_run.vtu'
vtuname2 = r'examples\U_elastic_run_ccx.vtu'

def launch(*args, **kwargs):
    '''
    Start Qt/VTK interaction.
    '''
    
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    app.processEvents()
    
    window = interactor(None)
    window.active_vtu = vtuname1
    window.show()
    window.iren.Initialize()
    
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
        
        #create new layout to hold both VTK and Qt interactors
        self.mainlayout=QtWidgets.QGridLayout(self.centralWidget)

        #create VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        
        #create Qt layout to contain interactions
        main_ui_box = QtWidgets.QGridLayout()
        
        self.vtkWidget.setMinimumSize(QtCore.QSize(800, 600))
        
        #buttons
        self.display_button11 = QtWidgets.QPushButton('S11/Sxx')
        self.display_button22 = QtWidgets.QPushButton('S22/Syy')
        self.display_button33 = QtWidgets.QPushButton('S33/Szz')
        
        # line extraction from surface
        extractBox = QtWidgets.QGridLayout()
        extract_data_label = QtWidgets.QLabel("Extract")
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
        point2_z_label = QtWidgets.QLabel("z0:")
        self.point2_z_coord = QtWidgets.QDoubleSpinBox()
        self.point2_z_coord.setMinimum(-100000)
        self.point2_z_coord.setMaximum(100000)
        
        interval_label=QtWidgets.QLabel("Interval:")
        self.extract_interval=QtWidgets.QSpinBox()
        self.extract_interval.setValue(50)
        self.extract_interval.setMinimum(3)
        self.extract_interval.setMaximum(1000)
        
        self.extract_button = QtWidgets.QPushButton('Extract')
        self.export_button = QtWidgets.QPushButton('Export')
        self.export_button.setEnabled(False)
        
        
        main_ui_box.addWidget(self.display_button11,0,0,1,1)
        main_ui_box.addWidget(self.display_button22,0,1,1,1)
        main_ui_box.addWidget(self.display_button33,0,2,1,1)
        main_ui_box.addLayout(extractBox,1,0,1,3)
        
        extractBox.addWidget(extract_data_label,0,0,1,6)
        extractBox.addWidget(point1_x_label,1,0,1,1)
        extractBox.addWidget(self.point1_x_coord,1,1,1,1)
        extractBox.addWidget(point1_y_label,1,2,1,1)
        extractBox.addWidget(self.point1_y_coord,1,3,1,1)
        extractBox.addWidget(point1_z_label,1,4,1,1)
        extractBox.addWidget(self.point1_z_coord,1,5,1,1)
        extractBox.addWidget(point2_x_label,2,0,1,1)
        extractBox.addWidget(self.point2_x_coord,2,1,1,1)
        extractBox.addWidget(point2_y_label,2,2,1,1)
        extractBox.addWidget(self.point2_y_coord,2,3,1,1)
        extractBox.addWidget(point2_z_label,2,4,1,1)
        extractBox.addWidget(self.point2_z_coord,2,5,1,1)
        extractBox.addWidget(interval_label,3,0,1,1)
        extractBox.addWidget(self.extract_interval,3,1,1,1)
        extractBox.addWidget(self.extract_button,3,2,1,2)
        extractBox.addWidget(self.export_button,3,4,1,2)

        #plot
        self.figure = plt.figure(figsize=(4,4))
        self.figure.patch.set_facecolor((242/255,242/255,242/255))
        self.canvas = FigureCanvas(self.figure)

        lvlayout=QtWidgets.QVBoxLayout()
        lvlayout.addLayout(main_ui_box)
        lvlayout.addWidget(self.canvas)
        lvlayout.addStretch(1)
        
        self.mainlayout.addWidget(self.vtkWidget,0,0,1,1)
        self.mainlayout.addLayout(lvlayout,0,1,1,1)

        def initialize(self):
            self.vtkWidget.start()

class interactor(QtWidgets.QWidget):
    '''
    Inherits most properties from Qwidget, but starts the VTK window, and ties functions to interactors defined in main_window
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
        self.ren.GetActiveCamera().ParallelProjectionOn()
        self.ui.display_button11.clicked.connect(lambda: self.draw_model("S11"))
        self.ui.display_button22.clicked.connect(lambda: self.draw_model("S22"))
        self.ui.display_button33.clicked.connect(lambda: self.draw_model("S33"))
        self.ui.extract_button.clicked.connect(lambda: self.extract())
        self.ui.export_button.clicked.connect(lambda: self.export())

    def draw_model(self,component):
    
        #clear all actors
        self.ren.RemoveAllViewProps()
        
        result, self.output, mesh_lut, r = generate_model_data(self.active_vtu, component, None, None)
        
        #create scale bar
        scalar_bar_widget = vtk.vtkScalarBarWidget()
        sb_actor=scalar_bar_widget.GetScalarBarActor()
        sb_actor.SetLookupTable(mesh_lut)
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
        sb_actor.SetTitleTextProperty(propT);
        sb_actor.SetLabelTextProperty(propL);
        sb_actor.GetLabelTextProperty().SetFontSize(1)
        sb_actor.GetTitleTextProperty().SetFontSize(1)
        sb_actor.SetLabelFormat("%.1f")

        self.ren.AddActor(result)
        self.ren.AddActor(sb_actor)
        self.ren.AddActor(generate_axis_actor(self.output,self.ren))
        
        scalar_bar_widget.SetInteractor(self.iren)
        scalar_bar_widget.On()
        self.ren.ResetCamera()
        
        self.ui.vtkWidget.update()
        QtWidgets.QApplication.processEvents()

    def extract(self):
        '''
        Get points from ui, call line_query and plot data on matplotlib canvas
        '''
        p1 = [self.ui.point1_x_coord.value(), self.ui.point1_y_coord.value(), self.ui.point1_z_coord.value()]
        p2 = [self.ui.point2_x_coord.value(), self.ui.point2_y_coord.value(), self.ui.point2_z_coord.value()]
        self.q = line_query(self.output,p1,p2,self.ui.extract_interval.value())
        self.x = range(len(self.q))
        self.ui.figure.clear()
        ax = self.ui.figure.add_subplot(111)
        ax.scatter(self.x,self.q)
        ax.set_ylabel("MPa")
        ax.set_xlabel("Point number")
        ax.grid(b=True, which='major', color='#666666', linestyle='-')
        ax.minorticks_on()
        ax.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        self.ui.figure.tight_layout()
        self.ui.canvas.draw()
        
        self.ui.export_button.setEnabled(True)

    def export(self):
        """
        Collects data from ui, gets a valid file to write to.
        """
        
        fileo,startdir=get_save_file('*.csv',None)
        if fileo is None:
            return
        
        if fileo != None: #because filediag can be cancelled
            np.savetxt(fileo,
            np.column_stack((self.x,self.q)), 
            delimiter=',',
            header = "Point number, Stress (MPa)")

def generate_model_data(vtuname, component, lut, range):
    '''
    Read an unstructured grid from an XML formated vtu file, setting the output to be 'component'. If not specified, generate a lookup table and range based on the specified component, otherwise, use the lookup table specified with the given range.
    '''
    # Read the source file.
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(vtuname)
    reader.Update()
    output = reader.GetOutput()
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

def generate_axis_actor(output,ren):
    '''
    Generate a 3D axis based on the bounds of incoming 'output' and renderer
    '''

    ax3D = vtk.vtkCubeAxesActor()
    ax3D.ZAxisTickVisibilityOn()
    ax3D.SetXTitle('X')
    ax3D.SetYTitle('Y')
    ax3D.SetZTitle('Z')
    
    ax3D.GetTitleTextProperty(0).SetColor(0,0,0)
    ax3D.GetLabelTextProperty(0).SetColor(0,0,0)
    ax3D.GetXAxesLinesProperty().SetColor(0,0,0)

    ax3D.GetTitleTextProperty(1).SetColor(0,0,0)
    ax3D.GetLabelTextProperty(1).SetColor(0,0,0)
    ax3D.GetYAxesLinesProperty().SetColor(0,0,0)

    ax3D.GetTitleTextProperty(2).SetColor(0,0,0)
    ax3D.GetLabelTextProperty(2).SetColor(0,0,0)
    ax3D.GetZAxesLinesProperty().SetColor(0,0,0)
    
    ax3D.SetBounds(output.GetBounds())
    ax3D.SetCamera(ren.GetActiveCamera())
    return ax3D

def line_query(output,q1,q2,numPoints):
    """
    Interpolate the data from output over q1 to q2 (list of x,y,z)
    """
    # query_point = [[0,80,0],[0,70.2,0]]
    query_point = [q1,q2]
    line = vtk.vtkLineSource()
    line.SetResolution(numPoints)
    line.SetPoint1(q1)
    line.SetPoint2(q2)
    line.Update()

    probe = vtk.vtkProbeFilter()
    probe.SetInputConnection(line.GetOutputPort())
    probe.SetSourceData(output)

    probe.Update()

    # get the data from the VTK-object (probe) to an numpy array
    q = v2n(probe.GetOutput().GetPointData().GetArray('S11'))

    return q

def get_save_file(ext,outputd):
    '''
    Returns a the complete path to the file name with ext, starting in outputd. Checks extensions and if an extension is not imposed, it will write the appropriate extension based on ext.
    '''
    ftypeName={}
    ftypeName['*.csv']='OpenRS formatted output file'

    
    if outputd==None: id=str(os.getcwd())
    else: id=outputd
    lapp = QtWidgets.QApplication.instance()
    if lapp is None:
        lapp = QtWidgets.QApplication([])

    filer, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save as:", id,str(ftypeName[ext]+' ('+ext+')'))

    if filer == '':
        return None, None
    else:
        return filer, os.path.dirname(filer)


if __name__ == "__main__":
    if len(sys.argv)>1:
        launch(sys.argv[1])
    else:
        launch()