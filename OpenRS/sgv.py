#!/usr/bin/env python
'''
Standard gauge volume viewer widget for OpenRS
'''

import sys
import numpy as np
import vtk
from PyQt5 import QtCore, QtGui, QtWidgets
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from OpenRS.open_rs_common import xyview, generate_axis_actor
from OpenRS.transform_widget import make_rotate_button, get_trans_from_euler_angles

class sgv_viewer(QtWidgets.QWidget):
    def __init__(self, parent = None):
        super(sgv_viewer, self).__init__(parent)
        
        vl = QtWidgets.QVBoxLayout()
        
        self.vtkWidget = QVTKRenderWindowInteractor(parent)
        
        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        style=vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)
        self.setLayout(vl)
        
        #make button box for specifying shape of gauge volume
        define_box = QtWidgets.QGroupBox('Define')
        self.width = QtWidgets.QDoubleSpinBox()
        self.width.setMinimum(0.05)
        self.width.setValue(1)
        self.width.setMaximum(5)
        self.width.setPrefix('Width ')
        self.width.setSuffix(' mm')
        
        self.depth = QtWidgets.QDoubleSpinBox()
        self.depth.setMinimum(0.05)
        self.depth.setValue(2)
        self.depth.setMaximum(10)
        self.depth.setPrefix('Depth ')
        self.depth.setSuffix(' mm')

        theta_label =QtWidgets.QLabel("2\u03F4 (deg)")
        self.theta = QtWidgets.QDoubleSpinBox()
        self.theta.setMinimum(0.1)
        self.theta.setValue(90)
        self.theta.setMaximum(179.9)
        self.theta.setPrefix("2\u03F4 ")
        self.theta.setSuffix(' °')
        
        self.update_sgv = QtWidgets.QPushButton('Preview')
        self.reset_sgv = QtWidgets.QPushButton('Reset')
        self.finalize_sgv = QtWidgets.QPushButton('Finalize')
        
        #get rotation from transform widget
        self.rotate_group_dropdown = make_rotate_button(self)
        
        sgv_buttongroup = QtWidgets.QGridLayout()
        define_box.setLayout(sgv_buttongroup)
        sgv_buttongroup.addWidget(self.width,0,0,1,1)
        sgv_buttongroup.addWidget(self.depth,1,0,1,1)
        sgv_buttongroup.addWidget(self.theta,2,0,1,1)
        sgv_buttongroup.addWidget(self.rotate_group_dropdown,0,1,1,1)
        sgv_buttongroup.addWidget(self.reset_sgv, 0,2,1,1)
        sgv_buttongroup.addWidget(self.update_sgv,1,2,1,1)
        sgv_buttongroup.addWidget(self.finalize_sgv,2,2,1,1)
        sgv_buttongroup.setColumnStretch(0,0)
        sgv_buttongroup.setColumnStretch(2,0)
        

        vl.addWidget(self.vtkWidget)
        vl.addWidget(define_box)
        
        self.rotation_widget.trans_origin_button.setEnabled(True)
        
        self.update_sgv.clicked.connect(self.draw)
        self.rotation_widget.trans_origin_button.clicked.connect(self.draw)
        self.reset_sgv.clicked.connect(self.reset)
        self.finalize_sgv.clicked.connect(self.finalize)
        
        self.finalized = False
        self.initialize_vtk()
        self.draw()
    
    def initialize_vtk(self):
        '''
        Run-once setup/definition of interactor specifics
        '''
        axes_actor = vtk.vtkAxesActor()
        self.axes = vtk.vtkOrientationMarkerWidget()
        self.axes.SetOrientationMarker(axes_actor)
        
        self.iren.AddObserver("KeyPressEvent",self.keypress)
        self.axes.SetInteractor(self.iren)
        
        self.axes.EnabledOn()
        self.axes.InteractiveOn()
        self.ren.GetActiveCamera().ParallelProjectionOn()
        colors = vtk.vtkNamedColors()
        self.ren.SetBackground(colors.GetColor3d('Azure'))
        self.ren.ResetCamera()
        self.iren.Initialize()
    
    def finalize(self):
        '''
        Lock all characteristics of interactor, make sgv_viewer read-only to allow rendering of sgv externally
        '''
        self.finalized = True
        #deactivate relevant widgets
        self.update_sgv.setDisabled(True)
        self.finalize_sgv.setDisabled(True)
        self.width.setDisabled(True)
        self.depth.setDisabled(True)
        self.theta.setDisabled(True)
        self.rotation_widget.rotate_x.setDisabled(True)
        self.rotation_widget.rotate_y.setDisabled(True)
        self.rotation_widget.rotate_z.setDisabled(True)
        self.params = {
        'width': self.width.value(),
        'depth': self.depth.value(),
        '2theta': self.theta.value(),
        'rotate_x': self.rotation_widget.rotate_x.value(),
        'rotate_y': self.rotation_widget.rotate_y.value(),
        'rotate_z': self.rotation_widget.rotate_z.value()
        } #for repopulating interactor on load.
    
    def reset(self):
        '''
        Unlock interactor and reset to defaults, call draw() to update
        '''
        self.finalized = False
        self.update_sgv.setDisabled(False)
        self.finalize_sgv.setDisabled(False)
        self.width.setDisabled(False)
        self.width.setValue(1)
        self.depth.setDisabled(False)
        self.depth.setValue(2)
        self.theta.setDisabled(False)
        self.theta.setValue(90)
        self.rotation_widget.rotate_x.setDisabled(False)
        self.rotation_widget.rotate_x.setValue(0)
        self.rotation_widget.rotate_y.setDisabled(False)
        self.rotation_widget.rotate_y.setValue(0)
        self.rotation_widget.rotate_z.setDisabled(False)
        self.rotation_widget.rotate_z.setValue(0)
        self.draw()
        
        
    def draw(self):
        self.ren.RemoveAllViewProps()
        w=self.width.value()
        d = self.depth.value()
        # t=np.radians(np.absolute(180-self.theta.value())/2)
        t = np.radians(self.theta.value())
        
        self.trans = get_trans_from_euler_angles( \
        self.rotation_widget.rotate_x.value(), \
        self.rotation_widget.rotate_y.value(), \
        self.rotation_widget.rotate_z.value())
        
        
        #get rotated vtk source for sgv
        ugrid = draw_sgv(w, d, t, self.trans)
        #get vtk assembly for arrows
        sgv_arrows = draw_directions(w,t,self.trans)

        # Create a mapper and actor for gauge volume
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(ugrid)
        
        
        colors = vtk.vtkNamedColors()
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(mapper)
        self.actor.GetProperty().SetColor(
            colors.GetColor3d('Salmon'))
        
        self.actor.GetProperty().SetOpacity(0.5)
        
        self.ren.AddActor(self.actor)
        self.ren.AddActor(sgv_arrows)
        self.ren.AddActor(generate_axis_actor(self.actor,self.ren))
        
        self.ren.ResetCamera()
        self.vtkWidget.update()


    def keypress(self,obj,event):
        key = obj.GetKeyCode()
        if key == "1":
            xyview(self.ren)
        self.ren.ResetCamera()
        self.vtkWidget.update()

