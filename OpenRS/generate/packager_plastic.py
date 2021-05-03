'''
Python script for generating a model of an EASI-STRESS plastically deformed U-bend specimen. The script operates sequentially according to:
1) Runs an Abaqus Python preprocessing script "build_model.py" with Abaqus CAE to generate an abaqus input deck without material assignment or boundary conditions (a mesh). build_model.py requires the arguments of a provided *.STEP file, and global mesh size/density.
2) Appends boundary conditions and material properties to the input deck generated in (1), generates an input deck with material properties and boundary conditions, and submits it to the Abaqus solver.
3) The resulting output database from (2) is processed with an Abaqus Python script "odb_access.py", which generates an ASCII-based *.vtu (VTK unstructured grid) suitable for further postprocessing with ParaView. A further *fid.txt file is generated containing the displaced node numbers and coordinates of the fiducial markers. These latter two files have the same prefixes as `run_file_name`.
See accompanying documentation where available.
NB: Relies on 'abaqus' being available at the command line
(c) M. J. Roy 2021
'''
import os
import subprocess as subproc
import sys
import glob

#block to run abaqus cae with appropriate pass-through, returns successful if inp file is created.
mesh_density = 2 #mm
mesh_file_name = 'U_plastic_mesh_only.inp'
run_file_name = 'U_plastic_run.inp'
plunger_displacement = 100

#run cae script held in build_model.py using subprocess
#arg 1: mesh density
arg_inp="abaqus cae noGUI=build_model_plastic.py -- %f"%(mesh_density)
try:
    run=subproc.check_output(arg_inp, shell=True)
except:
    print('mesh generation failed')
    
#will generate mesh_file_name

#displacement case
appended_details='''
**
**Create material properties
**
*SOLID SECTION, MATERIAL=STEEL, ELSET=all
*MATERIAL, NAME=STEEL
*ELASTIC
200000,0.3
*PLASTIC
400, 0.0E-2
420, 2.0E-2
500,20.0E-2
600,50.0E-2
**
** Contact definition
**
*CONTACT PAIR, INTERACTION=FRIC, TYPE=SURFACE TO SURFACE
TOP, Roller-1_R1_SURF
*CONTACT PAIR, INTERACTION=FRIC, TYPE=SURFACE TO SURFACE
BOTTOM, Roller-2_R2_SURF
*CONTACT PAIR, INTERACTION=FRIC, TYPE=SURFACE TO SURFACE
BOTTOM, Roller-3_R3_SURF
*SURFACE INTERACTION, NAME=FRIC
*FRICTION
0.1,
**
**Initial BCs
**
*BOUNDARY
xy_midplane, 3,3,
yz_midplane, 1,1,
Roller-1-RefPt_, 1,1,
Roller-1-RefPt_, 3,6,
Roller-2-RefPt_, 1,6,
Roller-3-RefPt_, 1,6,
**
** Step 1
**
*STEP, INC=1000, NLGEOM=YES
*STATIC, STABILIZE=0.0002, ALLSDTOL=0.05, CONTINUE=NO
.0001,1.0,1.E-8,1
*BOUNDARY
Roller-1-RefPt_, 2,2, -%f
*output, field, frequency=10, variable=preselect
*el print, elset=all, freq=1
coord, S
*node print, nset=all, freq=1
U
*end step
'''%(plunger_displacement)

with open(mesh_file_name) as mesh:
    with open(run_file_name, "w+") as run:
        run.write(mesh.read())
        run.write(appended_details)
try:
    #submit the job and run it, ask_delete bypasses old job file check
    arg_inp="abaqus job=%s int ask_delete=OFF"%os.path.splitext(run_file_name)[0]
    run=subproc.check_output(arg_inp, shell=True) #use check_output instead
except:
    print('Job submission failed. Exiting.')
    sys.exit()


#run abaqus python script to get stresses at nodes written to an ascii file, and run clean up.
prefix = os.path.splitext(run_file_name)[0]
outputdir = 'examples'

arg_inp="abaqus python odb_access_plastic.py %s %s"%(prefix+'.odb', os.path.join(outputdir,prefix+'.vtu'))
run=subproc.check_output(arg_inp, shell=True) #use check_output instead

print('Finished data extraction. Cleaning up . . .')
#clean up directory
ext = ['.dat', '.odb', '.py', '.vtu', '.STEP', '.inp', '.txt'] #extensions to preserve

dirlist = glob.glob(os.path.join(os.getcwd(),'*.*'))
for file in dirlist:
    if not file.endswith(tuple(ext)):
        os.remove(file)

print('Complete.')