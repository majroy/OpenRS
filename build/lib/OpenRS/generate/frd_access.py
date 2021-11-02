'''
Python script for extracting stresses at nodes of a C3D8 formulation conducted by CalculiX. Output: ascii based *.vtu or legacy *.vtk file depending on `outfile` extension. Both will consisting of deformed mesh and scalar fields at S11, S22, S33. Further extracts deformed positions of fiducial points specified to a text file which are read from a companion *.dat file. Input frd, dat and output directory are arguments.
(c) M. J. Roy 2021
'''
import sys
import os.path
import numpy as np
from itertools import islice

def postprocess(frdname,outfile,fiducial_file):

    #debug (script treatment)
    # np.set_printoptions(precision=3,suppress=True)
    #check if incoming odb file is valid. Use try/catch for valid directory. Assumes dat file has same prefix as frd file.
    # frdname = sys.argv[1]
    # outfile = sys.argv[2]
    # fiducial_file = sys.argv[3]

    datname, _ = os.path.splitext(frdname)
    datname = datname + '.dat'

    if not os.path.isfile(frdname):
        sys.exit("Specified frd file to frd_access not valid.")

    #read file and get line numbers with key values identifying output
    i=0
    lineFlag=[]
    keyStrings=["    2C", "    3C", " -4  DISP", " -4  STRESS", " -3"]

    fid = open(frdname)
    while 1:
        lines = fid.readlines(100000)
        if not lines:
            break
        for line in lines:
            i+=1
            for keyString in keyStrings:
                if line[0:len(keyString)]==keyString:
                    lineFlag.append(i)
                
    fid.close()

    #read nodal data
    a = np.genfromtxt(frdname,
        delimiter = (3,10,12,12,12),
        skip_header=lineFlag[0], max_rows=lineFlag[1]-lineFlag[0]-1)
    node_array = a[:,1::] #node number, x,y,z coords

    n_nodes = np.size(node_array, 0)
    n_elements = int((lineFlag[3]-1 - lineFlag[2])/2) #Could also be read directly from '3C' flag

    #preallocate numpy array
    element_array = np.zeros([n_elements,9]) #C3D8
    #read element data using isslice, could be optimised with regex
    with open(frdname) as fid:
        lines = islice(fid,lineFlag[2],lineFlag[3]-1)
        e_num = 0
        for line in lines:
            l = np.array([int(i) for i in line.split()])
            #capture lines that once split have 8 values (C3D8)
            if l[0] == -1: #then element declaration
                e_num = l[1]
                element_array[e_num-1,0] = e_num-1 #cell numbering in vtk is 0 based
            if l[0] == -2 and e_num != 0:#then connectivity of element number declared the line above
                element_array[e_num-1,1::] = l[1::]-1 #node numbering in vtk is 0 based

    vtk_element_array = element_array
    vtk_element_array[:,0] = 8 #quads

    #read displacement data and add to node_array
    a = np.genfromtxt(frdname,
        delimiter = (3,10,12,12,12),
        skip_header=lineFlag[4]+4, max_rows=lineFlag[5]-1-(lineFlag[4]+4))
        
    for row in a:
        node_array[int(row[1])-1,1::] = node_array[int(row[1])-1,1::] + row[2::]

    #read averaged stresses
    a = np.genfromtxt(frdname,
        delimiter = (3,10,12,12,12,12,12,12),
        skip_header=lineFlag[6]+6, max_rows=lineFlag[7]-1-(lineFlag[6]+6))
    stress_avg_array = a[:,2:5] #SXX/S11, SYY/S22, SZZ/S33


    #write output
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

    #get deformed datum coodinates
    lld = 'left_lower_datum'.upper()
    lud = 'left_upper_datum'.upper()
    rud = 'right_upper_datum'.upper()
    rld = 'right_lower_datum'.upper()
    datum_nodeSets = [lld, lud, rud, rld] #list of nodeSets

    #identify lines which contain 'displacements'
    keyStrings = [" displacements", " stresses"]
    lineFlag = []
    fid = open(datname)
    i=0
    while 1:
        lines = fid.readlines(100000)
        if not lines:
            break
        for line in lines:
            i+=1
            for keyString in keyStrings:
                if line[0:len(keyString)]==keyString:
                    lineFlag.append(i)
    fid.close()

    with open(fiducial_file, "w+") as f:

        for i in range(len(datum_nodeSets)):
            disp_array = np.genfromtxt(datname,
                delimiter = (10,14,14,14),
                skip_header=lineFlag[i]+1, max_rows=lineFlag[i+1]-2-(lineFlag[i]+1))#additional ints are for whitespace
            
            for row in disp_array:
                #add displacement to starting node position
                disp_array[disp_array[:,0]==row[0],1::] = node_array[int(row[0])-1,1::]+[row[1],row[2],row[3]]
            f.write('U_%s\n'%datum_nodeSets[i]) #'U_' required to identify as datum for main postprocessor
            np.savetxt(f,disp_array)
            
    print('Wrote %s.'%fiducial_file)
