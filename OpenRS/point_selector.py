#!/usr/bin/env python
'''
Qt and VTK application to allow for viewing and querying positions to measure residual stress within the context of diffraction.
-------------------------------------------------------------------------------
0.1 - Inital release
'''

import sys, os
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n
from vtk.util.numpy_support import numpy_to_vtk as n2v
from vtk.util.numpy_support import numpy_to_vtkIdTypeArray as n2v_id
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from OpenRS.open_rs_common import get_file, get_save_file, generate_sphere, generate_axis_actor, generate_point_actor, generate_info_actor, xyview, yzview, xzview, flip_visible, make_logo, table_model, do_transform
from OpenRS.sgv import sgv_viewer, draw_sgv
from OpenRS.open_rs_hdf5_io import *
from OpenRS.transform_widget import make_transformation_button_layout, get_trans_from_euler_angles

__author__ = "M.J. Roy"
__version__ = "0.1"
__email__ = "matthew.roy@manchester.ac.uk"
__status__ = "Experimental"
__copyright__ = "(c) M. J. Roy, 2021-"

class launch(QtWidgets.QMainWindow):
    '''
    Start Qt/VTK interaction if started independently
    '''
    def __init__(self, parent=None):
        super(launch,self).__init__(parent)
        self.main_window = interactor(self)
        self.setCentralWidget(self.main_window)
        self.setWindowTitle("point selector widget v%s" %__version__)
        screen = QtWidgets.QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setMinimumSize(QtCore.QSize(int(2*rect.width()/3), int(2*rect.height()/3)))

class entry_combo_box(QtWidgets.QComboBox):
    '''
    Custom combo box allowing insertion, renaming and clearing of entries
    '''
    def __init__(self, *args, **kwargs):
        super(QtWidgets.QComboBox, self).__init__()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        size_policy = self.sizePolicy()
        size_policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        self.setSizePolicy(size_policy)
        self.customContextMenuRequested.connect(self.show_entry_menu)
        

    def show_entry_menu(self,pos):
        menu = QtWidgets.QMenu()
        rename_action = menu.addAction("Rename") 
        insert_action = menu.addAction("Insert")
        clear_action = menu.addAction("Clear")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == clear_action:
            self.clear_selection()
        if action == rename_action:
            self.rename_selection()
        if action == insert_action:
            self.insert_entry()
    
    @pyqtSlot(int)
    def on_clear_selection(self, value):
        pass
    
    def clear_selection(self):
        self.activated[int].connect(self.on_clear_selection)
        self.removeItem(self.currentIndex())
        
    
    def rename_selection(self):
        '''
        Sets up dialog with a line edit to change the entry.
        '''
        
        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        
        self.dlg = QtWidgets.QDialog(self)
        buttons = QtWidgets.QDialogButtonBox(QBtn)
        self.dlg.setWindowTitle('Rename entry')
        
        line_edit = QtWidgets.QLineEdit(self.currentText(), self)
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(buttons)
        self.dlg.setLayout(layout)
        buttons.accepted.connect(lambda: self.change_text(line_edit.text()))
        buttons.rejected.connect(self.close_dialog)
        self.dlg.exec()
        
    
    def change_text(self, text):
        index = self.currentIndex()
        self.setItemText(index,text)
        if hasattr(self,'dlg'):
            self.close_dialog()

    def close_dialog(self):
        self.dlg.close()
        self.setEditable(False)
        
    def insert_entry(self):
        num_items = self.count()
        self.insertItem(num_items,"Entry %d"%(num_items))
        self.setCurrentIndex(self.count()-1) #because python indices start from 0

