'''
Abaqus Python script for generating a mesh based on elastically loaded EASI-STRESS U-bend samples.
Run with 'abaqus noGUI=build_model.py STEPFILE MESHDENSITY
STEPFILE prefix should end with 'imp_fid', otherwise script will look for explicit datum features (cylindrical bores) to create geometry-based sets, rather than specific nodes.
(c) M. J. Roy 2021
'''

import numpy as np
from abaqus import *
from abaqusConstants import *
import sys
from caeModules import *
from driverUtils import executeOnCaeStartup
executeOnCaeStartup()

explicit_datums = True
if 'imp_fid' in sys.argv[-2]:
    explicit_datums = False

##Build part from imported step
step = mdb.openStep(sys.argv[-2], 
    scaleFromFile=OFF)
mdb.models['Model-1'].PartFromGeometryFile(name='U_elastic', 
    geometryFile=step, combine=False, dimensionality=THREE_D, 
    type=DEFORMABLE_BODY)
mdb.models['Model-1'].setValues(noPartsInputFile=ON)
p = mdb.models['Model-1'].parts['U_elastic']
a = mdb.models['Model-1'].rootAssembly
a.Instance(name='U_elastic', part=p, dependent=OFF)
session.journalOptions.setValues(replayGeometry=COORDINATE, recoverGeometry=COORDINATE)

##Partition
#create xy, yz plane
p = mdb.models['Model-1'].parts['U_elastic']
p.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=0.0) #2
p.DatumPlaneByPrincipalPlane(principalPlane=XYPLANE, offset=0.0) #3
#create contact datum planes
#root of notch is -2 mm (x) +15 (y) mm from origin
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=10) #4
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=15) #5
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=20) #6
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=25) #7
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=45) #8
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=50) #9
p.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=26) #10
p.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=-26) #11


c = p.cells
pickedCells = c.findAt(((0, 75, 0), ))
# d = p.datums
p.PartitionCellByDatumPlane(datumPlane=p.datums[3], cells=pickedCells)
c = p.cells
pickedCells = c.findAt(((-25, 40, -5), ), ((-25, 
    40, 5), ))
p.PartitionCellByDatumPlane(datumPlane=p.datums[4], cells=pickedCells)
c = p.cells
pickedCells = c.findAt(((-25, 40, -5), ), ((-25, 
    40, 5), ), ((25, 40, -5), ), ((25, 40, 5), ))
p.PartitionCellByDatumPlane(datumPlane=p.datums[5], cells=pickedCells)

c = p.cells
pickedCells = c.findAt(((-25, 40, -5), ), ((-25, 
    40, 5), ), ((25, 40, -5), ), ((25, 40, 5), ))
p.PartitionCellByDatumPlane(datumPlane=p.datums[6], cells=pickedCells)

c = p.cells
pickedCells = c.findAt(((-25, 40, -5), ), ((-25, 
    40, 5), ), ((25, 40, -5), ), ((25, 40, 5), ))
p.PartitionCellByDatumPlane(datumPlane=p.datums[9], cells=pickedCells)

f = p.faces
pickedFaces = f.findAt(((25, 40.0, 0.0), ),((-25, 40.0, 0.0), ))
p.PartitionFaceByDatumPlane(datumPlane=p.datums[7], faces=pickedFaces)

f = p.faces
pickedFaces = f.findAt(((25, 40.0, 0.0), ), ((-25, 40.0, 0.0), ))
p.PartitionFaceByDatumPlane(datumPlane=p.datums[8], faces=pickedFaces)

f = p.faces
pickedFaces = f.findAt(((25, 40.0, 0.0), ))
p.PartitionFaceByDatumPlane(datumPlane=p.datums[10], faces=pickedFaces)

f = p.faces
pickedFaces = f.findAt(((-25, 40.0, 0.0), ))
p.PartitionFaceByDatumPlane(datumPlane=p.datums[11], faces=pickedFaces)

f = p.faces
pickedFaces = f.findAt(((0, 75, 0.0), ))
p.PartitionFaceByDatumPlane(datumPlane=p.datums[2], faces=pickedFaces)



a.regenerate() #important to run in order to update partitions done at the part level to get over to the assembly level

#create geometric sets and surfaces
e = a.instances['U_elastic'].edges
edges = e.findAt(((-28, 15, 6), ), ((-28, 
    15, -6), ))
a.Set(edges=edges, name='left')
edges = e.findAt(((28, 15, 6), ), ((28, 
    15, -6), ))
a.Set(edges=edges, name='right')
edges = e.findAt(((-11.480503, 77.716386, 0.0), ), ((27.716386, 61.480503, 
    0.0), ))
