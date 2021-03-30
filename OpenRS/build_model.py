import numpy as np
from abaqus import *
from abaqusConstants import *
import sys
from caeModules import *
from driverUtils import executeOnCaeStartup
executeOnCaeStartup()

##Build part from imported step
step = mdb.openStep(
    sys.argv[-2], 
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
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=15) #4
p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=50) #5


#implement partitions, starting first with contact planes
c = p.cells
pickedCells = c.findAt(((0, 75, 0), ))
d = p.datums
p.PartitionCellByDatumPlane(datumPlane=d[4], cells=pickedCells)
#cell count now increased . . .
c = p.cells
pickedCells = c.findAt(((0, 75, 0), ))
p.PartitionCellByDatumPlane(datumPlane=d[5], cells=pickedCells)
#central partitions
c = p.cells
pickedCells = c.findAt(((0, 75, 0), ))
p.PartitionCellByDatumPlane(datumPlane=d[3], cells=pickedCells)
c = p.cells
pickedCells = c.findAt(((0, 75, -5), ), ((0, 
    75, 5), ))
p.PartitionCellByDatumPlane(datumPlane=d[2], cells=pickedCells)

c = p.cells
pickedCells = c.findAt(((-25, 5, 0), ), ((25, 
    5, 0), ))
v = p.vertices
p.PartitionCellByPlaneThreePoints(point1=v.findAt(coordinates=(-30.0, 10.0, 
    10.0)), point2=v.findAt(coordinates=(30.0, 10.0, 10.0)), point3=v.findAt(
    coordinates=(30.0, 10.0, -10.0)), cells=pickedCells)

c = p.cells
pickedCells = c.findAt(((-29, 40, 0), ), ((29, 
    40, 0), ))
p.PartitionCellByPlaneThreePoints(point1=v.findAt(coordinates=(-30.0, 20.0, 
    10.0)), point2=v.findAt(coordinates=(30.0, 20.0, 10.0)), point3=v.findAt(
    coordinates=(30.0, 20.0, -10.0)), cells=pickedCells)

#cells containing datum features
f = p.faces
c = p.cells
pickedCells = c.findAt(((25, 45, 0), ))
p.PartitionCellByExtendFace(extendFace=f.findAt(coordinates=(26, 45.0, 
    0)), cells=pickedCells)
c = p.cells
pickedCells = c.findAt(((-25, 45, 0), ))
p.PartitionCellByExtendFace(extendFace=f.findAt(coordinates=(-26, 45.0, 
    0)), cells=pickedCells)



a.regenerate() #important to run in order to update partitions done at the part level to get over to the assembly level

#create geometric sets and surfaces
e = a.instances['U_elastic'].edges
edges = e.findAt(((-28, 15, 6), ), ((-28, 
    15, -6), ))
a.Set(edges=edges, name='left')


edges = e.findAt(((28, 15, 6), ), ((28, 
    15, -6), ))
a.Set(edges=edges, name='right')
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


edges = e.findAt(((0.0, 75.0, 0.0), ))
a.Set(edges=edges, name='output')

c = a.instances['U_elastic'].cells
cells = c.findAt(((-25, 7.5, 0), ), ((25, 7.5, 
    0), ), ((-25, 22.5, 0), ), ((25, 22.5, 
    0), ), ((-1, 75, -5), ), ((-1, 75, 
    5), ), ((1, 75, -5), ), ((1, 75, 
    5), ), ((-25,11,9), ), ((25,11,
    9), ),((-25,19,9), ), ((25, 19,
    9), ), ((-25,11,-9), ), ((25,11,
    -9), ),((-25,19,-9), ), ((25, 19,
    -9), ),((-29, 40, 2.5), ), (( 29, 40,
    2.5), ))
a.Set(cells=cells, name='all')

f = a.instances['U_elastic'].faces
faces = f.findAt(((-2.0, 76.0, 0.0), ), ((2.0, 76.0, 
    0.0), ))
a.Set(faces=faces, name='midplane_xy')

faces = f.findAt(((0, 76.0, 2.5), ), ((0, 76.0, 
    -2.5), ))
a.Set(faces=faces, name='midplane_zy')

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

#rigid body node
v = a.instances['U_elastic'].vertices
verts = v.findAt(((0.0, 80.0, 0.0), ))
a.Set(vertices=verts, name='rigid')



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
