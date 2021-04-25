#build_plasticity model

from abaqus import *
from abaqusConstants import *
from caeModules import *
session.journalOptions.setValues(replayGeometry=COORDINATE, recoverGeometry=COORDINATE)

#roller diameter & width
t = 10 #thickness of blank
r1 = 2*t #roller1 diameter - 2t according to ISO 5173
r2 = 2*t #roller2&3 diameter, same as r1 (ISO 5173)
w = 25.0 # width of rollers
l = 160 #length of blank
d =  2*(3*t+2)#space between outer rollers, equal to die radius, must conform to a min. 4t+3, max. 5t (ISO 5173)
b_w = 20 #width of blank
i_clearance = 0
mesh_size = float(sys.argv[-1]) #mm

half_spacing1 = d/2 + r1
v_spacing1 = r1 + t/2 + i_clearance
half_spacing = d/2 + r2
v_spacing2 = r2 + t/2 + i_clearance
roller_positions = [(0,v_spacing1,0), (-half_spacing,-v_spacing2,0), (half_spacing,-v_spacing2,0)] #list of tuples corresponding to roller1,2 &3

##make parts
#make roller1
s1 = mdb.models['Model-1'].ConstrainedSketch(name='__profile__', 
    sheetSize=200.0)
g, v, d, c = s1.geometry, s1.vertices, s1.dimensions, s1.constraints
s1.setPrimaryObject(option=STANDALONE)
s1.ConstructionLine(point1=(0.0, -100.0), point2=(0.0, 100.0))
s1.FixedConstraint(entity=g.findAt((0.0, 0.0)))
s1.Line(point1=(r1, w/2), point2=(r1, -w/2))
s1.VerticalConstraint(entity=g.findAt((r1, 0.0)), addUndoState=False)
p = mdb.models['Model-1'].Part(name='Roller1', dimensionality=THREE_D, 
    type=ANALYTIC_RIGID_SURFACE)
p = mdb.models['Model-1'].parts['Roller1']
p.AnalyticRigidSurfRevolve(sketch=s1)
s1.unsetPrimaryObject()
p = mdb.models['Model-1'].parts['Roller1']
p.ReferencePoint(point=(0.0, 0.0, 0.0))
session.viewports['Viewport: 1'].setValues(displayedObject=p)
del mdb.models['Model-1'].sketches['__profile__']

#make roller1
s1 = mdb.models['Model-1'].ConstrainedSketch(name='__profile__', 
    sheetSize=200.0)
g, v, d, c = s1.geometry, s1.vertices, s1.dimensions, s1.constraints
s1.setPrimaryObject(option=STANDALONE)
s1.ConstructionLine(point1=(0.0, -100.0), point2=(0.0, 100.0))
s1.FixedConstraint(entity=g.findAt((0.0, 0.0)))
s1.Line(point1=(r2, w/2), point2=(r2, -w/2))
s1.VerticalConstraint(entity=g.findAt((r2, 0.0)), addUndoState=False)
p = mdb.models['Model-1'].Part(name='Roller23', dimensionality=THREE_D, 
    type=ANALYTIC_RIGID_SURFACE)
p = mdb.models['Model-1'].parts['Roller23']
p.AnalyticRigidSurfRevolve(sketch=s1)
s1.unsetPrimaryObject()
p = mdb.models['Model-1'].parts['Roller23']
p.ReferencePoint(point=(0.0, 0.0, 0.0))
session.viewports['Viewport: 1'].setValues(displayedObject=p)
del mdb.models['Model-1'].sketches['__profile__']

#make blank
s = mdb.models['Model-1'].ConstrainedSketch(name='__profile__', 
    sheetSize=200.0)
g, v, d, c = s.geometry, s.vertices, s.dimensions, s.constraints
s.setPrimaryObject(option=STANDALONE)
s.rectangle(point1=(-b_w/2, t/2), point2=(b_w/2, -t/2))
p = mdb.models['Model-1'].Part(name='Blank', dimensionality=THREE_D, 
    type=DEFORMABLE_BODY)
p = mdb.models['Model-1'].parts['Blank']
p.BaseSolidExtrude(sketch=s, depth=l)
s.unsetPrimaryObject()
p = mdb.models['Model-1'].parts['Blank']
session.viewports['Viewport: 1'].setValues(displayedObject=p)
del mdb.models['Model-1'].sketches['__profile__']


#create roller instances & move to positions
a = mdb.models['Model-1'].rootAssembly
a.DatumCsysByDefault(CARTESIAN)
p = mdb.models['Model-1'].parts['Roller1']
a.Instance(name='Roller-1', part=p, dependent=OFF)
a.rotate(instanceList=('Roller-1', ), axisPoint=(0.0, 0.0, 0.0), 
    axisDirection=(1, 0.0, 0.0), angle=90.0)
a.translate(instanceList=('Roller-1', ), vector=(0.0, v_spacing1, 0.0))


a = mdb.models['Model-1'].rootAssembly
p = mdb.models['Model-1'].parts['Roller23']
a.Instance(name='Roller-2', part=p, dependent=OFF)
a = mdb.models['Model-1'].rootAssembly
a.rotate(instanceList=('Roller-2', ), axisPoint=(0.0, 0.0, 0.0), 
    axisDirection=(1.0, 0.0, 0.0), angle=90.0)
