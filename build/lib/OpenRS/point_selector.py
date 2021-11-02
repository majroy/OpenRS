#!/usr/bin/env python
'''
Qt and VTK application to allow for viewing and querying positions to measure residual stress within the context of diffraction.
-------------------------------------------------------------------------------
0.1 - Inital release
'''

import sys, os
import numpy as np
import vtk
from vtk.util import numpy_support as nps
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from OpenRS.open_rs_common import get_file, get_save_file, generate_sphere, generate_axis_actor, generate_point_actor, generate_info_actor, xyview, yzview, xzview, flip_visible, make_logo, table_model
from OpenRS.sgv import sgv_viewer, draw_sgv
from OpenRS.open_rs_hdf5_io import *

__author__ = "M.J. Roy"
__version__ = "0.1"
__email__ = "matthew.roy@manchester.ac.uk"
__status__ = "Experimental"
__copyright__ = "(c) M. J. Roy, 2021-"

def launch(*args, **kwargs):
    '''
    Start Qt/VTK interaction.
    '''
    
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    app.processEvents()
    
    window = interactor(None) #otherwise specify parent widget
    window.show()
    window.iren.Initialize()

    app.exec_()
    
    if sys.stdin.isatty() and not hasattr(sys, 'ps1'):
        sys.exit()
        window.closeEvent()
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
        MainWindow.setWindowTitle("OpenRS - point selector v%s" %__version__)
        
        #create new layout to hold both VTK and Qt interactors
        mainlayout=QtWidgets.QHBoxLayout(self.centralWidget)
        
        #set headings font
        headFont=QtGui.QFont("Helvetica [Cronyx]",weight=QtGui.QFont.Bold)
        
        #make divisors
        frame_style = QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken
        horizLine1=QtWidgets.QFrame()
        horizLine1.setFrameStyle(frame_style)
        horizLine2=QtWidgets.QFrame()
        horizLine2.setFrameStyle(frame_style)
        
        #make upper layout
        geo_button_layout = QtWidgets.QGridLayout()
        load_stl_label = QtWidgets.QLabel("Display")
        load_stl_label.setFont(headFont)
        self.load_stl_button = QtWidgets.QPushButton('Load')
        self.load_label = QtWidgets.QLabel("Nothing loaded.")
        self.load_label.setWordWrap(True)
        op_slider_label = QtWidgets.QLabel("Set geometry opacity:")
        self.op_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.op_slider.setRange(0,100)
        self.op_slider.setSliderPosition(50)
        geo_button_layout.addWidget(load_stl_label,0,0,1,1)
        geo_button_layout.addWidget(self.load_stl_button,0,1,1,1)
        geo_button_layout.addWidget(self.load_label,1,0,1,2)
        geo_button_layout.addWidget(op_slider_label,2,0,1,1)
        geo_button_layout.addWidget(self.op_slider,2,1,1,1)
        
        #make button group for translation of STL origin
        translate_label = QtWidgets.QLabel("Translate origin:")
        translate_label.setFont(headFont)
        
        #right hand button group
        self.choose_vertex_button = QtWidgets.QPushButton('Vertex')
        self.choose_vertex_button.setEnabled(False)
        self.choose_vertex_button.setCheckable(True)
        self.choose_vertex_button.setToolTip("Press 'R' to select")
        self.trans_reset_button = QtWidgets.QPushButton('Reset')
        self.trans_reset_button.setEnabled(False)
        self.trans_origin_button = QtWidgets.QPushButton('Update')
        self.trans_origin_button.setEnabled(False)
        
        translate_x_label =QtWidgets.QLabel("X")
        self.translate_x = QtWidgets.QDoubleSpinBox()
        self.translate_x.setMinimum(-1000)
        self.translate_x.setValue(0)
        self.translate_x.setMaximum(1000)
        
        translate_y_label =QtWidgets.QLabel("Y")
        self.translate_y = QtWidgets.QDoubleSpinBox()
        self.translate_y.setMinimum(-1000)
        self.translate_y.setValue(0)
        self.translate_y.setMaximum(1000)
        
        translate_z_label =QtWidgets.QLabel("Z")
        self.translate_z = QtWidgets.QDoubleSpinBox()
        self.translate_z.setMinimum(-1000)
        self.translate_z.setValue(0)
        self.translate_z.setMaximum(1000)

        #make button group for STL origin rotation
        rotation_label = QtWidgets.QLabel("Rotate origin about:")
        rotation_label.setFont(headFont)
        xlabel = QtWidgets.QLabel("X (deg)")
        self.rotate_x = QtWidgets.QDoubleSpinBox()
        self.rotate_x.setSingleStep(15)
        self.rotate_x.setMinimum(-345)
        self.rotate_x.setValue(0)
        self.rotate_x.setMaximum(345)
        ylabel = QtWidgets.QLabel("Y (deg)")
        self.rotate_y = QtWidgets.QDoubleSpinBox()
        self.rotate_y.setSingleStep(15)
        self.rotate_y.setMinimum(-345)
        self.rotate_y.setValue(0)
        self.rotate_y.setMaximum(345)
        zlabel = QtWidgets.QLabel("Z (deg)")
        self.rotate_z = QtWidgets.QDoubleSpinBox()
        self.rotate_z.setSingleStep(15)
        self.rotate_z.setMinimum(-345)
        self.rotate_z.setValue(0)
        self.rotate_z.setMaximum(345)

        #transform origin button layout
        trans_origin_layout = QtWidgets.QGridLayout()
        trans_origin_layout.addWidget(translate_label,0,0,1,2)
        trans_origin_layout.addWidget(rotation_label,0,2,1,2)
        trans_origin_layout.addWidget(translate_x_label,1,0,1,1)
        trans_origin_layout.addWidget(self.translate_x,1,1,1,1)
        trans_origin_layout.addWidget(xlabel,1,2,1,1)
        trans_origin_layout.addWidget(self.rotate_x,1,3,1,1)
        trans_origin_layout.addWidget(self.trans_reset_button,1,4,1,1)
        
        trans_origin_layout.addWidget(translate_y_label,2,0,1,1)
        trans_origin_layout.addWidget(self.translate_y,2,1,1,1)
        trans_origin_layout.addWidget(ylabel,2,2,1,1)
        trans_origin_layout.addWidget(self.rotate_y,2,3,1,1)
        trans_origin_layout.addWidget(self.choose_vertex_button,2,4,1,1)
        
        trans_origin_layout.addWidget(translate_z_label,3,0,1,1)
        trans_origin_layout.addWidget(self.translate_z,3,1,1,1)
        trans_origin_layout.addWidget(zlabel,3,2,1,1)
        trans_origin_layout.addWidget(self.rotate_z,3,3,1,1)
        trans_origin_layout.addWidget(self.trans_origin_button,3,4,1,1)
        
        #make lower button layout
        draw_button_layout = QtWidgets.QGridLayout()
        self.draw_button = QtWidgets.QPushButton('Draw')
        self.draw_button.setEnabled(False)
        draw_button_layout.addWidget(self.draw_button,0,0,1,1)
        
        #make side panel layout
        lvlayout=QtWidgets.QVBoxLayout()

        #create VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(100)
        sizePolicy.setVerticalStretch(100)
        self.vtkWidget.setSizePolicy(sizePolicy)
        
        self.vtkWidget.setMinimumSize(QtCore.QSize(800, 600))

        lvlayout.addLayout(geo_button_layout)
        lvlayout.addWidget(horizLine1)
        lvlayout.addLayout(trans_origin_layout)
        lvlayout.addWidget(horizLine2)
        lvlayout.addWidget(self.make_table_layout())
        lvlayout.addWidget(self.draw_button)
        lvlayout.addLayout(draw_button_layout)
        lvlayout.addStretch(1)
        
        mainlayout.addWidget(self.vtkWidget)
        mainlayout.addStretch(1)
        mainlayout.addLayout(lvlayout)
        
    def make_table_layout(self):

        self.mtable = QtWidgets.QTableView()
        self.mtable.setSelectionBehavior(QtWidgets.QTableView().SelectRows)
        self.ftable = QtWidgets.QTableView()
        self.ftable.setSelectionBehavior(QtWidgets.QTableView().SelectRows)

        #default table entries
        self.mdata = [[0,0,0]]
        self.fdata = [[0,0,0]]
        
        self.mmodel = table_model(self.mdata,['X','Y','Z'])
        self.mtable.setModel(self.mmodel)
        self.fmodel = table_model(self.fdata,['X','Y','Z'])
        self.ftable.setModel(self.fmodel)
        
        #make toolbars
        self.meas_insertaction = QtWidgets.QAction("Insert")
        self.meas_deletedaction = QtWidgets.QAction("Delete")
        self.meas_loadaction = QtWidgets.QAction("Load")
        self.meas_saveaction = QtWidgets.QAction("Export")
        self.fid_insertaction = QtWidgets.QAction("Insert")
        self.fid_deletedaction = QtWidgets.QAction("Delete")
        self.fid_loadaction = QtWidgets.QAction("Load")
        self.fid_saveaction = QtWidgets.QAction("Export")
        meas_toolbar = QtWidgets.QToolBar("Edit")
        meas_toolbar.addAction(self.meas_insertaction)
        meas_toolbar.addSeparator()
        meas_toolbar.addAction(self.meas_deletedaction)
        meas_toolbar.addSeparator()
        meas_toolbar.addAction(self.meas_loadaction)
        meas_toolbar.addSeparator()
        meas_toolbar.addAction(self.meas_saveaction)
        fid_toolbar = QtWidgets.QToolBar("Edit")
        fid_toolbar.addAction(self.fid_insertaction)
        fid_toolbar.addSeparator()
        fid_toolbar.addAction(self.fid_deletedaction)
        fid_toolbar.addSeparator()
        fid_toolbar.addAction(self.fid_loadaction)
        fid_toolbar.addSeparator()
        fid_toolbar.addAction(self.fid_saveaction)
        
        #create layout and add to window
        slvlayout=QtWidgets.QVBoxLayout()
        mlvlayout=QtWidgets.QVBoxLayout()
        flvlayout=QtWidgets.QVBoxLayout()
        
        mlvlayout.setMenuBar(meas_toolbar)
        mlvlayout.addWidget(self.mtable)
        flvlayout.setMenuBar(fid_toolbar)
        flvlayout.addWidget(self.ftable)

        self.tabwidget = QtWidgets.QTabWidget()
        self.tabwidget.setMinimumSize(QtCore.QSize(400, 500))
        
        sgv_tab = QtWidgets.QWidget(self.tabwidget)
        meas_tab = QtWidgets.QWidget(self.tabwidget)
        fid_tab = QtWidgets.QWidget(self.tabwidget)
        self.tabwidget.addTab(sgv_tab,'Define SGV')
        self.tabwidget.addTab(meas_tab,'Measurement')
        self.tabwidget.addTab(fid_tab,'Fiducial')
        self.sgv = sgv_viewer(self.tabwidget)
        slvlayout.addWidget(self.sgv)
        sgv_tab.setLayout(slvlayout)
        meas_tab.setLayout(mlvlayout)
        fid_tab.setLayout(flvlayout)
        
        #connect buttons
        self.meas_deletedaction.triggered.connect(self.delete_row)
        self.meas_insertaction.triggered.connect(self.insert_row)
        self.meas_loadaction.triggered.connect(self.get_point_data)
        self.meas_saveaction.triggered.connect(self.grab)

        self.fid_deletedaction.triggered.connect(self.delete_row)
        self.fid_insertaction.triggered.connect(self.insert_row)
        self.fid_loadaction.triggered.connect(self.get_point_data)
        self.fid_saveaction.triggered.connect(self.grab)
        
        return self.tabwidget

    def get_point_data(self):
        '''
        Populates measurement and fiducial points from external file
        '''
        # if there's a file, with conditioning to make sure that the lists generated are the right dimension before sending to Tablemodel
        
        filep, _ = get_file('*.txt')
        if filep is None:
            return
        if not(os.path.isfile(filep)):
            print('Data file invalid.')
            return

        if self.tabwidget.currentIndex() == 1:
            #delete the relevant table_model as opposed to working on repopulating with insertRows
            del self.mmodel
            self.mdata = np.genfromtxt(filep)
            if len(self.mdata.shape) > 1:
                self.mdata = self.mdata.tolist()
            else:
                self.mdata = [self.mdata.tolist()]

            self.mmodel = table_model(self.mdata,['X','Y','Z'])
            self.mtable.setModel(self.mmodel)

        if self.tabwidget.currentIndex() == 2:
            del self.fmodel
            self.fdata = np.genfromtxt(filep)
            if len(self.fdata.shape) > 1:
                self.fdata = self.fdata.tolist()
            else:
                self.fdata = [self.fdata.tolist()]
            self.fmodel = table_model(self.fdata,['X','Y','Z'])
            self.ftable.setModel(self.fmodel)
    def insert_row(self):
        '''
        inserts a row at a selected row from the table, or at the end if not
        '''
        #Add rows to table depending on what tab is selected
        if self.tabwidget.currentIndex() == 1:
            index = self.mtable.currentIndex()
            if index.row() > -1:
                self.mmodel.insertRows(index.row(),1,index, None)
            else: #add row to end
                self.mdata.append([0,0,0])
                self.mtable.model().layoutChanged.emit()
        elif self.tabwidget.currentIndex() == 2:
            index = self.ftable.currentIndex()
            if index.row() > -1:
                self.fmodel.insertRows(index.row(),1,index, None)
            else: #add row to end
                self.fdata.append([0,0,0])
                self.ftable.model().layoutChanged.emit()
                
    def delete_row(self):
        '''
        deletes a selected row from the table
        '''
        #Add rows to table depending on what tab is selected
        if self.tabwidget.currentIndex() == 1:
            index = self.mtable.currentIndex()
            self.mmodel.removeRows(index.row(),1,index)
        elif self.tabwidget.currentIndex() == 2:
            index = self.ftable.currentIndex()
            self.fmodel.removeRows(index.row(),1,index)


    def grab(self):
        '''
        Based on selected tab, migrates data from Qt to csv file
        '''
        fileo, _ = get_save_file('*.txt')
        if fileo is None:
            return
            
        if self.tabwidget.currentIndex() == 1:
            model = self.mmodel

        elif self.tabwidget.currentIndex() == 2:
            model =self.fmodel
            
        else: return
        nrows = model.rowCount(0)
        ncols = model.columnCount(0)
        update_data=np.empty([nrows,ncols])
        for i in range(nrows):
            for j in range(ncols):
                update_data[i,j]=model.getCellData([i,j])
        np.savetxt(fileo,update_data)
        return update_data, self.tabwidget.currentIndex()

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
        self.iren.AddObserver("KeyPressEvent", self.keypress)
        self.iren.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.ren.GetActiveCamera().ParallelProjectionOn()
        
        self.file = None #overwritten at launch
        make_logo(self.ren)
        
        #connect buttons
        self.ui.tabwidget.currentChanged.connect(self.check_draw)
        self.ui.load_stl_button.clicked.connect(self.load_stl)
        self.ui.op_slider.valueChanged[int].connect(self.change_opacity)
        self.ui.draw_button.clicked.connect(self.draw_pnts)
        self.ui.trans_origin_button.clicked.connect(self.transform_origin)
        self.ui.choose_vertex_button.clicked.connect(self.vertex_select)
        self.ui.trans_reset_button.clicked.connect(self.redraw)
    
    def check_draw(self):
        '''
        Sets the availability of drawing SGVs on basis of whether they have been finalized in the SGV ui.
        '''
        if self.ui.tabwidget.currentIndex() == 0:
            self.ui.draw_button.setEnabled(False)
        elif self.ui.tabwidget.currentIndex() == 1 and self.ui.sgv.finalized:
            self.ui.draw_button.setEnabled(True)
        elif self.ui.tabwidget.currentIndex() == 1:
            self.ui.draw_button.setEnabled(False)
        elif self.ui.tabwidget.currentIndex() == 2:
            self.ui.draw_button.setEnabled(True)
    
    def redraw(self):
        '''
        Resets/initialises the transformation by clearing all actors, changing the transformation matrix back to the identity.
        '''
        self.ren.RemoveAllViewProps()

        self.trans = vtk.vtkMatrix4x4()
        self.trans.Identity()
        
        #reset ui/load from file
        self.ui.translate_x.setValue(0)
        self.ui.translate_y.setValue(0)
        self.ui.translate_z.setValue(0)
        self.ui.rotate_x.setValue(0)
        self.ui.rotate_y.setValue(0)
        self.ui.rotate_z.setValue(0)
        
        #regenerate stl_actor from np data
        polydata = vtk.vtkPolyData()
        points = vtk.vtkPoints()
        points.SetData(nps.numpy_to_vtk(self.np_pts))
        cells = vtk.vtkCellArray()
        cells.SetCells(0, nps.numpy_to_vtkIdTypeArray(self.np_verts))
        
        polydata.SetPoints(points)
        polydata.SetPolys(cells)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)

        self.stl_actor = vtk.vtkActor()
        self.stl_actor.SetMapper(mapper)
        self.stl_actor.GetProperty().SetOpacity(0.5)
        self.stl_actor.PickableOff()
        self.stl_actor.GetProperty().SetColor(vtk.vtkNamedColors().GetColor3d('Gray'))
        
        #regenerate vertex data, origin actor and box axis
        self.vertex_actor, self.vertex_polydata = generate_point_actor( \
        self.np_pts, \
        vtk.vtkNamedColors().GetColor3d("violet"), \
        5)
        self.vertex_actor.SetVisibility(False)
        self.origin_actor = vtk.vtkAxesActor()
        #change scale of origin on basis of size of stl_actor
        origin_scale = np.max(self.stl_actor.GetBounds())/16
        self.origin_actor.SetTotalLength(origin_scale,origin_scale,origin_scale)
        self.origin_actor.SetNormalizedShaftLength(1,1,1)
        self.origin_actor.SetNormalizedTipLength(0.2,0.2,0.2)
        
        self.origin_actor.GetXAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
        self.origin_actor.GetYAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
        self.origin_actor.GetZAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
        
        
        self.ren.AddActor(self.stl_actor)
        self.ren.AddActor(self.vertex_actor)
        self.ren.AddActor(self.origin_actor)
        
        #redraw box axis
        self.axis_actor = generate_axis_actor(self.stl_actor,self.ren)
        self.ren.AddActor(self.axis_actor)
        
        self.ui.choose_vertex_button.setEnabled(True)
        self.ui.choose_vertex_button.setChecked(False)

        self.ren.ResetCamera()
        self.ui.vtkWidget.update()
        self.ui.vtkWidget.setFocus()
    
    def load_stl(self):
        '''
        Loads/reads stl file, returns an actor for the stl file, as well as points and polygons which can be saved and used to build a polydata object later.
        '''
        filep,startdir=get_file('*.stl')
        
        if filep is None:
            return
        if not(os.path.isfile(filep)):
            print('Data file invalid.')
            return
        
        reader = vtk.vtkSTLReader()
        reader.SetFileName(filep)
        reader.Update()
        
        self.stl_polydata = reader.GetOutput()
        self.np_pts = nps.vtk_to_numpy(self.stl_polydata.GetPoints().GetData())
        self.np_verts = nps.vtk_to_numpy(self.stl_polydata.GetPolys().GetData())
        self.ui.choose_vertex_button.setEnabled(True)
        self.ui.trans_reset_button.setEnabled(True)
        self.ui.trans_origin_button.setEnabled(True)
        
        self.c_trans = np.eye(4)
        self.ui.load_label.setText(filep)
        self.redraw()
        

    def apply_transform(self):
        '''
        As underlying sources of the stl file and vertices cannot be transformed without affecting vertex_select (actors are updated, but not pickable vertices)
        '''
        
        #get homogeneous numpy tranformation matrix
        T = vtkmatrix_to_numpy(self.trans)
        #apply to np arrays which make up vertex and stl objects
        self.np_pts = np.dot(self.np_pts,T[0:3,0:3])+T[0:3,-1]
        
        self.c_trans = T @ self.c_trans #for a unique, traceable transformation matrix from the originating STL file.
        self.redraw()


    def vertex_select(self):
        if self.ui.choose_vertex_button.isChecked():
            self.vertex_actor.SetVisibility(True)
            self.iren.SetInteractorStyle(vtk.vtkInteractorStyleRubberBandPick())
            picker = vtk.vtkAreaPicker()
            self.iren.SetPicker(picker)
            picker.AddObserver("EndPickEvent", self.picker_callback)
            self.ui.trans_origin_button.setEnabled(False)
            self.ui.vtkWidget.setFocus()
            self.ui.vtkWidget.update()
        else:
            self.ui.trans_origin_button.setEnabled(False)
            self.vertex_actor.SetVisibility(False)
            self.ui.trans_origin_button.setEnabled(True)
            self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
            self.transform_origin()
            self.ui.vtkWidget.update()

    def picker_callback(self, object, event):
        
        n_color = [int(i*255) for i in vtk.vtkNamedColors().GetColor3d("violet")]
        h_color = [int(i*255) for i in vtk.vtkNamedColors().GetColor3d("tomato")]
        selected_frustrum = vtk.vtkExtractSelectedFrustum()
        selected_frustrum.SetFrustum(object.GetFrustum())
        selected_frustrum.SetInputData(self.vertex_polydata)
        selected_frustrum.Update()
        selected = selected_frustrum.GetOutput()
        
        id = vtk.vtkIdTypeArray()
        id = selected.GetPointData().GetArray("vtkOriginalPointIds")
        if id and id.GetSize() > 0:
            #reset color array to original
            colors=vtk.vtkUnsignedCharArray()
            colors.SetNumberOfComponents(3)
            vertices = self.vertex_polydata.GetPointData().GetNumberOfTuples()
            for j in range(vertices):
                colors.InsertNextTuple(n_color)
            #set the specific one chosen (or first in a batch) as 'the one'
            colors.SetTuple(id.GetValue(0),h_color)
            self.vertex_polydata.GetPointData().SetScalars(colors)
            
            self.ui.vtkWidget.update()
            # update ui translation boxes
            local_vertices = nps.vtk_to_numpy(self.vertex_polydata.GetPoints().GetData())
            vt = local_vertices[id.GetValue(0),:]
            self.ui.translate_x.setValue(-vt[0])
            self.ui.translate_y.setValue(-vt[1])
            self.ui.translate_z.setValue(-vt[2])
            
            
    def change_opacity(self,value):
        if hasattr(self,'stl_actor'):
            self.stl_actor.GetProperty().SetOpacity(value/100)
        self.ui.vtkWidget.update()
        
    def draw_pnts(self):
        def gen_assembly(color):
            #return an assembly of SGV actors
            pnt_assembly = vtk.vtkAssembly()
            for pnt in a:
                pnt_assembly.AddPart(generate_sphere(pnt,1,color))
            pnt_assembly.SetOrigin(0,0,0)
            return pnt_assembly
        
        def gen_meas_point_assembly(color):
            sgv_assembly = vtk.vtkAssembly()
            w = self.ui.sgv.width.value()
            d = self.ui.sgv.depth.value()
            t = np.radians(self.ui.sgv.theta.value())
            trans = self.ui.sgv.trans
            for pnt in a:
                local_trans = trans
                local_trans[0:3,3] = pnt
                local_ugrid = draw_sgv(w, d, t, local_trans)
                mapper = vtk.vtkDataSetMapper()
                mapper.SetInputData(local_ugrid)
                local_actor = vtk.vtkActor()
                local_actor.SetMapper(mapper)
                local_actor.GetProperty().SetColor(color)
                # local_actor.GetProperty().SetOpacity(0.5)
                sgv_assembly.AddPart(local_actor)
            return sgv_assembly
        
        tab = self.ui.tabwidget.currentIndex()

        tab_models = [self.ui.mmodel, self.ui.fmodel] #both models into an array to parse
        tab_data = []
        ind = 0
        for model in tab_models:
            nrows = model.rowCount(0)
            ncols = model.columnCount(0)
            tab_data.append(np.empty([nrows,ncols]))
            for i in range(nrows):
                for j in range(ncols):
                    tab_data[ind][i,j]=model.getCellData([i,j])
            ind += 1

        a = tab_data[tab - 1]

        if tab == 1:
            if hasattr(self,'meas_pnt_assembly'):
                self.ren.RemoveActor(self.meas_pnt_assembly)
            color = vtk.vtkNamedColors().GetColor3d("salmon")
            self.meas_pnt_assembly = gen_meas_point_assembly(color)
            self.ren.AddActor(self.meas_pnt_assembly)
        elif tab == 2:
            if hasattr(self,'fid_pnt_assembly'):
                self.ren.RemoveActor(self.fid_pnt_assembly)
            color = vtk.vtkNamedColors().GetColor3d("green")
            self.fid_pnt_assembly = gen_assembly(color)
            self.ren.AddActor(self.fid_pnt_assembly)

        self.ren.ResetCamera()
        self.ui.vtkWidget.update()
        self.ui.vtkWidget.setFocus()

    def draw_all_points(self):
        '''
        Draws both sgvs and fiducial points using points currently in tabs
        '''
        c_tab = self.ui.tabwidget.currentIndex()
        
        for j in [1,2]:
            self.ui.tabwidget.setCurrentIndex(j)
            self.draw_pnts()
        
        self.ui.tabwidget.setCurrentIndex(c_tab)


    def transform_origin(self):
        '''
        -reads ui and generates transformation matrix
        -applies to ui by calling draw_stl
        -save to OpenRS data file
        '''
        
        x = self.ui.translate_x.value()
        y = self.ui.translate_y.value()
        z = self.ui.translate_z.value()
        ax = np.deg2rad(self.ui.rotate_x.value())
        Rx = np.array([[1,0,0],[0, np.cos(ax), -np.sin(ax)],[0, np.sin(ax), np.cos(ax)]])
        ay = np.deg2rad(self.ui.rotate_y.value())
        Ry = np.array([[np.cos(ay), 0, np.sin(ay)],[0,1,0],[-np.sin(ay), 0, np.cos(ay)]])
        az = np.deg2rad(self.ui.rotate_z.value())
        Rz = np.array([[np.cos(az), -np.sin(az), 0],[np.sin(az), np.cos(az), 0],[0,0,1]])
        R = Rx @ Ry @ Rz
        
        #numpy transformation matrix
        trans = np.identity(4)
        trans[0:3,0:3] = R
        trans[0:3,3] = [x,y,z]
        
        #update vtk transformation matrix with numpy
        for i in range(4):
            for j in range(4):
                self.trans.SetElement(i,j,trans[i,j])
                
        self.apply_transform()

    def closeEvent(self, event):
        self.ui.vtkWidget.close()
        self.ui.sgv.vtkWidget.close()

    def load_h5(self):
    
        if self.file is None:
            self.file, _ = get_file("*.OpenRS")
        
        if self.file is not None:
            #check if sample/points is empty
            with h5py.File(self.file, 'r') as f:
                if f['sample/points'].shape is None:
                    self.info_actor = generate_info_actor(self.ren,'Point data could not be loaded.')
                    return
        
        #otherwise read it
        with h5py.File(self.file, 'r') as f:
            self.np_pts = f['sample/points'][()]
            self.np_verts = f['sample/vertices'][()]
            self.c_trans = f['sample/transform'][()]
            
            #do fiducials and measurement points
            del self.ui.mmodel
            del self.ui.fmodel
            self.ui.mdata = f['measurement_points/points'][()].tolist()
            self.ui.fdata = f['fiducials/points'][()].tolist()
            self.ui.mmodel = table_model(self.ui.mdata,['X','Y','Z'])
            self.ui.mtable.setModel(self.ui.mmodel)
            self.ui.fmodel = table_model(self.ui.fdata,['X','Y','Z'])
            self.ui.ftable.setModel(self.ui.fmodel)
            
            self.ui.sgv.width.setValue(f['sgv'].attrs['width'])
            self.ui.sgv.depth.setValue(f['sgv'].attrs['depth'])
            self.ui.sgv.theta.setValue(f['sgv'].attrs['2theta'])
            self.ui.sgv.rotate_x.setValue(f['sgv'].attrs['rotate_x'])
            self.ui.sgv.rotate_y.setValue(f['sgv'].attrs['rotate_y'])
            self.ui.sgv.rotate_z.setValue(f['sgv'].attrs['rotate_z'])
        self.redraw() #draws stl/sample
        self.draw_all_points() #draws meas & fiducial
        self.info_actor = generate_info_actor(self.ren,'Loaded model from data file.')
            
    def write_h5(self):
        '''
        method which writes to an hdf5 file if there is any sample data available.
        '''
        #has read an STL file
        if not hasattr(self,'np_pts'):
            return
        
        if self.file is None:
            self.file = initialize_HDF5()
        
        
        #itinerary from this interactor is:
        #stl data
        #stl user-defined transform
        #measurement points
        #fiducial points
        #sgv values: width, depth, 2theta, rotations
        tab_models = [self.ui.mmodel, self.ui.fmodel] #both models into an array to parse
        tab_data = []
        ind = 0
        for model in tab_models:
            nrows = model.rowCount(0)
            ncols = model.columnCount(0)
            tab_data.append(np.empty([nrows,ncols]))
            for i in range(nrows):
                for j in range(ncols):
                    tab_data[ind][i,j]=model.getCellData([i,j])
            ind += 1
        
        #finalize sgv
        self.ui.sgv.finalize()

        with h5py.File(self.file, 'r+') as f:
            #delete anything that could have been resized
            del f['sample/points']
            del f['sample/vertices']
            del f['sample/transform']
            del f['measurement_points/points']
            del f['fiducials/points']
            f.create_dataset('sample/points', data=self.np_pts)
            f.create_dataset('sample/vertices', data=self.np_verts)
            f.create_dataset('sample/transform', data=self.c_trans)
            f.create_dataset('measurement_points/points', data=tab_data[0])
            f.create_dataset('fiducials/points', data=tab_data[1])
            for k in self.ui.sgv.params.keys():
                f['sgv'].attrs[k] = self.ui.sgv.params[k]
            f.attrs['date_modified'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            self.info_actor = generate_info_actor(self.ren,'Saved to data file.')


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

def vtkmatrix_to_numpy(matrix):
    """
    Copies the elements of a vtkMatrix4x4 into a numpy array.

    :param matrix: The matrix to be copied into an array.
    :type matrix: vtk.vtkMatrix4x4
    :rtype: numpy.ndarray
    """
    m = np.ones((4, 4))
    for i in range(4):
        for j in range(4):
            m[i, j] = matrix.GetElement(i, j)
    return m

def numpy_to_vtkmatrix(matrix):
    """
    Copies the elements of a vtkMatrix4x4 into a numpy array.

    :param matrix: The matrix to be copied into an array.
    :type matrix: vtk.vtkMatrix4x4
    :rtype: numpy.ndarray
    """
    m = vtk.vtkMatrix4x4()
    m.DeepCopy(matrix.ravel(), m)
    return m


if __name__ == "__main__":
    launch()

