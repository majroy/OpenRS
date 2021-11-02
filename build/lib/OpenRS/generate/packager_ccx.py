'''
Python script for generating a model of an EASI-STRESS elastically loaded U-bend specimen. The script operates sequentially according to:
1) Appends boundary conditions and material properties to an input deck containing mesh information including subsequently referenced geometry, generating an input deck with material properties and boundary conditions, and submits it to the CalculiX solver.
2) The resulting output database from (2) is processed with a standard Python script "frd_access.py", which generates an ASCII-based *.vtu (VTK unstructured grid) suitable for further postprocessing with ParaView. A further *fid.txt file is generated containing the displaced node numbers and coordinates of the fiducial markers. See accompanying documentation.
Relies on full path to CalculiX executable being specified below.
(c) M. J. Roy 2021
'''

import os
import subprocess as subproc
import sys
import glob
from OpenRS.generate.frd_access import postprocess

def run_packager_ccx(mesh_file_name='U_elastic_mesh_only.inp', \
            run_file_name='U_elastic_run_ccx.inp', \
            disp = 1.0, \
            ccx_exe = r'C:\Calculix\CL32-win64bit\bin\ccx\ccx213.exe', \
            outputdir = r'..\examples'):

    #displacement case
    appended_details='''
    *solid section, elset=all, material=S355
    **Properties for S355 are here:
    **https://www.sciencedirect.com/science/article/pii/S0141029616301249
    *material, name=S355
    *elastic, type=iso
    2.05E5,0.3
    *step
    *static
    *boundary
    left, 1,1,%f
    left, 2,2,
    right, 1,1,%f
    right, 2,2,
    midplane_xy, 3,3,
    *node file
    U
    *el file
    S
    *node print, nset=left_lower_datum
    U
    *node print, nset=left_upper_datum
    U
    *node print, nset=right_upper_datum
    U
    *node print, nset=right_lower_datum
    U
    *el print, elset=all
    S
    *endstep
    '''%(disp/2,-disp/2)

    with open(mesh_file_name) as mesh:
        with open(run_file_name, "w+") as run:
            run.write(mesh.read())
            run.write(appended_details)

    print('Wrote CalculiX input, running . . .')
    try:
        #submit the job and run it
        arg_inp="%s -i %s"%(ccx_exe,os.path.splitext(run_file_name)[0])
        run=subproc.check_output(arg_inp, shell=True) #use check_output instead
    except Exception as e:
        print('Job submission failed with following command: %s. Exiting.'%arg_inp)
        print(e)
        sys.exit()

    prefix = os.path.splitext(run_file_name)[0]


    #run post-processing Python function located in frd_access and run clean-up.
    postprocess(prefix+'.frd', os.path.join(outputdir,prefix+'.vtu'), os.path.join(outputdir,prefix+'_fid.txt'))

    print('Finished data extraction. Cleaning up . . .')
    #clean up directory
    ext = ['.dat', '.odb', '.py', '.vtu', '.STEP', '.inp', '.txt', '.frd'] #extensions to preserve

    dirlist = glob.glob(os.path.join(os.getcwd(),'*.*'))
    for file in dirlist:
        if not file.endswith(tuple(ext)):
            os.remove(file)
        if file.endswith('input.inp'): #CalculiX artefact
            os.remove(file)
            
    print('Complete.')
    
if __name__ == "__main__":
    run_packager_ccx()