a.Set(edges=edges, name='xy_outer')

#fiducial mounting features - either there are holes, or there aren't. Find at will fail in the latter
if explicit_datums:
    edges = e.findAt(((-30, 46, 0), ), ((-30, 
        44, 0), ), (( -26, 46, 0),), (( -26, 44, 0),))
    a.Set(edges=edges, name='left_upper_datum')
    edges = e.findAt(((-30, 26, 0), ), ((-30, 
        24, 0), ), (( -26, 26, 0),), (( -26, 24, 0),))
    a.Set(edges=edges, name='left_lower_datum')
    edges = e.findAt(((30, 46, 0), ), ((30, 
        44, 0), ), (( 26, 46, 0),), (( 26, 44, 0),))
    a.Set(edges=edges, name='right_upper_datum')
    edges = e.findAt(((30, 26, 0), ), ((30, 
        24, 0), ), (( 26, 26, 0),), (( 26, 24, 0),))
    a.Set(edges=edges, name='right_lower_datum')
else:
    print 'Not using explicit fiducial features . . .'
    edges = e.findAt(((-29, 25, 0.0), ))
    a.Set(edges=edges, name='left_lower_datum')
    edges = e.findAt(((-29, 45, 0.0), ))
    a.Set(edges=edges, name='left_upper_datum')
    edges = e.findAt(((29, 25, 0.0), ))
    a.Set(edges=edges, name='right_lower_datum')
    edges = e.findAt(((29, 45, 0.0), ))
    a.Set(edges=edges, name='right_upper_datum')



c = a.instances['U_elastic'].cells
cells = c.findAt(((-25, 7.5, 2.5), ), ((25, 7.5, 
    2.5), ), ((-25, 7.5, -2.5), ), ((25, 7.5, 
    -2.5), ), ((-25, 22.5, 0), ), ((25, 22.5, 
    0), ), ((-1, 75, -5), ), ((-1, 75, 
    5), ), ((1, 75, -5), ), ((1, 75, 
    5), ), ((-25,11,9), ), ((25,11,
    9), ),((-25,19,9), ), ((25, 19,
    9), ), ((-25,11,-9), ), ((25,11,
    -9), ),((-25,19,-9), ), ((25, 19,
    -9), ),((-29, 40, 2.5), ), (( 29, 40,
    2.5), ), ((-29, 40, -2.5), ), (( 29, 40,
    -2.5), ))
a.Set(cells=cells, name='all')

f = a.instances['U_elastic'].faces
faces = f.findAt(((-2.0, 76.0, 0.0), ), ((2.0, 76.0, 
    0.0), ))
a.Set(faces=faces, name='midplane_xy')

faces = f.findAt(((-29,12.5,7.0), ), ((-29, 17.5, 
    7.0), ))
a.Surface(side1Faces=faces, name='left_outer')

faces = f.findAt(((-21,12.5,7.0), ), ((-21, 17.5, 
    7.0), ))
a.Surface(side1Faces=faces, name='left_inner')

faces = f.findAt(((21,12.5,7.0), ), ((21, 17.5, 
    7.0), ))
a.Surface(side1Faces=faces, name='right_inner')

faces = f.findAt(((29,12.5,7.0), ), ((29, 17.5, 
    7.0), ))
a.Surface(side1Faces=faces, name='right_outer')


#mesh controls/type
elemType = mesh.ElemType(elemCode=C3D8, elemLibrary=STANDARD, 
    secondOrderAccuracy=OFF, distortionControl=DEFAULT)
a.setElementType(regions=(cells, ), elemTypes=(elemType, elemType, elemType)) #because setElementType needs a tuple for elemTypes

##mesh
partInstances =(a.instances['U_elastic'], )
a.seedPartInstance(regions=partInstances, size=float(sys.argv[-1]), deviationFactor=0.1, minSizeFactor=0.1)
a.generateMesh(partInstances)

session.viewports['Viewport: 1'].setValues(displayedObject=a)

#write input
mdb.Job(name='U_elastic_mesh_only', model='Model-1', description='', type=ANALYSIS, 
    atTime=None, waitMinutes=0, waitHours=0, queue=None, memory=90, 
    memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True, 
    explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF, 
    modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='', 
    scratch='', resultsFormat=ODB, parallelizationMethodExplicit=DOMAIN, 
    numDomains=1, activateLoadBalancing=False, multiprocessingMode=DEFAULT, 
    numCpus=1, numGPUs=0)
mdb.jobs['U_elastic_mesh_only'].writeInput(consistencyChecking=OFF)
print "Wrote mesh"
