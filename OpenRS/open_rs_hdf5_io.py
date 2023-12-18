#!/usr/bin/env python

'''
Helper functions and classes for passing VTK data to and from HDF5 for OpenRS

Berk Geveci's classes to write and read VTK unstructured grids to HDF5: from 'Developing HDF5 readers using vtkPythonAlgorithm', 2014 and 'HDF5 Reader and Writer for Unstructured Grids', 2015
https://blog.kitware.com/hdf5-reader-and-writer-for-unstructured-grids/

Modified for OpenRS' 'model' group and overwrite support.
'''

import os
import vtk
import h5py
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase
from vtk.numpy_interface import dataset_adapter as dsa
import numpy as np
from datetime import datetime
from OpenRS.open_rs_common import get_save_file

def initialize_HDF5(file=None):
    '''
    Create an HDF5 file with relevant empty structures.
    '''
    if file is None:
        #launch get_save_file
        file, _ = get_save_file('*.OpenRS')
    
    if file is None:
            return

    with h5py.File(file, 'w') as f:
        f.attrs['date_created'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        # f.attrs['version'] = __version__
        
        #create model group
        # model = f.create_group("model_data")
        boundary = f.create_group("model_boundary")
        boundary.create_dataset("points", data=h5py.Empty("f"))
        boundary.create_dataset("vertices", data=h5py.Empty("f"))
        boundary.create_dataset("transform", data=h5py.Empty("f"))
        
        #create fiducial group
        fid = f.create_group("fiducials")
        fid.create_dataset("enabled", data=h5py.Empty("bool"))
        fid.create_dataset("points", data=h5py.Empty("f"))
        
        #create measurement group
        meas = f.create_group("measurement_points")
        meas.create_dataset("enabled", data=h5py.Empty("bool"))
        meas.create_dataset("points", data=h5py.Empty("f"))
        
        #create the sample group
        sample = f.create_group("sample")
        sample.create_dataset("points", data=h5py.Empty("f"))
        sample.create_dataset("vertices", data=h5py.Empty("f"))
        sample.create_dataset("transform", data=h5py.Empty("f"))
        
        #create sgv group
        sgv = f.create_group("sgv")
        
        f.attrs['date_modified'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    
    return file
    

class HDF5vtkug_writer(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(self, \
        nInputPorts=1, \
        inputType='vtkUnstructuredGrid', \
        nOutputPorts=0)
 
        self.__FileName = ""
        self.__NumberOfPieces = 1
        self.__CurrentPiece = 0


    def RequestData(self, request, inInfo, outInfo):
        info = inInfo[0].GetInformationObject(0)
        inp = dsa.WrapDataObject(vtk.vtkDataSet.GetData(info))
 
        if self.__CurrentPiece == 0:
            self.__File = h5py.File(self.__FileName, 'r+')
            if "model" in self.__File:
                del self.__File["model_data"]
        
        model = self.__File.create_group("model_data")
        grp = model.create_group("piece%d" % self.__CurrentPiece)
        grp.attrs['bounds'] = inp.GetBounds()
 
        grp.create_dataset("cells", data=inp.Cells)
        grp.create_dataset("cell_types", data=inp.CellTypes)
        grp.create_dataset("cell_locations", data=inp.CellLocations)
 
        grp.create_dataset("points", data=inp.Points)
 
        pdata = grp.create_group("point_data")
        for name in inp.PointData.keys():
            pdata.create_dataset(name, data=inp.PointData[name])
        
        self.__File.attrs['date_modified'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        
        if self.__CurrentPiece < self.__NumberOfPieces - 1:
            # If we are not done, ask the pipeline to re-execute us.
            self.__CurrentPiece += 1
            request.Set(
                vtk.vtkStreamingDemandDrivenPipeline.CONTINUE_EXECUTING(),
                1)
        else:
            # Stop execution
            request.Remove(
                vtk.vtkStreamingDemandDrivenPipeline.CONTINUE_EXECUTING())
            self.__File.close()
            del self.__File
        return 1
 
    def RequestInformation(self, request, inInfo, outInfo):
        # Reset values.
        self.__CurrentPiece = 0
        return 1
 
    def RequestUpdateExtent(self, request, inInfo, outInfo):
        info = inInfo[0].GetInformationObject(0)
        info.Set(
            vtk.vtkStreamingDemandDrivenPipeline.UPDATE_NUMBER_OF_PIECES(),
            self.__NumberOfPieces)
        info.Set(
            vtk.vtkStreamingDemandDrivenPipeline.UPDATE_PIECE_NUMBER(),
            self.__CurrentPiece)
        return 1
 
    def SetFileName(self, fname):
        if fname != self.__FileName:
            self.Modified()
            self.__FileName = fname
 
    def GetFileName(self):
        return self.__FileName
 
    def SetNumberOfPieces(self, npieces):
        if npieces != self.__NumberOfPieces:
            self.Modified()
            self.__NumberOfPieces = npieces
 
    def GetNumberOfPieces(self):
        return self.__NumberOfPieces

class HDF5vtkpd_writer(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(self, \
        nInputPorts=1, \
        inputType='vtkPolyData', \
        nOutputPorts=0)
 
        self.__FileName = ""
        self.__NumberOfPieces = 1
        self.__CurrentPiece = 0


    def RequestData(self, request, inInfo, outInfo):
        info = inInfo[0].GetInformationObject(0)
        inp = dsa.WrapDataObject(vtk.vtkDataSet.GetData(info))
 
        if self.__CurrentPiece == 0:
            self.__File = h5py.File(self.__FileName, 'r+')
            if "model" in self.__File:
                del self.__File["model_data"]
        
        model = self.__File.create_group("model_data")
        grp = model.create_group("piece%d" % self.__CurrentPiece)
        grp.attrs['bounds'] = inp.GetBounds()
 
        # grp.create_dataset("cells", data=inp.Cells)
        
        # grp.create_dataset("cell_locations", data=inp.CellLocations)
 
        grp.create_dataset("points", data=inp.Points)
 
        pdata = grp.create_group("point_data")
        for name in inp.PointData.keys():
            pdata.create_dataset(name, data=inp.PointData[name])
        
        self.__File.attrs['date_modified'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        
        if self.__CurrentPiece < self.__NumberOfPieces - 1:
            # If we are not done, ask the pipeline to re-execute us.
            self.__CurrentPiece += 1
            request.Set(
                vtk.vtkStreamingDemandDrivenPipeline.CONTINUE_EXECUTING(),
                1)
        else:
            # Stop execution
            request.Remove(
                vtk.vtkStreamingDemandDrivenPipeline.CONTINUE_EXECUTING())
            self.__File.close()
            del self.__File
        return 1
 
    def RequestInformation(self, request, inInfo, outInfo):
        # Reset values.
        self.__CurrentPiece = 0
        return 1
 
    def RequestUpdateExtent(self, request, inInfo, outInfo):
        info = inInfo[0].GetInformationObject(0)
        info.Set(
            vtk.vtkStreamingDemandDrivenPipeline.UPDATE_NUMBER_OF_PIECES(),
            self.__NumberOfPieces)
        info.Set(
            vtk.vtkStreamingDemandDrivenPipeline.UPDATE_PIECE_NUMBER(),
            self.__CurrentPiece)
        return 1
 
    def SetFileName(self, fname):
        if fname != self.__FileName:
            self.Modified()
            self.__FileName = fname
 
    def GetFileName(self):
        return self.__FileName
 
    def SetNumberOfPieces(self, npieces):
        if npieces != self.__NumberOfPieces:
            self.Modified()
            self.__NumberOfPieces = npieces
 
    def GetNumberOfPieces(self):
        return self.__NumberOfPieces

class HDF5vtkug_reader(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(self,
            nInputPorts=0,
            nOutputPorts=1, outputType='vtkMultiBlockDataSet')
 
        self.__FileName = ""
 
    def RequestData(self, request, inInfo, outInfo):
        output = dsa.WrapDataObject(vtk.vtkMultiBlockDataSet.GetData(outInfo))
        f = h5py.File(self.__FileName, 'r')
        idx = 0
        data = f["model_data"]
        for grp_name in data:
            ug = vtk.vtkUnstructuredGrid()
            output.SetBlock(idx, ug)
            idx += 1
            ug = dsa.WrapDataObject(ug)
            grp = data[grp_name]
            cells = grp['cells'][:]
            locations = grp['cell_locations'][:]
            types = grp['cell_types'][:]
            ug.SetCells(types, locations, cells)
            pts = grp['points'][:]
            ug.Points = pts
            pt_arrays = grp['point_data']
            for pt_array in pt_arrays:
                array = pt_arrays[pt_array][:]
                ug.PointData.append(array, pt_array)
 
        return 1
 
    def SetFileName(self, fname):
        if fname != self.__FileName:
            self.Modified()
            self.__FileName = fname
 
    def GetFileName(self):
        return self.__FileName

class HDF5vtkpd_reader(VTKPythonAlgorithmBase):
    def __init__(self):
        VTKPythonAlgorithmBase.__init__(self,
            nInputPorts=0,
            nOutputPorts=1, outputType='vtkMultiBlockDataSet')
 
        self.__FileName = ""
 
    def RequestData(self, request, inInfo, outInfo):
        output = dsa.WrapDataObject(vtk.vtkMultiBlockDataSet.GetData(outInfo))
        f = h5py.File(self.__FileName, 'r')
        idx = 0
        data = f["model_data"]
        for grp_name in data:
            pd = vtk.vtkPolyData()
            output.SetBlock(idx, pd)
            idx += 1
            pd = dsa.WrapDataObject(pd)
            grp = data[grp_name]
            pts = grp['points'][:]
            pd.Points = pts
            pt_arrays = grp['point_data']
            verts = vtk.vtkCellArray()
            for i in np.arange(len(pts)):
                verts.InsertNextCell(1)
                verts.InsertCellPoint(i)
            pd.SetVerts(verts)
            
            for pt_array in pt_arrays:
                array = pt_arrays[pt_array][:]
                pd.PointData.append(array, pt_array)
 
        return 1
 
    def SetFileName(self, fname):
        if fname != self.__FileName:
            self.Modified()
            self.__FileName = fname
 
    def GetFileName(self):
        return self.__FileName