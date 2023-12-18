#!/usr/bin/env python

'''
Common functions for OpenRS
'''

import os
import vtk
import numpy as np
from scipy.interpolate import LinearNDInterpolator as NDinterp
from vtk.util.numpy_support import vtk_to_numpy as v2n
from vtk.util.numpy_support import numpy_to_vtk as n2v
from vtk.numpy_interface import dataset_adapter as dsa
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pkg_resources import Requirement, resource_filename
import yaml
from OpenRS.return_disp import get_disp_from_fid

def generate_sphere(center, radius, color):
    source = vtk.vtkSphereSource()
    source.SetCenter(*center)
    source.SetRadius(radius)
    source.SetThetaResolution(20)
    source.SetPhiResolution(20)
    source.Update()
    
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(source.GetOutput())
    
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    
    return actor

def generate_point_actor(pts,color,size):
    '''
    Returns vtk actor for a point cloud having 'size' points, which are provided in a numpy matrix, one point per row.
    '''

    vtkPnts = vtk.vtkPoints()
    vtkVerts = vtk.vtkCellArray()
    
    #convert color to 8-bit rgb tuple if needed
    if color[0]<=1:
        color=(int(color[0]*255),int(color[1]*255),int(color[2]*255))


    colors=vtk.vtkUnsignedCharArray()
    colors.SetNumberOfComponents(3)
    colors.SetName("color")
    
    
    #load up points
    for i in pts:
        pId= vtkPnts.InsertNextPoint(i)
        vtkVerts.InsertNextCell(1)
        vtkVerts.InsertCellPoint(pId)
        colors.InsertNextTuple(color)

    polydata = vtk.vtkPolyData()
    polydata.SetPoints(vtkPnts)
    polydata.SetVerts(vtkVerts)
    polydata.GetPointData().SetScalars(colors)
    
    vtkPntMapper = vtk.vtkDataSetMapper()
    vtkPntMapper.SetInputData(polydata)

    actor=vtk.vtkActor()
    actor.SetMapper(vtkPntMapper)

    actor.GetProperty().SetPointSize(size)
    return actor, polydata

def generate_info_actor(message,ren):
    '''
    Returns an information actor comprised of the incoming message string positioned correctly according to the incoming renderer
    '''
    
    textmapper = vtk.vtkTextMapper()
    textmapper.SetInput(message)
    textProperty = vtk.vtkTextProperty()
    textProperty.SetFontSize(16)
    textProperty.SetJustificationToCentered()
    textProperty.SetColor(vtk.vtkNamedColors().GetColor3d('tomato'))
    textmapper.SetTextProperty(textProperty)
    info_actor = vtk.vtkActor2D()
    info_actor.SetMapper(textmapper)
    #get size of renderwindow
    size = ren.GetSize() #(width,height)
    info_actor.SetPosition(int(0.5*size[0]), int(0.001*size[1]))
    return info_actor

