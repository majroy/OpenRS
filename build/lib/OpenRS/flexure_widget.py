import numpy as np
import os
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pkg_resources import Requirement, resource_filename
import yaml
from OpenRS.return_disp import get_disp_from_fid
from OpenRS.open_rs_common import table_model, get_file

class external(QThread):
    '''
    Sets up and runs external thread for FEA, emits 100 when done.
    '''
    _signal = pyqtSignal(int)
    def __init__(self,disp,ccx_exe,outputdir):
        super(external, self).__init__()
        self.disp = disp
        self.ccx_exe = ccx_exe
        self.outputdir = outputdir

    def run(self):
        from OpenRS.generate.packager_ccx import run_packager_ccx
        current_dir = os.getcwd()
        os.chdir(self.outputdir)
        mf = resource_filename("OpenRS","generate/U_elastic_mesh_only.inp")
        rf = 'U_elastic_run_ccx.inp'
        run_packager_ccx(mesh_file_name = mf, \
            run_file_name = rf, \
            disp = self.disp, \
            ccx_exe = self.ccx_exe, \
            outputdir = self.outputdir)
        self._signal.emit(100)
        os.chdir(current_dir)


class modeling_widget(QtWidgets.QDialog):

    def __init__(self, parent):
        super(modeling_widget, self).__init__(parent)
        
        self.setWindowTitle("OpenRS - FEA flexure calculation" )
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumSize(QtCore.QSize(450, 400))

        spl_fname=resource_filename("OpenRS","meta/flexure_pnts.png")
        fid_layout_image = QtGui.QPixmap(spl_fname,'PNG')
        self.fid_layout_image = fid_layout_image.scaledToHeight(250)
        self.image_label = QtWidgets.QLabel()
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(self.fid_layout_image)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        
        fid_data_group = QtWidgets.QGroupBox('Boundary condition input:')
        #populate with points from undeformed orientations
        self.fid_data = np.array([[-40,25,0],[-40,45,0],[40,45,0],[40,25,0]]).tolist()
        self.disp = 0.0
        
        self.pbar = QtWidgets.QProgressBar(self, textVisible=True)
        self.pbar.setAlignment(Qt.AlignCenter)
        self.pbar.setFormat("Idle")
        self.pbar.setFont(QtGui.QFont("Helvetica",italic=True))
        self.pbar.setValue(0)

        self.fid_model = table_model(self.fid_data,['X','Y','Z'])
        self.fid_table = QtWidgets.QTableView()
        self.fid_table.setModel(self.fid_model)
        self.fid_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.fid_table.resizeColumnsToContents()
        self.fid_table.resizeRowsToContents()
        
        dti_entry_label = QtWidgets.QLabel('DTI reading')
        self.dti_entry = QtWidgets.QDoubleSpinBox()
        self.dti_entry.setMinimum(-0.58865412)
        self.dti_entry.setMaximum(0.58865412)
        self.dti_entry.setDecimals(3)
        calc_button_group = QtWidgets.QButtonGroup(self)
        self.calc_fid_rbutton = QtWidgets.QRadioButton("Calculate using fiducial")
        self.calc_fid_rbutton.setChecked(True)
        self.calc_dti_rbutton = QtWidgets.QRadioButton("Calculate using DTI")
        calc_button_group.addButton(self.calc_fid_rbutton)
        calc_button_group.addButton(self.calc_dti_rbutton)
        calc_button_group.setExclusive(True)
        self.run_calc_button = QtWidgets.QPushButton('Calculate')
        calc_layout = QtWidgets.QGridLayout()
        calc_layout.addWidget(dti_entry_label,0,0,1,1)
        calc_layout.addWidget(self.dti_entry,0,1,1,1)
        calc_layout.addWidget(self.calc_fid_rbutton,1,0,1,2)
        calc_layout.addWidget(self.calc_dti_rbutton,2,0,1,2)
        calc_layout.addWidget(self.run_calc_button,3,0,1,2)
        
        
        headFont=QtGui.QFont("Helvetica [Cronyx]", 14, weight=QtGui.QFont.Bold )
        d1_label = QtWidgets.QLabel('Displacement:')
        self.d1 = QtWidgets.QLabel(str(self.disp))
        self.d1.setFont(headFont)
        d_layout = QtWidgets.QHBoxLayout()
        d_layout.addWidget(d1_label)
        d_layout.addWidget(self.d1)
        
        fid_table_layout = QtWidgets.QVBoxLayout()
        fid_table_layout.addWidget(self.fid_table)
        fid_table_layout.addLayout(calc_layout)
        fid_table_layout.addLayout(d_layout)
        fid_data_group.setLayout(fid_table_layout)
        
        
        
        fid_layout = QtWidgets.QHBoxLayout()
        fid_layout.addWidget(self.image_label)
        fid_layout.addStretch()
        fid_layout.addWidget(fid_data_group)
        

        self.run_button = QtWidgets.QPushButton('Run')
        ccx_exec_path_label = QtWidgets.QLabel('Path to CalculiX executable:')
        self.ccx_exec_path = QtWidgets.QLineEdit()
        ccx_choose_path = QtWidgets.QPushButton('...')
        ccx_choose_path.setMaximumWidth(20)
        fea_path_label = QtWidgets.QLabel('Working directory:')
        self.fea_path = QtWidgets.QLineEdit()
        wd_choose_path = QtWidgets.QPushButton('...')
        wd_choose_path.setMaximumWidth(20)

        fea_layout = QtWidgets.QGridLayout()
        fea_layout.addWidget(self.run_button,2,0,1,1)
        fea_layout.addWidget(ccx_exec_path_label,0,0,1,1)
        fea_layout.addWidget(self.ccx_exec_path,0,1,1,2)
        fea_layout.addWidget(ccx_choose_path,0,3,1,1)
        fea_layout.addWidget(fea_path_label,1,0,1,1)
        fea_layout.addWidget(self.fea_path,1,1,1,2)
        fea_layout.addWidget(wd_choose_path,1,3,1,1)
        fea_layout.addWidget(self.pbar,2,1,1,3)

        
        self.run_calc_button.clicked.connect(self.get_disp)

        self.run_button.clicked.connect(self.run_calc)
        
        ccx_choose_path.clicked.connect(self.set_ccx)
        wd_choose_path.clicked.connect(self.set_wd)
        

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(fid_layout)
        vertical_spacer = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout.addItem(vertical_spacer)
        self.layout.addLayout(fea_layout)

        self.setLayout(self.layout)
        self.read_config()
        self.show()

    def get_disp(self):
        '''
        Reads GUI, depending on what radio button calculated displacement boundary condition
        '''
        if self.calc_fid_rbutton.isChecked():
            model = self.fid_model
            fid_pts = np.zeros((4,3))
            nrows = model.rowCount(0)
            ncols = model.columnCount(0)
            for i in range(nrows):
                for j in range(ncols):
                    fid_pts[i,j]=model.getCellData([i,j])
            self.disp = get_disp_from_fid(fid_pts,False)
            self.dti_entry.setValue(self.disp*-0.58865412)
        elif self.calc_dti_rbutton.isChecked():
            self.disp = self.dti_entry.value()/-0.58865412
        
        self.d1.setText('%6.3f'%self.disp)
        
    def set_ccx(self):
        f,_ = get_file("*.*")
        self.ccx_exec_path.setText(f)
        self.make_config_change()
    
    def set_wd(self):
        dir = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.fea_path.setText(dir)
        self.make_config_change()
        
    def run_calc(self):
        self.thread = external(self.disp,self.ccx_exec_path.text(),self.fea_path.text())
        self.thread._signal.connect(self.signal_accept)
        self.thread.start()
        self.pbar.setTextVisible(True)
        self.pbar.setStyleSheet("")
        self.pbar.setRange(0,0)
        
    def signal_accept(self, msg):
        if int(msg) == 100:
            self.pbar.setRange(0,100)
            self.pbar.setValue(0)
            self.pbar.setFormat("Complete")
            self.pbar.setStyleSheet("QProgressBar"
              "{"
              "background-color: lightgreen;"
              "border : 1px"
              "}")
        

    def read_config(self):
        fname=resource_filename("OpenRS","meta/OpenRSconfig.yml")
        with open(fname, 'r') as f:
            read = yaml.load(f, Loader=yaml.FullLoader)
        
        self.ccx_exec_path.setText(read['FEA']['ccx_exec'])
        self.fea_path.setText(read['FEA']['work_dir'])

    def make_config_change(self):
        data = dict(
        FEA = dict(
        ccx_exec = str(self.ccx_exec_path.text()),
        work_dir = str(self.fea_path.text())
        )
        )
        fname=resource_filename("OpenRS","meta/OpenRSconfig.yml")
        with open(fname,'w+') as f:
            yaml.dump(data,f, default_flow_style=False)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = modeling_widget(None)
    sys.exit(app.exec_())