def draw_directions(w, t, trans):
    '''
    Return a vtkAssembly of arrows showing entry and exit of beam from sgv
    '''
    arrow_length = w / np.sin(t)
    
    t = np.absolute((np.pi - t)/2) # rotate by 2 theta
    
    exit_direction = np.array([w*np.sin(t), w*np.cos(t), 0])
    enter_direction = np.array([-w*np.sin(t), w*np.cos(t), 0])
    strain_direction_ref = np.array([0, w, 0])
    
    #transform directions based on trans
    enter_direction = np.dot(enter_direction,trans[0:3,0:3])
    exit_direction = np.dot(exit_direction,trans[0:3,0:3])
    strain_direction_ref = np.dot(strain_direction_ref,trans[0:3,0:3])

    exit_norm = exit_direction / (np.linalg.norm(exit_direction))
    enter_norm = enter_direction / (np.linalg.norm(enter_direction))
    strain_ref_norm = strain_direction_ref / (np.linalg.norm(strain_direction_ref))
    exit_arrow_actor = arrow(np.array([0,0,0]),arrow_length,exit_norm,False,(1,0,0))
    enter_arrow_actor = arrow(np.array([0,0,0]),arrow_length,enter_norm,True,(1,0,0))
    strain_arrow_actor = arrow(np.array([0,0,0]),arrow_length,strain_ref_norm,False,(0,0,1))
    arrows = vtk.vtkAssembly()
    arrows.AddPart(enter_arrow_actor)
    arrows.AddPart(exit_arrow_actor)
    arrows.AddPart(strain_arrow_actor)
    return arrows

