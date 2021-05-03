'''
Abaqus Python script for extracting stresses at nodes of a C3D8 mesh. Output: ascii based *.vtu or legacy *.vtk file depending on `outfile` extension. Both will consisting of deformed mesh and scalar fields at S11, S22, S33. Input odb and output directory are arguments.
(c) M. J. Roy 2021
'''
import sys
import os.path
import numpy as np
from odbAccess import *

#check if incoming odb file is valid. Use try/catch for valid directory.
odbname = sys.argv[1]
outfile = sys.argv[2]

if not os.path.isfile(odbname):
    sys.exit("Specified odb file to odb_access not valid.")


odb = openOdb(odbname,readOnly=True)
print "ODB opened"

#access geometry and topology information ( odb->rootAssembly->instances->(nodes, elements) )
rootassembly = odb.rootAssembly
instance = rootassembly.instances
print instance

#access attribute information
step = odb.steps

allinstancestr = str(instance)
autoins = allinstancestr.split("'")
instancename = autoins[1]
print instancename

es = instance[instancename].elementSets['ALL']
ns = instance[instancename].nodeSets['ALL']
print(es)
print(ns)

#----------------------------------------------------

# node = instance[instancename].nodes
# element = instance[instancename].elements

node = ns.nodes
element = es.elements

n_nodes = len(node)
n_elements = len(element)
print n_nodes, n_elements

allstepstr = str(step)
autostep = allstepstr.split("'")
stepname = autostep[1] #only 'named' step

N_Frame = odb.steps[stepname].frames[-1] #last frame
print 'frame', N_Frame
d = N_Frame.fieldOutputs['U']
Displacement = d.getSubset(region=ns)

#create np array containing nodeLabel and baseline x, y, z
node_array = np.zeros([n_nodes,4])
for n in node:
    node_array[n.label-1,:]=[n.label,n.coordinates[0],n.coordinates[1],n.coordinates[2]]

#get displacements and add to base coordinates for deformed locations
for value in Displacement.values:
    node_array[value.nodeLabel-1,1::] = node_array[value.nodeLabel-1,1::] + value.data

#get element data
element_array = np.zeros([n_elements,len(element[0].connectivity)+1])
for e in element:
    con = np.asarray([i for i in e.connectivity])
    element_array[e.label-1,0] = e.label
    element_array[e.label-1,1::] = con-1 #vtk node numbering starts at 0, not 1
    
vtk_element_array = element_array
vtk_element_array[:,0] = 8 #quads

#access Stress components
Stress = N_Frame.fieldOutputs['S']
node_Stress = Stress.getSubset(position=ELEMENT_NODAL)
fieldValues = node_Stress.values


#read stresses at nodes on elemental basis
stress_array = np.zeros([n_nodes,4]) #Nxcount,culmulative S11,S22, S33
for entry in fieldValues:
    stress_array[entry.nodeLabel-1,0]+=1
    stress_array[entry.nodeLabel-1,1]+=entry.data[0]
    stress_array[entry.nodeLabel-1,2]+=entry.data[1]
    stress_array[entry.nodeLabel-1,3]+=entry.data[2]

print stress_array, len(stress_array)
#average stresses at nodes
stress_avg_array = np.zeros([n_nodes,3])
for i in range(3):
    stress_avg_array[:,i] = stress_array[:,i+1]/stress_array[:,0]
    
if outfile.endswith('.vtk'):
    fid=open(outfile,'w+')
    fid.write('# vtk DataFile Version 2.0\n')
    fid.write('%s,created by OpenRS\n'%outfile[:-4])
    fid.write('ASCII\n')
    fid.write('DATASET UNSTRUCTURED_GRID\n')
    fid.write('POINTS %i double\n'%n_nodes)
    np.savetxt(fid,node_array[:,1::],fmt='%.6f')
    fid.write('\n')

    fid.write('CELLS %i %i\n'%(n_elements,np.size(element_array)))
    np.savetxt(fid,vtk_element_array,fmt='%i')
    fid.write('\n')

    fid.write('CELL_TYPES %i\n'%n_elements)
    CellType=np.ones([n_elements,1])*12 #quads
    np.savetxt(fid,CellType,fmt='%i')
    fid.write('\n')

    fid.write('POINT_DATA %i\n'%n_nodes)
    for i in range(3):
        fid.write('SCALARS S%s%s float 1\n'%(i+1,i+1))
        fid.write('LOOKUP_TABLE DEFAULT\n')
        np.savetxt(fid,stress_avg_array[:,i])
    
    fid.close()

#write a vtu file (preferred)
elif outfile.endswith('.vtu'):
    fid=open(outfile,'w+')
    fid.write('<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" header_type="UInt32" compressor="vtkZLibDataCompressor">\n<UnstructuredGrid><Piece NumberOfPoints="%i" NumberOfCells="%i">\n'%(n_nodes,n_elements))
    fid.write('<PointData>\n')
    #now point data (stresses at nodes)    
    for i in range(3):
        fid.write('<DataArray Name="S%s%s" type="Float64" format="ASCII">\n'%(i+1,i+1))
        np.savetxt(fid,stress_avg_array[:,i])
        fid.write('</DataArray>\n')
    fid.write('</PointData>\n')
    #write node coordinates
    fid.write('<Points>\n<DataArray type="Float64" Name="Points" NumberOfComponents="3" format="ascii" RangeMin="%f" RangeMax="%f">\n'%(np.min(node_array[:,1::]),np.max(node_array[:,1::])))
    np.savetxt(fid,node_array[:,1::],fmt='%.6f')
    fid.write('</DataArray>\n</Points>')

    fid.write('<Cells>\n <DataArray type="Int64" Name="connectivity" format="ascii" RangeMin="%i" RangeMax="%i">\n'%(0,n_nodes+1))
    np.savetxt(fid,vtk_element_array[:,1::],fmt='%i')
    fid.write('</DataArray>\n<DataArray type="Int64" Name="offsets" format="ascii" RangeMin="%i" RangeMax="%i">\n'%(8,8*n_elements))
    offsets = np.asarray([i * 8 for i in range(n_elements+1)])
    np.savetxt(fid,offsets[1::],fmt='%i')
    fid.write('</DataArray>\n<DataArray type="UInt8" Name="types" format="ascii" RangeMin="%i" RangeMax="%i">\n'%(12,12))
    types = np.asarray([12 for i in range(n_elements+1)])
    np.savetxt(fid,types,fmt='%i')

    fid.write('</DataArray>\n</Cells>\n</Piece>\n</UnstructuredGrid>\n</VTKFile>')
    fid.close()
else:
    sys.exit("Specified output file for odb_access not valid.")

print('Wrote %s.'%outfile)

odb.close()