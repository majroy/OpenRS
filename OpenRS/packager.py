import os
import subprocess as subproc
import sys

#block to run abaqus cae with appropriate pass-throughs, returns successful if inp file is created.
step_file_name = 'U_elastic_v4.STEP'
mesh_density = 2 #mm
mesh_file_name = 'U_elastic_mesh_only.inp'
run_file_name = 'U_elastic_run.inp'
disp = 1.2

#run cae script held in build_model.py using subprocess
arg_inp="abaqus cae noGUI=build_model.py -- %s %f"%(step_file_name,mesh_density)
try:
    run=subproc.check_output(arg_inp, shell=True)
except:
    print('mesh generation failed')
    
#will generate mesh_file_name

#displacement case
appended_details='''
*solid section, elset=all, material=S355
**Properties for S355 are here:
**https://www.sciencedirect.com/science/article/pii/S0141029616301249
*material, name=S355
*elastic, type=iso
2.05E5,0.3
*step, perturbation, name=DirectLoading, nlgeom
*static
*boundary
left, 1,1,%f
left, 2,2,
right, 1,1,%f
right, 2,2,
midplane_xy, 3,3,
midplane_zy, 1,1,
*output, field, frequency=1, variable=preselect
*el print, elset=all, freq=1
coord, S
*node print, nset=all, freq=1
U
*end step
'''%(disp/2,-disp/2)

#clean up directory to ensure subproc does not hang waiting for 'y'
ext = ['.dat', '.msg', '.odb', '.prt', '.sim', '.sta', '.com']

for e in ext:
    target = os.path.splitext(run_file_name)[0].join(e)
    if os.path.isfile(target):
        os.remove(target)

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
arg_inp="abaqus python odb_datum_access.py %s %s"%(os.path.splitext(run_file_name)[0]+'.odb', 'Results\\U_elastic_odb.txt')
run=subproc.check_output(arg_inp, shell=True) #use check_output instead