def generate_axis_actor(actor,ren):
    '''
    Generate a 3D axis based on the bounds of incoming 'actor' or actor-like object that has a GetBounds() method and renderer
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
    
    ax3D.SetBounds(actor.GetBounds())
    ax3D.SetCamera(ren.GetActiveCamera())
    return ax3D

def line_query_NDinterp(output,q1,q2,numPoints,component):
    """
    Interpolate the data from output over q1 to q2 using NDinterpolation
    """
    
    #generate series of x, y and z values extending from q1 to q2
    line_pts = np.linspace(np.asarray(q1), np.asarray(q2), numPoints)
    #get points comprising the model
    mdl_pts = v2n(output.GetPoints().GetData())
    #get array of specified stresses according to mdl_pts
    field = v2n(output.GetPointData().GetArray(component))
    #make interpolator
    local_interp = NDinterp(mdl_pts,field)
    return np.hstack((line_pts,local_interp(line_pts).reshape((-1, 1))))
    

def line_query_vtk(output,q1,q2,numPoints,component):
    """
    Interpolate the data from output over q1 to q2 (list of x,y,z) using VTK's probe filter
    """
    line = vtk.vtkLineSource()
    line.SetResolution(numPoints)
    line.SetPoint1(q1)
    line.SetPoint2(q2)
    line.Update()
    
    probe = vtk.vtkProbeFilter()
    probe.SetInputConnection(line.GetOutputPort())
    probe.SetSourceData(output)
    
    probe.Update() 
    
    #initialize numpy array - number of points in probe potentially != numPoints
    line_pts = np.empty((probe.GetOutput().GetNumberOfPoints(),3)) #x,y,z
    
    #get all points: could also iterate over probe.GetOutput().GetNumberOfPoints()
    for i in range(numPoints):
        line_pts[i,:] = probe.GetOutput().GetPoint(i)
    #stack probe value on end column of line_pts
    line_pts = np.hstack((line_pts, \
            np.array([v2n(probe.GetOutput().GetPointData().GetArray(component))]).T))
    
    return line_pts

def get_save_file(ext):
    '''
    Returns a the complete path to the file name with ext, starting in outputd. Checks extensions and if an extension is not imposed, it will write the appropriate extension based on ext.
    '''
    ftypeName={}
    ftypeName['*.csv']='OpenRS comma delimited output file'
    ftypeName['*.txt']='OpenRS whitespace delimited output file'
    ftypeName['*.stl']='OpenRS stereolithography (STL) file'
    ftypeName['*.OpenRS'] = 'OpenRS HDF5-format data file'
    ftypeName['*.vtp']= 'OpenRS converted VTK polydata (XML format)'
    id=str(os.getcwd())

    filer, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save as:", id,str(ftypeName[ext]+' ('+ext+')'))

    if filer == '':
        return None, None
    else:
        return filer, os.path.dirname(filer)

def get_file(*args):
    '''
    Returns absolute path to filename and the directory it is located in from a PyQt5 filedialog. First value is file extension, second is a string which overwrites the window message.
    '''
    ext = args
    launchdir = os.getcwd()
    ftypeName={}
    ftypeName['*.vtu']=["VTK model file (XML format)", "*.vtu", "VTU file"]
    ftypeName['*.vtp']=["VTK model file (XML format)", "*.vtp", "VTP file"]
    ftypeName['*.stl']=["OpenRS STL", "*.stl","STL file"]
    ftypeName['*.OpenRS'] = ["OpenRS HDF5-format data file", "*.OpenRS", "OpenRS file"]
    ftypeName['*.txt'] = ["OpenRS whitespace delimited points", "*.txt", "OpenRS text input"]
    ftypeName['*.*'] = ["OpenRS external executable", "*.*", "..."]
    
    filter_str = ""
    for entry in args:
        filter_str += ftypeName[entry][2] + ' ('+ftypeName[entry][1]+');;'
    filter_str += ('All Files (*.*)')
    
    filer = QtWidgets.QFileDialog.getOpenFileName(None, ftypeName[ext[0]][0], 
         os.getcwd(),(filter_str))

    if filer[0] == '':
        filer = None
        startdir = None
        return filer, startdir
        
    else: #return the filename/path
        return filer[0], os.path.dirname(filer[0])
        
def xyview(ren):
    camera = ren.GetActiveCamera()
    camera.SetPosition(0,0,1)
    camera.SetFocalPoint(0,0,0)
    camera.SetViewUp(0,1,0)

def yzview(ren):
    camera = ren.GetActiveCamera()
    camera.SetPosition(1,0,0)
    camera.SetFocalPoint(0,0,0)
    camera.SetViewUp(0,0,1)

def xzview(ren):
    vtk.vtkObject.GlobalWarningDisplayOff() #mapping from '3' triggers an underlying stereoview that most displays do not support
    camera = ren.GetActiveCamera()
    camera.SetPosition(0,1,0)
    camera.SetFocalPoint(0,0,0)
    camera.SetViewUp(0,0,1)

def flip_visible(actor):
    '''
    Convenience function for changing the visibility of actors
    '''
    if actor.GetVisibility():
        actor.VisibilityOff()
    else:
        actor.VisibilityOn()

def make_logo(ren):
    spl_fname=resource_filename("OpenRS","meta/Logo.png")
    img_reader = vtk.vtkPNGReader()
    img_reader.SetFileName(spl_fname)
    img_reader.Update()
    logo = vtk.vtkLogoRepresentation()
    logo.SetImage(img_reader.GetOutput())
    logo.ProportionalResizeOn()
    logo.SetPosition( 0.1, 0.1 ) #lower left
    logo.SetPosition2( 0.8, 0.8 ) #upper right
    logo.GetImageProperty().SetDisplayLocationToBackground()
    ren.AddViewProp(logo)
    logo.SetRenderer(ren)
    return logo

def do_transform(points, T):
    '''
    Applies 4x4 transformation matrix to points and returns the result
    @Param - points, Nx3 matrix of points; T - 4x4 homologous matrix
    '''
    X = points.copy()
    X = X.transpose()
    X = np.append(X, np.ones((1, X.shape[1])), axis=0) #pad with 1's
    X = T @ X #apply by matrix multiplication
    return X[0:3].transpose() #return an Nx3

class table_model(QtCore.QAbstractTableModel):

    def __init__(self, data, headerlabels):
        '''
        data - matrix-like data (needs to be a list of lists)
        headerlabels - list of strings for column labels
        '''
        super(table_model, self).__init__()
        self._data = data
        self.headerlabels = headerlabels
        
    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            value = self._data[index.row()][index.column()] 
            return str(value)

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            try:
                float(value)
                self._data[index.row()][index.column()] = value
                return True
            except ValueError:
                return False
    
    def getCellData(self, index):
        return self._data[index[0]][index[1]]
            
    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])

    def headerData(self, col, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return QtCore.QVariant(self.headerlabels[col])
            if orientation == QtCore.Qt.Vertical:
                return str(col+1)

    def insertRows(self, position, rows, QModelIndex, parent):
        self.beginInsertRows(QModelIndex, position, position+rows-1)
        default_row = [0]*len(self._data[0])  # or _headers if defined.
        for i in range(rows):
            self._data.insert(position, default_row)
        self.endInsertRows()
        self.layoutChanged.emit()
        return True

    def removeRows(self, position, rows, QModelIndex):
        self.beginRemoveRows(QModelIndex, position, position+rows-1)
        for i in range(rows):
            del(self._data[position])
        self.endRemoveRows()
        self.layoutChanged.emit()
        return True

    def flags(self, index):
        return Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsEditable

class external(QThread):
    '''
    Sets up and runs external thread for FEA, emits 100 when done.
    '''
    _signal = pyqtSignal(int)
    def __init__(self,disp,ccx_exe,outputdir):
        super(external, self).__init__()
        self.disp = disp
        self.ccx_exe = ccx_exe
        self.outputdir = outputdir

    def run(self):
        from OpenRS.generate.packager_ccx import run_packager_ccx
        mf = resource_filename("OpenRS","generate/U_elastic_mesh_only.inp")
        rf = 'U_elastic_run_ccx.inp'
        run_packager_ccx(mesh_file_name = mf, \
            run_file_name = rf, \
            disp = self.disp, \
            ccx_exe = self.ccx_exe, \
            outputdir = self.outputdir)
        self._signal.emit(100)


class modeling_widget(QtWidgets.QDialog):

    def __init__(self, parent):
        super(modeling_widget, self).__init__(parent)
        
        self.setWindowTitle("OpenRS - FEA flexure calculation" )
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumSize(QtCore.QSize(450, 400))

        
        fid_layout_image = QtGui.QPixmap(r"meta\flexure_pnts.png",'PNG')
        self.fid_layout_image = fid_layout_image.scaledToHeight(250)
        self.image_label = QtWidgets.QLabel()
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(self.fid_layout_image)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        
        fid_data_group = QtWidgets.QGroupBox('Boundary condition input:')
        #populate with points from undeformed orientations
        self.fid_data = np.array([[-40,25,0],[-40,45,0],[40,45,0],[40,25,0]]).tolist()
        self.disp = 0.0
        
        self.pbar = QtWidgets.QProgressBar(self, textVisible=True)
        self.pbar.setAlignment(Qt.AlignCenter)
        self.pbar.setFormat("Idle")
        self.pbar.setFont(QtGui.QFont("Helvetica",italic=True))
        self.pbar.setValue(0)

        self.fid_model = table_model(self.fid_data,['X','Y','Z'])
        self.fid_table = QtWidgets.QTableView()
        self.fid_table.setModel(self.fid_model)
        self.fid_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.fid_table.resizeColumnsToContents()
        self.fid_table.resizeRowsToContents()
        
        dti_entry_label = QtWidgets.QLabel('DTI reading')
        self.dti_entry = QtWidgets.QDoubleSpinBox()
        self.dti_entry.setMinimum(-0.58865412)
        self.dti_entry.setMaximum(0.58865412)
        self.dti_entry.setDecimals(3)
        calc_button_group = QtWidgets.QButtonGroup(self)
        self.calc_fid_rbutton = QtWidgets.QRadioButton("Calculate using fiducial")
        self.calc_fid_rbutton.setChecked(True)
        self.calc_dti_rbutton = QtWidgets.QRadioButton("Calculate using DTI")
        calc_button_group.addButton(self.calc_fid_rbutton)
        calc_button_group.addButton(self.calc_dti_rbutton)
        calc_button_group.setExclusive(True)
        self.run_calc_button = QtWidgets.QPushButton('Calculate')
        calc_layout = QtWidgets.QGridLayout()
        calc_layout.addWidget(dti_entry_label,0,0,1,1)
        calc_layout.addWidget(self.dti_entry,0,1,1,1)
        calc_layout.addWidget(self.calc_fid_rbutton,1,0,1,2)
        calc_layout.addWidget(self.calc_dti_rbutton,2,0,1,2)
        calc_layout.addWidget(self.run_calc_button,3,0,1,2)
        
        
        headFont=QtGui.QFont("Helvetica [Cronyx]", 14, weight=QtGui.QFont.Bold )
        d1_label = QtWidgets.QLabel('Displacement:')
        self.d1 = QtWidgets.QLabel(str(self.disp))
        self.d1.setFont(headFont)
        d_layout = QtWidgets.QHBoxLayout()
        d_layout.addWidget(d1_label)
        d_layout.addWidget(self.d1)
        
        fid_table_layout = QtWidgets.QVBoxLayout()
        fid_table_layout.addWidget(self.fid_table)
        fid_table_layout.addLayout(calc_layout)
        fid_table_layout.addLayout(d_layout)
        fid_data_group.setLayout(fid_table_layout)
        
        
        
        fid_layout = QtWidgets.QHBoxLayout()
        fid_layout.addWidget(self.image_label)
        fid_layout.addStretch()
        fid_layout.addWidget(fid_data_group)
        

        self.run_button = QtWidgets.QPushButton('Run')
        ccx_exec_path_label = QtWidgets.QLabel('Path to CalculiX executable:')
        self.ccx_exec_path = QtWidgets.QLineEdit()
        ccx_choose_path = QtWidgets.QPushButton('...')
        ccx_choose_path.setMaximumWidth(20)
        fea_path_label = QtWidgets.QLabel('Working directory:')
        self.fea_path = QtWidgets.QLineEdit()
        wd_choose_path = QtWidgets.QPushButton('...')
        wd_choose_path.setMaximumWidth(20)

        fea_layout = QtWidgets.QGridLayout()
        fea_layout.addWidget(self.run_button,2,0,1,1)
        fea_layout.addWidget(ccx_exec_path_label,0,0,1,1)
        fea_layout.addWidget(self.ccx_exec_path,0,1,1,2)
        fea_layout.addWidget(ccx_choose_path,0,3,1,1)
        fea_layout.addWidget(fea_path_label,1,0,1,1)
        fea_layout.addWidget(self.fea_path,1,1,1,2)
        fea_layout.addWidget(wd_choose_path,1,3,1,1)
        fea_layout.addWidget(self.pbar,2,1,1,3)

        
        self.run_calc_button.clicked.connect(self.get_disp)

        self.run_button.clicked.connect(self.run_calc)
        
        ccx_choose_path.clicked.connect(self.set_ccx)
        wd_choose_path.clicked.connect(self.set_wd)
        

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(fid_layout)
        vertical_spacer = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout.addItem(vertical_spacer)
        self.layout.addLayout(fea_layout)

        self.setLayout(self.layout)
        self.read_config()
        self.show()

    def get_disp(self):
        '''
        Reads GUI, depending on what radio button calculated displacement boundary condition
        '''
        if self.calc_fid_rbutton.isChecked():
            model = self.fid_model
            fid_pts = np.zeros((4,3))
            nrows = model.rowCount(0)
            ncols = model.columnCount(0)
            for i in range(nrows):
                for j in range(ncols):
                    fid_pts[i,j]=model.getCellData([i,j])
            self.disp = get_disp_from_fid(fid_pts,False)
            self.dti_entry.setValue(self.disp*-0.58865412)
        elif self.calc_dti_rbutton.isChecked():
            self.disp = self.dti_entry.value()/-0.58865412
        
        self.d1.setText('%6.3f'%self.disp)
        
    def set_ccx(self):
        f,_ = get_file("*.*")
        self.ccx_exec_path.setText(f)
        self.make_config_change()
    
    def set_wd(self):
        dir = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.fea_path.setText(dir)
        self.make_config_change()
        
    def run_calc(self):
        self.thread = external(self.disp,self.ccx_exec_path.text(),self.fea_path.text())
        self.thread._signal.connect(self.signal_accept)
        self.thread.start()
        self.pbar.setTextVisible(True)
        self.pbar.setStyleSheet("")
        self.pbar.setRange(0,0)
        
    def signal_accept(self, msg):
        if int(msg) == 100:
            self.pbar.setRange(0,100)
            self.pbar.setValue(0)
            self.pbar.setFormat("Complete")
            self.pbar.setStyleSheet("QProgressBar"
              "{"
              "background-color: lightgreen;"
              "border : 1px"
              "}")
        

    def read_config(self):
        fname=resource_filename("OpenRS","meta/OpenRSconfig.yml")
        with open(fname, 'r') as f:
            read = yaml.load(f, Loader=yaml.FullLoader)
        
        self.ccx_exec_path.setText(read['FEA']['ccx_exec'])
        self.fea_path.setText(read['FEA']['work_dir'])

    def make_config_change(self):
        data = dict(
        FEA = dict(
        ccx_exec = str(self.ccx_exec_path.text()),
        work_dir = str(self.fea_path.text())
        )
        )
        fname=resource_filename("OpenRS","meta/OpenRSconfig.yml")
        with open(fname,'w+') as f:
            yaml.dump(data,f, default_flow_style=False)

def translate_amphyon_vtp(infile=None, outfile=None):
    '''
    Reads point-based data from the infile as specified by the default Amphyon output
    Ignores first column, assumes that columns 1-3 are undeformed coordinates, next 3 are deformations and the next 4 are stresses.
    Returns a polydata point cloud object with stresses as point data
    Returns a Nx3 numpy array of positions and Nx4 numpy array of 4 stresses if outfile is None, otherwise writes vtk polydata file to outfile.
    '''
    if infile is None:
        infile,startdir=get_file('*.txt')
        if infile is None: #dialog cancelled
            return
        if not(os.path.isfile(infile)):
            return
            
    #use genfromtxt to read in all data
    fid = open(infile,'r')
    skip_header_index = 0
    all_pos = []
    all_stresses = []
    while 1:
        lines = fid.readlines(100000)
        if not lines:
            break
        for line in lines:
            if skip_header_index > 0:
                line = line.replace(',','.')
                raw_line = line.split()
                raw_line = [float(x) for x in raw_line]
                #c1-c4: position, c5-7: displacment, c8-11: stresses (x, y, z & VM)
                pos = np.asarray(raw_line[1:4])
                disp = np.asarray(raw_line[4:7])
                pos = pos + disp
                stress = np.asarray(raw_line[8:12])
                all_pos.append(pos)
                all_stresses.append(stress)
            skip_header_index += 1
    
    fid.close()
    all_pos = np.asarray(all_pos)
    all_stresses = np.asarray(all_stresses)


    pnts = vtk.vtkPoints()
    pnts.SetData(n2v(all_pos))
    
    verts = vtk.vtkCellArray()
    for i in np.arange(len(all_pos)):
        verts.InsertNextCell(1)
        verts.InsertCellPoint(i)
    
    pd = vtk.vtkPolyData()
    pd.SetPoints(pnts)
    pd.SetVerts(verts)
    
    array_names = ['Sxx', 'Syy', 'Szz', 'Svm']
    for array_ind in range(all_stresses.shape[1]): #number of columns in all_stresses
        curr_array = n2v(all_stresses[:,array_ind], deep = True)
        curr_array.SetName(array_names[array_ind])
        pd.GetPointData().AddArray(curr_array)
    pd.Modified()

    if outfile is None:
        outfile, _ = get_save_file('*.vtp')
        if outfile is None: #dialog cancelled
            return

        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetInputData(pd)
        writer.SetFileName(outfile)
        writer.Write()
            
    return pd

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = modeling_widget(None)
    sys.exit(app.exec_())