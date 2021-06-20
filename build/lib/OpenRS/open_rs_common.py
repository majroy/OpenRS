#!/usr/bin/env python

'''
Common functions for OpenRS
'''

import os
import vtk
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy as v2n
from PyQt5 import QtGui, QtWidgets, QtCore
from pkg_resources import Requirement, resource_filename


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

def generate_info_actor(ren,message):
    '''
    Returns an information actor comprised of the incoming message string on the specified renderer
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
    ren.AddActor(info_actor)
    
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

def line_query(output,q1,q2,numPoints,component):
    """
    Interpolate the data from output over q1 to q2 (list of x,y,z)
    """
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
    q = v2n(probe.GetOutput().GetPointData().GetArray(component))

    return q

def get_save_file(ext):
    '''
    Returns a the complete path to the file name with ext, starting in outputd. Checks extensions and if an extension is not imposed, it will write the appropriate extension based on ext.
    '''
    ftypeName={}
    ftypeName['*.csv']='OpenRS comma delimited output file'
    ftypeName['*.txt']='OpenRS whitespace delimited output file'
    ftypeName['*.OpenRS'] = 'OpenRS HDF5-format data file'

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
    ext = args[0]
    if len(args)>1:
        launchdir = args[1]
    else: launchdir = os.getcwd()
    ftypeName={}
    ftypeName['*.vtu']=["OpenRS VTK unstructured grid (XML format)", "*.vtu", "VTU file"]
    ftypeName['*.stl']=["OpenRS STL", "*.stl","STL file"]
    ftypeName['*.OpenRS'] = ["OpenRS HDF5-format data file", "*.OpenRS", "OpenRS file"]
    ftypeName['*.txt'] = ["OpenRS whitespace delimited points", "*.txt", "OpenRS text input"]
        
    filer = QtWidgets.QFileDialog.getOpenFileName(None, ftypeName[ext][0], 
         os.getcwd(),(ftypeName[ext][2]+' ('+ftypeName[ext][1]+');;All Files (*.*)'))

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