class main_window(QtWidgets.QWidget):
    """
    Generic object containing all UI
    """
    
    def setup(self, parent):
        '''
        Creates Qt interactor
        '''
        
        #create new layout to hold both VTK and Qt interactors
        mainlayout=QtWidgets.QHBoxLayout(parent)
        
        #set headings font
        headFont=QtGui.QFont("Helvetica [Cronyx]",weight=QtGui.QFont.Bold)
        
        #make divisors
        frame_style = QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken
        horizLine1=QtWidgets.QFrame()
        horizLine1.setFrameStyle(frame_style)
        horizLine2=QtWidgets.QFrame()
        horizLine2.setFrameStyle(frame_style)
        
        #make upper layout
        display_box = QtWidgets.QGroupBox('Display')
        geo_button_layout = QtWidgets.QGridLayout()
        
        stl_layout = QtWidgets.QHBoxLayout()
        self.load_stl_button = QtWidgets.QPushButton('Load STL')
        self.load_stl_button.setToolTip('Load external STL file')

        self.entry_spec = entry_combo_box()
        self.entry_spec.setToolTip('Register discrete interaction geometry')
        stl_layout.addWidget(self.entry_spec)
        stl_layout.addWidget(self.load_stl_button)
        
        
        self.load_label = QtWidgets.QLabel("No geometry to show.")
        self.load_label.setToolTip("Path of last STL loaded.")
        self.load_label.setWordWrap(True)
        self.op_slider_label = QtWidgets.QLabel("Opacity:")
        self.op_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.op_slider.setRange(0,100)
        self.op_slider.setSliderPosition(100)

        geo_button_layout.addLayout(stl_layout,0,0,1,2)
        geo_button_layout.addWidget(self.load_label,1,0,1,2)
        geo_button_layout.addWidget(self.op_slider_label,2,0,1,1)
        geo_button_layout.addWidget(self.op_slider,2,1,1,1)
        geo_button_layout.addLayout(make_transformation_button_layout(self),3,0,1,2)
        geo_button_layout.setColumnStretch(0, 0)
        geo_button_layout.setColumnStretch(1, 1)
        display_box.setLayout(geo_button_layout)
        
        
        #make lower button layout
        draw_button_layout = QtWidgets.QGridLayout()
        self.draw_button = QtWidgets.QPushButton('Draw')
        self.draw_button.setEnabled(False)
        draw_button_layout.addWidget(self.draw_button,0,0,1,1)
        
        #make side panel layout
        lvlayout=QtWidgets.QVBoxLayout()

        #create VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor(parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(100)
        sizePolicy.setVerticalStretch(100)
        self.vtkWidget.setSizePolicy(sizePolicy)
        
        self.vtkWidget.setMinimumSize(QtCore.QSize(800, 600))

        lvlayout.addWidget(display_box)
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
        self.picking = False
        self.stl_actors = [] #entries is a dictionary comprised of everything that can get loaded
        make_logo(self.ren)
        
        #connect buttons
        self.ui.tabwidget.currentChanged.connect(self.check_draw)
        self.ui.load_stl_button.clicked.connect(self.load_stl)
        self.ui.entry_spec.currentIndexChanged.connect(self.change_entries)
        self.ui.op_slider.valueChanged[int].connect(self.change_opacity)
        self.ui.draw_button.clicked.connect(self.draw_pnts)
        
        self.ui.trans_widget.trans_origin_button.clicked.connect(self.apply_trans)
        self.ui.trans_reset_button.clicked.connect(self.reset_trans)
        self.ui.trans_widget.choose_vertex_button.clicked.connect(self.actuate_vertex_select)
        self.ui.rotation_widget.trans_origin_button.clicked.connect(self.apply_rotation)

    def change_entries(self):
        '''
        Makes sure that objects being held in the combobox's itemData match what's shown on screen. Makes the current item slightly highlighted. If there aren't any items in the combobox, then reset as if it first loaded
        '''
        #if the user has deleted all entries in the combobox:
        if self.ui.entry_spec.count() == 0:
            self.ren.RemoveAllViewProps()
            make_logo(self.ren)
            self.ui.vtkWidget.update()
            self.ui.trans_widget.trans_origin_button.setEnabled(False)
            self.ui.rotation_widget.trans_origin_button.setEnabled(False)
            self.ui.trans_reset_button.setEnabled(False)
            self.ui.trans_widget.choose_vertex_button.setEnabled(False)
            return
            
        #check if there's data for all entry_spec index.
        all_item_data = [self.ui.entry_spec.itemData(i) for i in range(self.ui.entry_spec.count())]
        #filter nones
        all_item_data = [x for x in all_item_data if x is not None]
        valid_actors = [all_item_data[i].actor for i in range(len(all_item_data))]

        #Because of the clear function, there will always be more stl_actors than there will be itemData entries, so using sets:
        remove_actors = list(set(self.stl_actors) - set(valid_actors))
        for actor in remove_actors:
            self.ren.RemoveActor(actor)
            self.stl_actors.remove(actor)
        #Remove the entries in self.stl_actors that correspond to remove_actors
        
        #highlight the actor at currentIndex if it exists
        index = self.ui.entry_spec.currentIndex()
        if self.ui.entry_spec.itemData(index) is not None:
            self.active_stl_color(index)

    def active_stl_color(self, entry_index):
        rgb_val = (8, 143, 143)
        rgb_norm = tuple(val/255 for val in rgb_val)
        target = self.ui.entry_spec.itemData(entry_index)
        target.actor.GetProperty().SetColor(rgb_norm)
        for index in range(len(self.stl_actors)):
            if index == entry_index:
                self.stl_actors[index].GetProperty().SetColor(rgb_norm)
            else:
                self.stl_actors[index].GetProperty().SetColor(vtk.vtkNamedColors().GetColor3d('Gray'))

        self.ui.vtkWidget.setFocus()
        self.ui.vtkWidget.update()
    
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
    
    def redraw(self, entry_index):
        '''
        Updates actor in renderer for a given STL instance of self.ui.entry_spec ItemData. Called on each time that the instance is transformed.
        '''
        update_actor_list = False #condition to either append to the stl_actor list, or to overwrite at entry_index
        instance = self.ui.entry_spec.itemData(entry_index)
        
        #remove the relevant actor. If the instance exists, then it is removed from the renderer. Otherwise, return.
        if instance is not None:
            if instance.actor is not None:
                self.ren.RemoveActor(instance.actor)
                update_actor_list = True
        else:
            return

        # #regenerate stl_actor from np data if it doesn't exist
        # if instance.polydata is None:
            # polydata = vtk.vtkPolyData()
            # points = vtk.vtkPoints()
            # points.SetData(n2v(instance.points))
            # cells = vtk.vtkCellArray()
            # cells.SetCells(0, n2v_id(instance.verts))
        
            # polydata.SetPoints(points)
            # polydata.SetPolys(cells)
            # instance.polydata = polydata
        # else:
            # polydata = instance.polydata
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(instance.polydata)

        stl_actor = vtk.vtkActor()
        stl_actor.SetMapper(mapper)
        stl_actor.GetProperty().SetOpacity(self.ui.op_slider.value())
        # stl_actor.PickableOff()
        stl_actor.GetProperty().SetColor(vtk.vtkNamedColors().GetColor3d('Gray'))
        # stl_actor.GetProperty().EdgeVisibilityOn() #debug
        
        #update instance to include actor:
        instance.actor = stl_actor
        self.ui.entry_spec.setItemData(entry_index,instance)
        
        if self.ui.entry_spec.currentIndex() == 0:
            if hasattr(self,'origin_actor'):
                self.ren.RemoveActor(self.origin_actor)
            self.origin_actor = vtk.vtkAxesActor()
            #change scale of origin on basis of size of stl_actor, only if this is the first entry
            origin_scale = np.max(stl_actor.GetBounds())/16
            self.origin_actor.SetTotalLength(origin_scale,origin_scale,origin_scale)
            self.origin_actor.SetNormalizedShaftLength(1,1,1)
            self.origin_actor.SetNormalizedTipLength(0.2,0.2,0.2)
            
            self.origin_actor.GetXAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
            self.origin_actor.GetYAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
            self.origin_actor.GetZAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
            self.ren.AddActor(self.origin_actor)
        
        self.ren.AddActor(stl_actor)
        
        if update_actor_list:
            self.stl_actors[entry_index] = stl_actor
        else:
            self.stl_actors.append(stl_actor)
        
        self.ui.vtkWidget.update()
    
    def load_stl(self):
        '''
        For current entry does the following:
        Loads/reads stl file, returns an actor for the stl file, as well as points and polygons which can be saved and used to build a polydata object with redraw.
        '''
        index = self.ui.entry_spec.currentIndex()

        #Check if this is a first run from launch
        if index == -1:
            #condition where user loads an stl file to an empty combobox
            self.ren.RemoveAllViewProps()
            self.ui.entry_spec.insert_entry()
            
        if self.ui.entry_spec.itemData(index) is None and not self.stl_actors:
            #condition where user inserts an entry at launch
            self.ren.RemoveAllViewProps()
        
        filep,startdir=get_file('*.stl')
        
        if filep is None:
            return
        if not(os.path.isfile(filep)):
            print('Data file invalid.')
            return
        
        reader = vtk.vtkSTLReader()
        reader.SetFileName(filep)
        reader.Update()
        
        stl_polydata = reader.GetOutput()
        np_pts = v2n(stl_polydata.GetPoints().GetData())
        np_verts = v2n(stl_polydata.GetPolys().GetData())
        entry_data_object = interaction_geometry(stl_polydata, np_pts, np_verts, np.eye(4))
        
        index = self.ui.entry_spec.currentIndex() #because this could be an over-write
        #if being overwritten, then assign the instance's actor to the entry_data_object to be handled by redraw
        instance = self.ui.entry_spec.itemData(index)
        if instance is not None:
            if instance.actor is not None:
                entry_data_object.actor = instance.actor

        self.ui.entry_spec.setItemData(index,entry_data_object)
        #get prefix of filep for entry_spec text
        base = os.path.basename(filep)
        prefix = os.path.splitext(base)[0]
        self.ui.entry_spec.change_text(prefix)
        self.ui.load_label.setText(filep)
        
        self.redraw(index)
        self.active_stl_color(index)
        self.ren.ResetCamera()
        self.ui.vtkWidget.setFocus()
        
        self.ui.trans_widget.trans_origin_button.setEnabled(True)
        self.ui.rotation_widget.trans_origin_button.setEnabled(True)
        self.ui.trans_reset_button.setEnabled(True)
        self.ui.trans_widget.choose_vertex_button.setEnabled(True)
        
    
    def load_model_geo(self):
        '''
        loads model boundaries from file, sets them as sample geometry.
        '''
        print(self.file)
        with h5py.File(self.file, 'r') as f:
            self.np_pts = f['model_boundary/points'][()]
            self.np_verts = f['model_boundary/vertices'][()]
            # self.c_trans = f['model_boundary/transform'][()]
            self.c_trans = np.eye(4)
        self.redraw()

        self.info_actor = generate_info_actor('Loaded and set model geometry from data file.',self.ren)

    def reset_trans(self):
        '''
        Applies the inverse of the current transformation matrix to revert all transformations, resets inputs for movement
        '''
        index = self.ui.entry_spec.currentIndex()
        instance = self.ui.entry_spec.itemData(index)
        T = np.linalg.inv(instance.trans)
        self.apply_transformation(T)
        self.display_info('Reset translation.')

    def apply_trans(self):
        '''
        Applies the appropriate translation to the existing model object(s)
        '''
        self.ui.translate_drop_button.setChecked(False)
        
        T = np.eye(4)
        T[0,-1] = self.ui.trans_widget.translate_x.value()
        T[1,-1] = self.ui.trans_widget.translate_y.value()
        T[2,-1] = self.ui.trans_widget.translate_z.value()
        self.apply_transformation(T)
        self.display_info('Translated model.')
        if self.picking:
            self.actuate_vertex_select()
    
    def apply_rotation(self):
        '''
        Applies a rotation matrix to the current object
        '''
        
        T = get_trans_from_euler_angles( \
        self.ui.rotation_widget.rotate_x.value(), \
        self.ui.rotation_widget.rotate_y.value(), \
        self.ui.rotation_widget.rotate_z.value())
        self.apply_transformation(T)
        self.display_info('Translated model.')

    def apply_transformation(self,T):
        '''
        Applies transformation matrix T to current STL entry
        '''
        
        index = self.ui.entry_spec.currentIndex()
        instance = self.ui.entry_spec.itemData(index)
        
        #modify relevant aspects of the instance according to the transformation matrix
        c_trans = instance.trans
        np_pts = do_transform(instance.points,T)
        c_trans = T @ instance.trans
        c_points = instance.polydata.GetPoints()
        for i in range(len(np_pts)):
            c_points.SetPoint(i, np_pts[i,:])
        instance.polydata.Modified()
        # trans_pd = None #Regen & updated by redraw
        #trans_pd = instance.polydata.GetPoints().SetData(n2v(np_pts)) #doesn't produce a valid polydata object; debug
        
        #update item data
        updated_instance = interaction_geometry(instance.polydata, np_pts, instance.verts, c_trans)
        #this will always be an 'overwrite' of the existing actor:
        updated_instance.actor = instance.actor
        
        self.ui.entry_spec.setItemData(index,updated_instance)

        self.redraw(index)
        self.active_stl_color(index)
        self.ren.ResetCamera()
        self.ui.vtkWidget.setFocus()

    def actuate_vertex_select(self):
        '''
        Starts picking and handles ui button display
        '''
        
        #selected actor is the vertex highlight
        if hasattr(self,'selected_actor'):
            self.ren.RemoveActor(self.selected_actor)
        
        if self.picking:
            #Remove picking observer and re-initialise
            self.iren.RemoveObservers('LeftButtonPressEvent')
            self.iren.AddObserver('LeftButtonPressEvent',self.default_left_button)
            QtWidgets.QApplication.processEvents()
            self.picking = False
            self.ui.translate_drop_button.setChecked(False)
            self.ui.trans_widget.choose_vertex_button.setChecked(False)

        else:
            self.iren.AddObserver('LeftButtonPressEvent', self.picker_callback)
            self.picking = True
            #meant to keep dropdown engaged through the picking process, but ineffective. Stopping picking suspends, as does 'updating'.
            self.ui.trans_widget.choose_vertex_button.setChecked(True)
            self.ui.translate_drop_button.setChecked(True)

    def default_left_button(self, obj, event):
        #forward standard events according to the default style`
        self.iren.GetInteractorStyle().OnLeftButtonDown()

    def picker_callback(self, obj, event):
        """
        Actuates a pick of a node on current component
        """
        index = self.ui.entry_spec.currentIndex()
        instance = self.ui.entry_spec.itemData(index)
        

        colors = vtk.vtkNamedColors()
        
        picker = vtk.vtkPointPicker()
        picker.SetTolerance(1)
        
        pos = self.iren.GetEventPosition()
        
        picker.Pick(pos[0], pos[1], 0, self.ren)

        if picker.GetPointId() != -1:
            
            ids = vtk.vtkIdTypeArray()
            ids.SetNumberOfComponents(1)
            ids.InsertNextValue(picker.GetPointId())

            if hasattr(self,'selected_actor'):
                self.ren.RemoveActor(self.selected_actor)
            centre = instance.polydata.GetPoint(picker.GetPointId())
            self.selected_actor = generate_sphere(centre,1,colors.GetColor3d("orchid"))
            
            self.ui.trans_widget.translate_x.setValue(-centre[0])
            self.ui.trans_widget.translate_y.setValue(-centre[1])
            self.ui.trans_widget.translate_z.setValue(-centre[2])
            
            self.ren.AddActor(self.selected_actor)
            
            
    def change_opacity(self,value):
        self.ui.op_slider_label.setText('Opacity: %d%%'%value)
        index = self.ui.entry_spec.currentIndex()
        if hasattr(self,'stl_actors'):
            self.stl_actors[index].GetProperty().SetOpacity(value/100)
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
                    self.info_actor = generate_info_actor('Point data could not be loaded.',self.ren)
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
        self.info_actor = generate_info_actor('Loaded model from data file.', self.ren)
            
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
            self.info_actor = generate_info_actor('Saved to data file.',self.ren)


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
            self.info_actor = generate_info_actor('Image saved.',self.ren)
        
        elif key=="r":
            flip_visible(self.axis_actor)
        
        self.ren.ResetCamera()
        self.ui.vtkWidget.update()

    def display_info(self,msg):
        '''
        Checks if there's an info_actor and removes it before displaying another one
        '''
        if hasattr(self,'info_actor'):
            self.ren.RemoveActor(self.info_actor)
        self.info_actor = generate_info_actor(msg,self.ren)
        self.ren.AddActor(self.info_actor)

    def on_mouse_move(self, obj, event):
        if hasattr(self,'info_actor'):
            self.ren.RemoveActor(self.info_actor)
        else:
            pass

class interaction_geometry:
    def __init__(self, polydata, points, vertices, transformation):
        self.polydata = polydata
        self.points = points
        self.verts = vertices
        self.trans = transformation
        self.actor = None

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
    app=QtWidgets.QApplication(sys.argv)
    window = launch()
    window.show()
    sys.exit(app.exec_())