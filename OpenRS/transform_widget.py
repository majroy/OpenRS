#!/usr/bin/env python
'''
Constructor functions/methods for transformation widgets for OpenRS.
'''

import sys
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import importlib.resources

def make_translate_button_layout(parent_window):
    '''
    Makes a button group containing a translation, rotation and reset button
    '''
    button_layout = QtWidgets.QHBoxLayout()
    parent_window.trans_reset_button = QtWidgets.QPushButton('Reset')
    parent_window.trans_reset_button.setToolTip('Reset all current transformations')
    parent_window.trans_reset_button.setEnabled(False)
    parent_window.translate_drop_button = make_translate_button(parent_window)
    button_layout.addWidget(parent_window.translate_drop_button)
    button_layout.addWidget(parent_window.trans_reset_button)
    button_layout.addStretch(1)
    return button_layout

def make_transformation_button_layout(parent_window):
    '''
    Makes a button group that contains a translation and reset button
    '''
    button_layout = QtWidgets.QHBoxLayout()
    parent_window.trans_reset_button = QtWidgets.QPushButton('Reset')
    parent_window.trans_reset_button.setToolTip('Reset all current transformations')
    parent_window.trans_reset_button.setEnabled(False)
    parent_window.translate_drop_button = make_translate_button(parent_window)
    button_layout.addWidget(parent_window.translate_drop_button)
    parent_window.rotate_drop_button = make_rotate_button(parent_window)
    button_layout.addWidget(parent_window.rotate_drop_button)
    button_layout.addWidget(parent_window.trans_reset_button)
    button_layout.addStretch(1)
    return button_layout


def make_translate_button(parent_window):
    
    ico = importlib.resources.files('OpenRS') / 'meta/translate_icon.png'
    with importlib.resources.as_file(ico) as path:
        rotate_icon = QtGui.QIcon(QtGui.QIcon(path.__str__()))
    
    translate_drop_button = QtWidgets.QToolButton()
    translate_drop_button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
    translate_drop_button.setCheckable(True)
    translate_drop_button.setMenu(QtWidgets.QMenu(translate_drop_button))
    trans_action = QtWidgets.QWidgetAction(translate_drop_button)
    parent_window.trans_widget = transform_box(parent_window,'translate')
    trans_action.setDefaultWidget(parent_window.trans_widget)
    translate_drop_button.menu().addAction(trans_action)
    translate_drop_button.setIcon(rotate_icon)
    translate_drop_button.setToolTip('Translate to new origin')
    return translate_drop_button

def make_rotate_button(parent_window):
    
    ico = importlib.resources.files('OpenRS') / 'meta/rotate_icon.png'
    with importlib.resources.as_file(ico) as path:
        rotate_icon = QtGui.QIcon(QtGui.QIcon(path.__str__()))

    rotate_drop_button = QtWidgets.QToolButton()
    rotate_drop_button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
    rotate_drop_button.setCheckable(True)
    rotate_drop_button.setMenu(QtWidgets.QMenu(rotate_drop_button))
    trans_action = QtWidgets.QWidgetAction(rotate_drop_button)
    parent_window.rotation_widget = transform_box(parent_window,'transform')
    trans_action.setDefaultWidget(parent_window.rotation_widget)
    rotate_drop_button.menu().addAction(trans_action)
    rotate_drop_button.setIcon(rotate_icon)
    rotate_drop_button.setToolTip('Rotate about origin')
    return rotate_drop_button

def get_trans_from_euler_angles(ax,ay,az):
    '''
    Based on incoming arguments in *degrees*, return a 4x4 transformation matrix
    '''
    ax = np.deg2rad(ax)
    Rx = np.array([[1,0,0],[0, np.cos(ax), -np.sin(ax)],[0, np.sin(ax), np.cos(ax)]])
    ay = np.deg2rad(ay)
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)],[0,1,0],[-np.sin(ay), 0, np.cos(ay)]])
    az = np.deg2rad(az)
    Rz = np.array([[np.cos(az), -np.sin(az), 0],[np.sin(az), np.cos(az), 0],[0,0,1]])
    R = Rx @ Ry @ Rz
    
    trans = np.identity(4)
    trans[0:3,0:3] = R
    return trans

