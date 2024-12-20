#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os
import unreal
from PySide2 import QtWidgets, QtUiTools, QtCore
#from QtUtil import qt_util

file_Path, fileName = os.path.split(__file__)
#file_Path = "F:\\VS-Code_Project\\MetaHumanPicker"
uiName = "MetaHumanPicker.ui"
uiPath = os.path.join(file_Path, uiName)
class MetaHumanPicker(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MetaHumanPicker, self).__init__(parent)
        self.setupUI()
    def setupUI(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath)
        self.ui.CTRL_L_brow_down.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_brow_lateral.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_brow_raiseIn.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_brow_raiseOut.clicked.connect(self.select_Contrl)

        self.ui.CTRL_R_brow_down.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_brow_lateral.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_brow_raiseIn.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_brow_raiseOut.clicked.connect(self.select_Contrl)

        self.ui.CTRL_C_eye.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_blink.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_blink.clicked.connect(self.select_Contrl)

        self.ui.CTRL_C_eye_parallelLook.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_lidPress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_pupil.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_nose_wrinkleUpper.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_lidPress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_pupil.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_nose_wrinkleUpper.clicked.connect(self.select_Contrl)

        self.ui.CTRL_R_ear_up.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_cheekRaise.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_squintInner.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_squintInner.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_cheekRaise.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_ear_up.clicked.connect(self.select_Contrl)

        self.ui.CTRL_L_mouth_upperLipRaise.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_dimple.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lowerLipDepress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_stretch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_sharpCornerPull.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_cornerPull.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_cornerDepress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_cornerPull.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_upperLipRaise.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lowerLipDepress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_sharpCornerPull.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_dimple.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_cornerDepress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_stretch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_mouth.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_suckBlow.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_suckBlow.clicked.connect(self.select_Contrl)

        self.ui.CTRL_R_nose.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_nose.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_stretchLipsClose.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_stretchLipsClose.clicked.connect(self.select_Contrl)

        self.ui.CTRL_C_tongue_move.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_tongue_bendTwist.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_tongue_tipMove.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_tongue_wideNarrow.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_tongue_inOut.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_tongue_press.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_tongue_roll.clicked.connect(self.select_Contrl)

        self.ui.CTRL_C_mouth_stickyU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_stickyInnerU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_stickyOuterU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_stickyOuterU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_stickyInnerU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_stickyOuterD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_stickyOuterD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_stickyInnerD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_mouth_stickyD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_stickyInnerD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipSticky.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipSticky.clicked.connect(self.select_Contrl)

        self.ui.CTRL_R_mouth_towardsU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_funnelU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_funnelU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_purseU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_purseD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_towardsU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_funnelD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_towardsD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_purseD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_purseU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_funnelD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_towardsD.clicked.connect(self.select_Contrl)

        self.ui.CTRL_L_mouth_tightenU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_tightenU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipBiteU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_tightenD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipBiteD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_tightenD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipBiteU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsPressU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipBiteD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsPressU.clicked.connect(self.select_Contrl)

        self.ui.CTRL_L_mouth_lipsBlow.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsBlow.clicked.connect(self.select_Contrl)

        self.ui.CTRL_L_jaw_ChinRaiseU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_jaw_chinCompress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_jaw_ChinRaiseU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_jaw_chinCompress.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_jaw_ChinRaiseD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_jaw_ChinRaiseD.clicked.connect(self.select_Contrl)

        self.ui.CTRL_C_jaw.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_jaw_openExtreme.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_jaw_clench.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_jaw_fwdBack.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_jaw_clench.clicked.connect(self.select_Contrl)

        self.ui.CTRL_R_mouth_lipsTogetherD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_pressD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_pressU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsTogetherU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_pressU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsTogetherU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_pressD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsTogetherD.clicked.connect(self.select_Contrl)

        self.ui.CTRL_rigLogicSwitch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_lookAtSwitch.clicked.connect(self.select_Contrl)

        self.ui.CTRL_neck_throatUpDown.clicked.connect(self.select_Contrl)
        self.ui.CTRL_neck_digastricUpDown.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_neck_stretch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_neck_throatExhaleInhale.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_neck_mastoidContract.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_neck_mastoidContract.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_neck_stretch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_neck_swallow.clicked.connect(self.select_Contrl)

        self.ui.CTRL_C_teethU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_faceScrunch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsRollD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_teeth_fwdBackD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_thicknessU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_teeth_fwdBackU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_eyelidD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_eyelidD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsRollU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_teethD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_thicknessD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_pushPullU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_corner.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_mouth_lipShiftD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_pushPullD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eye_eyelidU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsRollD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_nose_nasolabialDeepen.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_thicknessD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsTowardsTeethU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_cornerSharpnessD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_corner.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_lipsTowardsTeethD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_thicknessU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_C_mouth_lipShiftU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eyelashes_tweakerIn.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsRollU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_eyelidU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_cornerSharpnessU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eyelashes_tweakerIn.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_pushPullD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_eyelashes_tweakerOut.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsTowardsTeethD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_cornerSharpnessU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eyelashes_tweakerOut.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_pushPullU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_mouth_lipsTowardsTeethU.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_nose_nasolabialDeepen.clicked.connect(self.select_Contrl)
        self.ui.CTRL_eyesAimFollowHead.clicked.connect(self.select_Contrl)
        self.ui.CTRL_R_mouth_cornerSharpnessD.clicked.connect(self.select_Contrl)
        self.ui.CTRL_L_eye_faceScrunch.clicked.connect(self.select_Contrl)
        self.ui.CTRL_faceGUIfollowHead.clicked.connect(self.select_Contrl)

        self.ui.clear_pushButton.clicked.connect(self.clear_select)
        self.ui.load_sequencer_pushButton.clicked.connect(self.get_sequencer)
        self.ui.sequence_path_lineEdit.textChanged.connect(self.editItems)
        self.ui.tabWidget.currentChanged.connect(self.resetMinmumValue)
    def editItems(self):
        """将获取到关卡序列中的所有Actors，添加到comboBox中"""
        #self.ui.sequence_path_lineEdit.textChanged()
        hosting_actors_fullName,control_rigs_dic = self.get_control_rigs()
        self.ui.comboBox_Actors.clear()
        self.ui.comboBox_Actors.addItems(hosting_actors_fullName)

    def get_control_rigs(self):
        control_rigs_dic = {}
        hosting_actors_fullName = []
        sequence_asset = unreal.load_asset(self.ui.sequence_path_lineEdit.text())
        if sequence_asset:
            #获取序列中的所有 Control Rigs
            control_rigs = unreal.ControlRigSequencerLibrary.get_control_rigs(sequence_asset)
            for control in control_rigs:
                hosting_actor = control.control_rig.get_hosting_actor()
                actorName = hosting_actor.get_name()
                control_name = control.control_rig.get_name()
                returnName = f"{control_name}({actorName})"
                hosting_actors_fullName.append(returnName)
                control_rigs_dic[returnName] = control
            return hosting_actors_fullName,control_rigs_dic
    
    def select_Contrl(self):
        sender = self.sender()
        button_name = sender.objectName()
        hosting_actors_fullName,control_rigs_dic = self.get_control_rigs()
        actor_name = self.ui.comboBox_Actors.currentText()
        control_name = control_rigs_dic[actor_name]
        is_single = self.ui.single_radioButton.isChecked()
        if is_single:
            self.clear_control_selection(control_rigs_dic.values())
            control_name.control_rig.select_control(button_name,select = True)
        else:
            control_rigs = [i for i in control_rigs_dic.values() if i != control_name]
            self.clear_control_selection(control_rigs)
            control_name.control_rig.select_control(button_name,select = True)
    def clear_select(self):
        hosting_actors_fullName,control_rigs_dic = self.get_control_rigs()
        self.clear_control_selection(control_rigs_dic.values())

    def clear_control_selection(self,controlRigs):
        for _i in controlRigs:
            _i.control_rig.clear_control_selection()


    def get_sequencer(self):
        assetsList = unreal.EditorUtilityLibrary.get_selected_assets()
        if assetsList:
            sequence_path = assetsList[0].get_path_name()
        else:
            sequence_path = '/Game/MetaHumans/Tahir_Modify/MySequence.MySequence'
        self.ui.sequence_path_lineEdit.setText(sequence_path)
        #return sequence_path

    def resetMinmumValue(self):
        """
        Click Select tabWidget and resize the window
        """
        tabObjectName = self.ui.tabWidget.currentWidget()
        tabName = tabObjectName.objectName()
        if tabName == "tweakers_tab":
            self.ui.setMinimumWidth(744)
            self.ui.setMinimumHeight(655)
            self.ui.resize(QtCore.QSize(744, 655))
        elif tabName == "faceCtrl_tab":
            self.ui.setMinimumWidth(890)
            self.ui.setMinimumHeight(950)
            self.ui.resize(QtCore.QSize(890, 950))
        elif tabName == "body_tab":
            self.ui.setMinimumWidth(600)
            self.ui.setMinimumHeight(300)
            self.ui.resize(QtCore.QSize(600, 300))




if __name__ == "__main__":
    #app = qt_util.create_qt_application(use_stylesheet=False)
    mainwindow = MetaHumanPicker()
    mainwindow.ui.show()
    unreal.parent_external_window_to_slate(mainwindow.ui.winId())