def draw_sgv(w, l, t, trans):
    '''
    Return a vtkUnstructured grid based on w, l and t
    trans is either a 4x4 transformation matrix, or a 3x3 rotation matrix. Rotations are applied first.
    '''
    
    q = w/np.sin(t)
    vertices = np.array([[0,0,-l/2], #0
    [q, 0, -l/2], #1
    [q*(1+np.cos(t)), w, -l/2], #2
    [q*np.cos(t), w, -l/2], #3
    [0,0, l/2], #4
    [q, 0, l/2], #5
    [q*(1+np.cos(t)), w, l/2], #6
    [q*np.cos(t), w, l/2] #7
    ])
    
    #move vertices to centroid
    vertices = vertices - np.mean(vertices, axis=0)
    #rotate about z by half of (two) theta
    vertices = np.dot(vertices,np.array([[np.cos(t/2), -np.sin(t/2), 0],
    [np.sin(t/2), np.cos(t/2), 0],
    [0, 0, 1]]))
    
    vertices = np.dot(vertices,trans[0:3,0:3])
    if trans.size == 16:
        vertices = vertices+trans[0:3,3]

    points = vtk.vtkPoints()
    for v in vertices:
        points.InsertNextPoint(v)


    # These are the point ids corresponding to each face.
    faces = [[0, 3, 2, 1], [0, 4, 7, 3], [4, 5, 6, 7], [5, 1, 2, 6], [0, 1, 5, 4], [2, 3, 7, 6]]
    faceId = vtk.vtkIdList()
    faceId.InsertNextId(6)  # Six faces make up the cell.
    for face in faces:
        faceId.InsertNextId(len(face))  # The number of points in the face.
        [faceId.InsertNextId(i) for i in face]

    ugrid = vtk.vtkUnstructuredGrid()
    ugrid.SetPoints(points)
    ugrid.InsertNextCell(vtk.VTK_POLYHEDRON, faceId)
    return ugrid

def arrow(startPoint,length,direction,invert,color):
    """
    Draws and scales an arrow with a defined starting point, direction and length, adds to the renderer, returns the actor.
    """
    arrowSource=vtk.vtkArrowSource()
    arrowSource.SetShaftRadius(0.024)
    arrowSource.SetTipRadius(0.07)
    arrowSource.SetTipLength(0.14)
    arrowSource.SetTipResolution(20)
    arrowSource.SetShaftResolution(20)

    endPoint=(startPoint)+(length*direction)
    normalizedX=(endPoint-startPoint)/length

    
    arbitrary=np.array([1,1,1]) #can be replaced with a random vector
    normalizedZ=np.cross(normalizedX,arbitrary/np.linalg.norm(arbitrary))
    normalizedY=np.cross(normalizedZ,normalizedX)
    
    # Create the direction cosine matrix by writing values directly to an identity matrix
    matrix = vtk.vtkMatrix4x4()
    matrix.Identity()
    for i in range(3):
        matrix.SetElement(i, 0, normalizedX[i])
        matrix.SetElement(i, 1, normalizedY[i])
        matrix.SetElement(i, 2, normalizedZ[i])
        
    #Apply transforms
    transform = vtk.vtkTransform()
    transform.Translate(startPoint)
    transform.Concatenate(matrix)
    transform.Scale(length, length, length)
 
    # Transform the polydata
    transformPD = vtk.vtkTransformPolyDataFilter()
    transformPD.SetTransform(transform)
    transformPD.SetInputConnection(arrowSource.GetOutputPort())
    
    #Create mapper and actor
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(transformPD.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(color)
    
    if invert:
        arrowSource.InvertOn()
    else: arrowSource.InvertOff()
    arrowSource.Update()
    return actor

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widget = sgv_viewer()
    widget.show()
    sys.exit(app.exec_())