a.translate(instanceList=('Roller-2', ), vector=(-half_spacing, -v_spacing2, 0.0))

a = mdb.models['Model-1'].rootAssembly
p = mdb.models['Model-1'].parts['Roller23']
a.Instance(name='Roller-3', part=p, dependent=OFF)
a = mdb.models['Model-1'].rootAssembly
a.rotate(instanceList=('Roller-3', ), axisPoint=(0.0, 0.0, 0.0), 
    axisDirection=(1.0, 0.0, 0.0), angle=90.0)
a.translate(instanceList=('Roller-3', ), vector=(half_spacing, -v_spacing2, 0.0))

#create blank instance and move to location
a = mdb.models['Model-1'].rootAssembly
p = mdb.models['Model-1'].parts['Blank']
a.Instance(name='Blank-1', part=p, dependent=OFF)
a = mdb.models['Model-1'].rootAssembly
a.rotate(instanceList=('Blank-1', ), axisPoint=(0.0, 0.0, 0.0), 
    axisDirection=(0.0, 1.0, 0.0), angle=90.0)
a.translate(instanceList=('Blank-1', ), vector=(-l/2, 0.0, 0.0))

#create surfaces
a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Roller-1'].faces
roller_surf = roller_positions[0]
side1Faces1 = s1.findAt(((roller_positions[0][0], roller_positions[0][1]+r1, roller_positions[0][2]), ))
a.Surface(side1Faces=side1Faces1, name='R1_SURF')

a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Roller-2'].faces
side1Faces1 = s1.findAt(((roller_positions[1][0]+r2, roller_positions[1][1], roller_positions[1][2]), ))
a.Surface(side1Faces=side1Faces1, name='R2_SURF')

a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Roller-3'].faces
roller_surf = roller_positions[0]
side1Faces1 = s1.findAt(((roller_positions[2][0]+r2, roller_positions[2][1], roller_positions[2][2]), ))
a.Surface(side1Faces=side1Faces1, name='R3_SURF')

#upper side of the blank
a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Blank-1'].faces
side1Faces1 = s1.findAt(((0, t/2, 0), ))
a.Surface(side1Faces=side1Faces1, name='TOP')

#lower side of the blank
a = mdb.models['Model-1'].rootAssembly
s1 = a.instances['Blank-1'].faces
side1Faces1 = s1.findAt(((0, -t/2, 0), ))
a.Surface(side1Faces=side1Faces1, name='BOTTOM')

#make sets
a = mdb.models['Model-1'].rootAssembly
a.DatumPlaneByPrincipalPlane(principalPlane=XYPLANE, offset=0.0) #15
a = mdb.models['Model-1'].rootAssembly
a.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=0.0) #16


#partition blank
a = mdb.models['Model-1'].rootAssembly
c = a.instances['Blank-1'].cells
pickedCells = c.findAt(((0, 0, 0), ))
d = a.datums
a.PartitionCellByDatumPlane(datumPlane=d[16], cells=pickedCells)

a = mdb.models['Model-1'].rootAssembly
c = a.instances['Blank-1'].cells
pickedCells = c.findAt(((0,0,2.5), ), ((0, 
    0, -2.5), ))
a.PartitionCellByDatumPlane(datumPlane=d[15], cells=pickedCells)

#create sets
a = mdb.models['Model-1'].rootAssembly
f = a.instances['Blank-1'].faces
faces1 = f.findAt(((-l/4, 0.0, 0.0), ), ((l/4, 0.0, 
    0.0), ))
a.Set(faces=faces1, name='xy_midplane')

faces2 = f.findAt(((0.0, 0.0, 2.5), ), ((0.0, 0.0, 
    -2.5), ))
a.Set(faces=faces2, name='yz_midplane')

c = a.instances['Blank-1'].cells
cells = c.findAt(((-l/4, 0.0, 2.5), ), ((-l/4, 0.0, 
    -2.5), ), ((l/4, 0.0, 2.5), ), ((l/4, 0.0, -2.5), ))
a.Set(cells=cells, name='all')


a = mdb.models['Model-1'].rootAssembly
#mesh controls/type
elemType = mesh.ElemType(elemCode=C3D8, elemLibrary=STANDARD, 
    secondOrderAccuracy=OFF, distortionControl=DEFAULT)
a.setElementType(regions=(cells, ), elemTypes=(elemType, elemType, elemType)) #because setElementType needs a tuple for elemTypes

#mesh size/seed
partInstances =(a.instances['Blank-1'], )
a.seedPartInstance(regions=partInstances, size=mesh_size, deviationFactor=0.1, minSizeFactor=0.1)
a.generateMesh(regions=partInstances)


session.viewports['Viewport: 1'].setValues(displayedObject=a)

mdb.models['Model-1'].setValues(noPartsInputFile=ON)


#write input
mdb.Job(name='U_plastic_mesh_only', model='Model-1', description='', type=ANALYSIS, 
    atTime=None, waitMinutes=0, waitHours=0, queue=None, memory=90, 
    memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True, 
    explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF, 
    modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='', 
    scratch='', resultsFormat=ODB, parallelizationMethodExplicit=DOMAIN, 
    numDomains=1, activateLoadBalancing=False, multiprocessingMode=DEFAULT, 
    numCpus=1, numGPUs=0)
mdb.jobs['U_plastic_mesh_only'].writeInput(consistencyChecking=OFF)
print "Wrote mesh"
