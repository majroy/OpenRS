'''
Python script for generating a model of an EASI-STRESS elastically loaded U-bend specimen. The script operates sequentially according to:
1) Runs an Abaqus Python preprocessing script "build_model.py" with Abaqus CAE to generate an abaqus input deck without material assignment or boundary conditions (a mesh). build_model.py requires the arguments of a provided *.STEP file, and global mesh size/density.
2) Appends boundary conditions and material properties to the input deck generated in (1), generates an input deck with material properties and boundary conditions, and submits it to the Abaqus solver.
3) The resulting output database from (2) is processed with an Abaqus Python script "odb_access.py", which generates an ASCII-based *.vtu (VTK unstructured grid) suitable for further postprocessing with ParaView. A further *fid.txt file is generated containing the displaced node numbers and coordinates of the fiducial markers. These latter two files have the same prefixes as `run_file_name`.
See accompanying documentation where available.
NB: Relies on 'abaqus' being available at the command line, and the provided *.STEP file(s) being available.
(c) M. J. Roy 2021
'''
import os
import subprocess as subproc
import sys
import glob

# #block to run abaqus cae with appropriate pass-through, returns successful if inp file is created.
# step_file_name = r'geometry\U_elastic_imp_fid.STEP'
# mesh_density = 8 #mm
# mesh_file_name = 'U_elastic_mesh_only.inp'
run_file_name = 'U_elastic_run.inp'
# disp = 1.2

# #run cae script held in build_model.py using subprocess
# arg_inp="abaqus cae noGUI=build_model.py -- %s %f"%(step_file_name,mesh_density)
# try:
    # run=subproc.check_output(arg_inp, shell=True)
# except:
    # print('mesh generation failed')
    
# #will generate mesh_file_name

# #displacement case
# appended_details='''
# *solid section, elset=all, material=S355
# **Properties for S355 are here:
# **https://www.sciencedirect.com/science/article/pii/S0141029616301249
# *material, name=S355
# *elastic, type=iso
# 2.05E5,0.3
# *step, perturbation, name=DirectLoading
# *static
# *boundary
# left, 1,1,%f
# left, 2,2,
# right, 1,1,%f
# right, 2,2,
# midplane_xy, 3,3,
# *output, field, frequency=1, variable=preselect
# *el print, elset=all, freq=1
# coord, S
# *node print, nset=all, freq=1
# U
# *end step
# '''%(disp/2,-disp/2)

# with open(mesh_file_name) as mesh:
    # with open(run_file_name, "w+") as run:
        # run.write(mesh.read())
        # run.write(appended_details)
# try:
    # #submit the job and run it, ask_delete bypasses old job file check
    # arg_inp="abaqus job=%s int ask_delete=OFF"%os.path.splitext(run_file_name)[0]
    # run=subproc.check_output(arg_inp, shell=True) #use check_output instead
# except:
    # print('Job submission failed. Exiting.')
    # sys.exit()

#run abaqus python script to get stresses at nodes written to an ascii file, and run clean up.
prefix = os.path.splitext(run_file_name)[0]
outputdir = 'examples'

arg_inp="abaqus python odb_access.py %s %s %s"%(prefix+'.odb', os.path.join(outputdir,prefix+'.vtu'), os.path.join(outputdir,prefix+'_fid.txt'))
run=subproc.check_output(arg_inp, shell=True) #use check_output instead

print('Finished data extraction. Cleaning up . . .')
#clean up directory
ext = ['.dat', '.odb', '.py', '.vtu', '.STEP', '.inp', '.txt'] #extensions to preserve

dirlist = glob.glob(os.path.join(os.getcwd(),'*.*'))
for file in dirlist:
    if not file.endswith(tuple(ext)):
        os.remove(file)

print('Complete.')