class transform_box(QtWidgets.QWidget):
    def __init__(self, parent_window, cond, *args, **kwargs):
        '''
        Depending on 'cond', either just translate or both translate and rotate options provided.
        cond = 'translate': translate only
             = 'transform': translate and rotate
        '''
        
        super().__init__(*args, **kwargs)
        
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        
        vl = QtWidgets.QVBoxLayout()
        hl = QtWidgets.QHBoxLayout()
        button_layout = QtWidgets.QHBoxLayout()
        translate_box = QtWidgets.QGroupBox('Translate:')
        translate_layout = QtWidgets.QVBoxLayout()
        rotate_box = QtWidgets.QGroupBox('Rotate about:')
        rotate_layout = QtWidgets.QVBoxLayout()
        
        self.setLayout(button_layout)
        
        #right hand button group
        self.choose_vertex_button = QtWidgets.QPushButton('Vertex')
        self.choose_vertex_button.setEnabled(False)
        self.choose_vertex_button.setCheckable(True)
        self.choose_vertex_button.setToolTip("Select vertex from viewport")

        self.trans_origin_button = QtWidgets.QPushButton('Update')
        self.trans_origin_button.setToolTip('Apply transformation')
        self.trans_origin_button.setEnabled(False)
        
        self.translate_x = QtWidgets.QDoubleSpinBox()
        self.translate_x.setMinimum(-1000)
        self.translate_x.setValue(0)
        self.translate_x.setMaximum(1000)
        self.translate_x.setPrefix('X ')
        self.translate_x.setSuffix(' mm')
        
        translate_y_label =QtWidgets.QLabel("Y")
        self.translate_y = QtWidgets.QDoubleSpinBox()
        self.translate_y.setMinimum(-1000)
        self.translate_y.setValue(0)
        self.translate_y.setMaximum(1000)
        self.translate_y.setPrefix('Y ')
        self.translate_y.setSuffix(' mm')
        
        translate_z_label =QtWidgets.QLabel("Z")
        self.translate_z = QtWidgets.QDoubleSpinBox()
        self.translate_z.setMinimum(-1000)
        self.translate_z.setValue(0)
        self.translate_z.setMaximum(1000)
        self.translate_z.setPrefix('Z ')
        self.translate_z.setSuffix(' mm')

        #make button group for STL origin rotation
        self.rotate_x = QtWidgets.QDoubleSpinBox()
        self.rotate_x.setSingleStep(15)
        self.rotate_x.setMinimum(-345)
        self.rotate_x.setValue(0)
        self.rotate_x.setMaximum(345)
        self.rotate_x.setPrefix('X ')
        self.rotate_x.setSuffix(' °')
        
        self.rotate_y = QtWidgets.QDoubleSpinBox()
        self.rotate_y.setSingleStep(15)
        self.rotate_y.setMinimum(-345)
        self.rotate_y.setValue(0)
        self.rotate_y.setMaximum(345)
        self.rotate_y.setPrefix('Y ')
        self.rotate_y.setSuffix(' °')
        
        zlabel = QtWidgets.QLabel("Z (deg)")
        self.rotate_z = QtWidgets.QDoubleSpinBox()
        self.rotate_z.setSingleStep(15)
        self.rotate_z.setMinimum(-345)
        self.rotate_z.setValue(0)
        self.rotate_z.setMaximum(345)
        self.rotate_z.setPrefix('Z ')
        self.rotate_z.setSuffix(' °')

        #transform origin button layout
        translate_layout.addWidget(self.translate_x)
        translate_layout.addWidget(self.translate_y)
        translate_layout.addWidget(self.translate_z)
        
        rotate_layout.addWidget(self.rotate_x)
        rotate_layout.addWidget(self.rotate_y)
        rotate_layout.addWidget(self.rotate_z)
        
        translate_box.setLayout(translate_layout)
        rotate_box.setLayout(rotate_layout)
        if cond == 'translate':
            vl.addWidget(self.choose_vertex_button)
            hl.addWidget(translate_box)
        vl.addWidget(self.trans_origin_button)
        if cond == 'transform':
            hl.addWidget(rotate_box)
        
        button_layout.addLayout(vl)
        button_layout.addLayout(hl)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    layout1 = make_translate_button_layout(window)
    layout2 = make_transformation_button_layout(window)
    main_layout = QtWidgets.QVBoxLayout()
    main_layout.addLayout(layout1)
    main_layout.addLayout(layout2)
    window.setLayout(main_layout)
    window.show()
    sys.exit(app.exec_())