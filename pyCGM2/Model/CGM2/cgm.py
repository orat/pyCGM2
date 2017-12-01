# -*- coding: utf-8 -*-
import numpy as np
import logging
import copy
#from numba import jit, autojit

import btk

from pyCGM2 import enums
from pyCGM2.Model import model, modelDecorator,frame,motion
from pyCGM2.Math import euler,geometry
from pyCGM2.Tools import  btkTools
from pyCGM2.Nexus import nexusTools


class CGM(model.Model):
    """
        Abstract Class of the Conventional Gait Model
    """




    PIG_STATIC_ANGLE_LABELS= ["LPelvisAngles","RPelvisAngles",
                              "LHipAngles","RHipAngles",
                              "LKneeAngles","RKneeAngles",
                              "LAnkleAngles","RAnkleAngles",
                              "LAbsAnkleAngle","RAbsAnkleAngle",
                              "LFootProgressAngles","RFootProgressAngles"]

    PIG_STATIC_FORCE_LABELS= ["LAnkleForce","RAnkleForce",
                              "LGroundReactionForce","RGroundReactionForce",
                              "LHipForce","RHipForce",
                              "LKneeForce","RKneeForce",
                              "LNormalisedGRF","RNormalisedGRF"]


    PIG_STATIC_MOMENT_LABELS= ["LAnkleMoment","RAnkleMoment",
                              "LGroundReactionMoment","RGroundReactionMoment",
                              "LHipMoment","RHipMoment",
                              "LKneeMoment","RKneeMoment"]

    PIG_STATIC_POWER_LABELS= ["LAnklePower","RAnklePower",
                              "LHipPower","RHipPower",
                              "LKneePower","RKneePower",]

    def __init__(self):
        super(CGM, self).__init__()
        self.m_useLeftTibialTorsion=False
        self.m_useRightTibialTorsion=False

    @classmethod
    def reLabelOldOutputs(cls,acq):
        for it in btk.Iterate(acq.GetPoints()):
            if it.GetType() == btk.btkPoint.Angle and  it.GetLabel() in CGM.PIG_STATIC_ANGLE_LABELS:
                logging.warning( "angle (%s) suffixed (.OLD)" %(it.GetLabel()))
                it.SetLabel(it.GetLabel()+".OLD")

            if it.GetType() == btk.btkPoint.Force and  it.GetLabel() in CGM.PIG_STATIC_FORCE_LABELS:
                logging.warning( "force (%s) suffixed (.OLD)" %(it.GetLabel()))
                it.SetLabel(it.GetLabel()+".OLD")

            if it.GetType() == btk.btkPoint.Moment and  it.GetLabel() in CGM.PIG_STATIC_MOMENT_LABELS:
                logging.warning( "moment (%s) suffixed (.OLD)" %(it.GetLabel()))
                it.SetLabel(it.GetLabel()+".OLD")


            if it.GetType() == btk.btkPoint.Power and  it.GetLabel() in CGM.PIG_STATIC_POWER_LABELS:
                logging.warning( "power (%s) suffixed (.OLD)" %(it.GetLabel()))
                it.SetLabel(it.GetLabel()+".OLD")


    @classmethod
    def checkCGM1_StaticMarkerConfig(cls,acqStatic):

        out = dict()

        #--Left--
        leftKad = True if btkTools.isPointsExist(acqStatic,["LKAX","LKD1","LKD2"]) else False
        leftAnkleMed = True if btkTools.isPointsExist(acqStatic,["LMED","LANK"]) else False
        leftKneeMed = True if btkTools.isPointsExist(acqStatic,["LKNM","LKNE"]) else False

        if not leftKad and not leftAnkleMed and not leftKneeMed:
            out["left"] = enums.CgmStaticMarkerConfig.Native

        if leftKad and not leftAnkleMed:
            out["left"] = enums.CgmStaticMarkerConfig.KAD

        if leftKad and leftAnkleMed:
            out["left"] = enums.CgmStaticMarkerConfig.KADmed

        if leftKneeMed and not leftAnkleMed:
            out["left"] = enums.CgmStaticMarkerConfig.KneeMed

        if leftKneeMed and leftAnkleMed:
            out["left"] = enums.CgmStaticMarkerConfig.KneeAnkleMed

        #--right--
        rightKad = True if btkTools.isPointsExist(acqStatic,["RKAX","RKD1","RKD2"]) else False
        rightAnkleMed = True if btkTools.isPointsExist(acqStatic,["RMED","RANK"]) else False
        rightKneeMed = True if btkTools.isPointsExist(acqStatic,["RKNM","RKNE"]) else False

        if not rightKad and not rightAnkleMed and not rightKneeMed:
            out["right"] = enums.CgmStaticMarkerConfig.Native

        if rightKad and not rightAnkleMed:
            out["right"] = enums.CgmStaticMarkerConfig.KAD

        if rightKad and rightAnkleMed:
            out["right"] = enums.CgmStaticMarkerConfig.KADmed

        if rightKneeMed and not rightAnkleMed:
            out["right"] = enums.CgmStaticMarkerConfig.KneeMed

        if rightKneeMed and rightAnkleMed:
            out["right"] = enums.CgmStaticMarkerConfig.KneeAnkleMed

        return out

class CGM1LowerLimbs(CGM):
    """
    Lower limb conventional Gait Model 1 (i.e. Vicon Plugin Gait)

    """

    #nativeCgm1 = True

    MARKERS = ["LASI", "RASI","RPSI", "LPSI","LTHI","LKNE","LTIB","LANK","LHEE","LTOE","RTHI","RKNE","RTIB","RANK","RHEE","RTOE"]

    ANALYSIS_KINEMATIC_LABELS_DICT ={ 'Left': ["LHipAngles","LKneeAngles","LAnkleAngles","LFootProgressAngles","LPelvisAngles"],
                           'Right': ["RHipAngles","RKneeAngles","RAnkleAngles","RFootProgressAngles","RPelvisAngles"]}

    ANALYSIS_KINETIC_LABELS_DICT ={ 'Left': ["LHipMoment","LKneeMoment","LAnkleMoment","LHipPower","LKneePower","LAnklePower"],
                              'Right': ["RHipMoment","RKneeMoment","RAnkleMoment","RHipPower","RKneePower","RAnklePower"]}


    def __init__(self):
        super(CGM1LowerLimbs, self).__init__()
        self.decoratedModel = False
        self.version = "CGM1.0"

        # init of few mp_computed
        self.mp_computed["LeftKneeFuncCalibrationOffset"] = 0
        self.mp_computed["RightKneeFuncCalibrationOffset"] = 0


    def setVersion(self,string):
        self.version = string

    def __repr__(self):
        return "LowerLimb CGM1.0"

    @classmethod
    def cleanAcquisition(cls, acq, subjetPrefix="",removelateralKnee=False, kadEnable= False, ankleMedEnable = False):
        """
            Convenient class for cleaning an acquisition and keeping CGM1 markers only.

            :Parameters:
                - `acq` (btkAcquisition) - btkAcquisition instance from a  c3d
                - `subjetPrefix` (str) - prefix identifying a subjet ( ex : hannibal:)
                - `removelateralKnee` (bool) - remove lateral knee marker (True if you deal with a static KAD acquisition)
                - `kadEnable` (bool) - keep KAD markers
                - `ankleMedEnable` (bool) -keep medial ankle markers

            .. note:: With Vicon Nexus, subject name prefixed marker label if you selected different subjets ( mean vsk) within your session

        """

        markers = [subjetPrefix+"LASI",
                   subjetPrefix+"RASI",
                   subjetPrefix+"LPSI",
                   subjetPrefix+"RPSI",
                   subjetPrefix+"LTHI",
                   subjetPrefix+"LKNE",
                   subjetPrefix+"LTIB",
                   subjetPrefix+"LANK",
                   subjetPrefix+"LHEE",
                   subjetPrefix+"LTOE",
                   subjetPrefix+"RTHI",
                   subjetPrefix+"RKNE",
                   subjetPrefix+"RTIB",
                   subjetPrefix+"RANK",
                   subjetPrefix+"RHEE",
                   subjetPrefix+"RTOE",
                   subjetPrefix+"SACR"]

        if removelateralKnee:
            markers.append(subjetPrefix+"LKNE")
            markers.append(subjetPrefix+"RKNE")


        if kadEnable:
            markers.append(subjetPrefix+"LKAX")
            markers.append(subjetPrefix+"LKD1")
            markers.append(subjetPrefix+"LKD2")
            markers.append(subjetPrefix+"RKAX")
            markers.append(subjetPrefix+"RKD1")
            markers.append(subjetPrefix+"RKD2")

        if ankleMedEnable:
            markers.append(subjetPrefix+"LMED")
            markers.append(subjetPrefix+"RMED")


        btkTools.clearPoints(acq,markers)
        return acq


    def configure(self):
        """
            Model configuration. Define Segment, joint, ...
        """
        self.addSegment("Pelvis",0,enums.SegmentSide.Central,calibration_markers=[], tracking_markers = ["LASI","RASI","LPSI","RPSI"])
        self.addSegment("Left Thigh",1,enums.SegmentSide.Left,calibration_markers=[], tracking_markers = ["LKNE","LTHI"])
        self.addSegment("Right Thigh",4,enums.SegmentSide.Right,calibration_markers=[], tracking_markers = ["RKNE","RTHI"])
        self.addSegment("Left Shank",2,enums.SegmentSide.Left,calibration_markers=[], tracking_markers = ["LANK","LTIB"])
        self.addSegment("Left Shank Proximal",7,enums.SegmentSide.Left) # copy of Left Shank with anatomical frame modified by a tibial Rotation Value ( see calibration)
        self.addSegment("Right Shank",5,enums.SegmentSide.Right,calibration_markers=[], tracking_markers = ["RANK","RTIB"])
        self.addSegment("Right Shank Proximal",8,enums.SegmentSide.Right)        # copy of Left Shank with anatomical frame modified by a tibial Rotation Value ( see calibration)
        self.addSegment("Left Foot",3,enums.SegmentSide.Left,calibration_markers=[""], tracking_markers = ["LHEE","LTOE"] )
        self.addSegment("Right Foot",6,enums.SegmentSide.Right,calibration_markers=[""], tracking_markers = ["RHEE","RTOE"])

        self.addChain("Left Lower Limb", [3,2,1,0]) # Dist ->Prox Todo Improve
        self.addChain("Right Lower Limb", [6,5,4,0])

        self.addJoint("LHip","Pelvis", "Left Thigh","YXZ","LHJC")
        if self.version == "CGM1.0":
            self.addJoint("LKnee","Left Thigh", "Left Shank Proximal","YXZ","LKJC")
        else:
            self.addJoint("LKnee","Left Thigh", "Left Shank","YXZ","LKJC")


        #self.addJoint("LKneeAngles_cgm","Left Thigh", "Left Shank","YXZ")
        self.addJoint("LAnkle","Left Shank", "Left Foot","YXZ","LAJC")

        self.addJoint("RHip","Pelvis", "Right Thigh","YXZ","RHJC")
        if self.version == "CGM1.0":
            self.addJoint("RKnee","Right Thigh", "Right Shank Proximal","YXZ","RKJC")
        else:
            self.addJoint("RKnee","Right Thigh", "Right Shank","YXZ","RKJC")


        #self.addJoint("RKneeAngles_cgm","Right Thigh", "Right Shank","YXZ")
        self.addJoint("RAnkle","Right Shank", "Right Foot","YXZ","RAJC")

        # clinics
        self.setClinicalDescriptor("LHip",enums.DataType.Angle, [0,1,2],[-1.0,-1.0,-1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("LKnee",enums.DataType.Angle, [0,1,2],[+1.0,-1.0,-1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("LAnkle",enums.DataType.Angle, [0,2,1],[-1.0,-1.0,-1.0], [ np.radians(90),0.0,0.0])
        self.setClinicalDescriptor("RHip",enums.DataType.Angle, [0,1,2],[-1.0,+1.0,+1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("RKnee",enums.DataType.Angle, [0,1,2],[+1.0,+1.0,+1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("RAnkle",enums.DataType.Angle, [0,2,1],[-1.0,+1.0,+1.0], [ np.radians(90),0.0,0.0])

        self.setClinicalDescriptor("LPelvis",enums.DataType.Angle,[0,1,2],[1.0,1.0,-1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("RPelvis",enums.DataType.Angle,[0,1,2],[1.0,-1.0,+1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("Left Foot",enums.DataType.Angle,[0,2,1],[1.0,1.0,-1.0], [0.0,0.0,0.0])
        self.setClinicalDescriptor("Right Foot",enums.DataType.Angle,[0,2,1],[1.0,-1.0,1.0], [0.0,0.0,0.0])

        # distal Projection
        self.setClinicalDescriptor("LHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("LHip",enums.DataType.Moment, [1,0,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("RHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("RHip",enums.DataType.Moment, [1,0,2],[1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)

        self.setClinicalDescriptor("LKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("LKnee",enums.DataType.Moment, [1,0,2],[-1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("RKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("RKnee",enums.DataType.Moment, [1,0,2],[-1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)

        self.setClinicalDescriptor("LAnkle",enums.DataType.Force, [0,1,2],[-1.0,+1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("LAnkle",enums.DataType.Moment, [1,2,0],[1.0,-1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Force, [0,1,2],[-1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Moment, [1,2,0],[1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Distal)

        # proximal Projection
        self.setClinicalDescriptor("LHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("LHip",enums.DataType.Moment, [1,0,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("RHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("RHip",enums.DataType.Moment, [1,0,2],[1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)

        self.setClinicalDescriptor("LKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("LKnee",enums.DataType.Moment, [1,0,2],[-1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("RKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("RKnee",enums.DataType.Moment, [1,0,2],[-1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)

        self.setClinicalDescriptor("LAnkle",enums.DataType.Force, [0,1,2],[+1.0,+1.0,+1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("LAnkle",enums.DataType.Moment, [1,0,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Moment, [1,0,2],[1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Proximal)

        # Global Projection
        self.setClinicalDescriptor("LHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("LHip",enums.DataType.Moment, [1,0,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("RHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("RHip",enums.DataType.Moment, [1,0,2],[1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)

        self.setClinicalDescriptor("LKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("LKnee",enums.DataType.Moment, [1,0,2],[-1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("RKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("RKnee",enums.DataType.Moment, [1,0,2],[-1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)

        self.setClinicalDescriptor("LAnkle",enums.DataType.Force, [0,1,2],[+1.0,+1.0,+1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("LAnkle",enums.DataType.Moment, [1,0,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Moment, [1,0,2],[1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.Global)

        # JCS Projection
        self.setClinicalDescriptor("LHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("LHip",enums.DataType.Moment, [1,0,2],[1.0,-1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("RHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("RHip",enums.DataType.Moment, [1,0,2],[1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)

        self.setClinicalDescriptor("LKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("LKnee",enums.DataType.Moment, [1,0,2],[-1.0,-1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("RKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("RKnee",enums.DataType.Moment, [1,0,2],[-1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)


        self.setClinicalDescriptor("LAnkle",enums.DataType.Force, [0,1,2],[-1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("LAnkle",enums.DataType.Moment, [1,2,0],[1.0,-1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Force, [0,1,2],[-1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Moment, [1,2,0],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS)

        # JCS-dual Projection
        self.setClinicalDescriptor("LHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("LHip",enums.DataType.Moment, [1,0,2],[1.0,-1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("RHip",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("RHip",enums.DataType.Moment, [1,0,2],[1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)

        self.setClinicalDescriptor("LKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("LKnee",enums.DataType.Moment, [1,0,2],[-1.0,-1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("RKnee",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("RKnee",enums.DataType.Moment, [1,0,2],[-1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)


        self.setClinicalDescriptor("LAnkle",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("LAnkle",enums.DataType.Moment, [1,2,0],[1.0,1.0,-1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Force, [0,1,2],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)
        self.setClinicalDescriptor("RAnkle",enums.DataType.Moment, [1,2,0],[1.0,1.0,1.0], [0.0,0.0,0.0],projection = enums.MomentProjection.JCS_Dual)




    def calibrationProcedure(self):
        """
            Define the calibration Procedure

            :Return:
                - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
                - `dictRefAnatomical` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
        """

        dictRef={}
        dictRef["Pelvis"]={"TF" : {'sequence':"YZX", 'labels':   ["RASI","LASI","SACR","midASIS"]} }
        dictRef["Left Thigh"]={"TF" : {'sequence':"ZXiY", 'labels':   ["LKNE","LHJC","LTHI","LKNE"]} }
        dictRef["Right Thigh"]={"TF" : {'sequence':"ZXY", 'labels':   ["RKNE","RHJC","RTHI","RKNE"]} }
        dictRef["Left Shank"]={"TF" : {'sequence':"ZXiY", 'labels':   ["LANK","LKJC","LTIB","LANK"]} }
        dictRef["Right Shank"]={"TF" : {'sequence':"ZXY", 'labels':   ["RANK","RKJC","RTIB","RANK"]} }

        dictRef["Left Foot"]={"TF" : {'sequence':"ZXiY", 'labels':   ["LTOE","LAJC",None,"LAJC"]} } # uncorrected Foot - use shank flexion axis (Y) as second axis
        dictRef["Right Foot"]={"TF" : {'sequence':"ZXiY", 'labels':   ["RTOE","RAJC",None,"RAJC"]} } # uncorrected Foot - use shank flexion axis (Y) as second axis


        dictRefAnatomical={}
        dictRefAnatomical["Pelvis"]= {'sequence':"YZX", 'labels':  ["RASI","LASI","SACR","midASIS"]} # normaly : midHJC
        dictRefAnatomical["Left Thigh"]= {'sequence':"ZXiY", 'labels':  ["LKJC","LHJC","LKNE","LHJC"]} # origin = Proximal ( differ from native)
        dictRefAnatomical["Right Thigh"]= {'sequence':"ZXY", 'labels': ["RKJC","RHJC","RKNE","RHJC"]}
        dictRefAnatomical["Left Shank"]={'sequence':"ZXiY", 'labels':   ["LAJC","LKJC","LANK","LKJC"]}
        dictRefAnatomical["Right Shank"]={'sequence':"ZXY", 'labels':  ["RAJC","RKJC","RANK","RKJC"]}

        dictRefAnatomical["Left Foot"]={'sequence':"ZXiY", 'labels':  ["LTOE","LHEE",None,"LAJC"]}    # corrected foot
        dictRefAnatomical["Right Foot"]={'sequence':"ZXiY", 'labels':  ["RTOE","RHEE",None,"RAJC"]}    # corrected foot


        return dictRef,dictRefAnatomical

    def scoreResidualProcedure(self):
        """
            Define the calibration Procedure

            :Return:
                - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
                - `dictRefAnatomical` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
        """

        dict={}
        dict["LHJC"]={"proximal": "Pelvis",  }
        dictRef["Left Thigh"]={"TF" : {'sequence':"ZXiY", 'labels':   ["LKNE","LHJC","LTHI","LKNE"]} }
        dictRef["Right Thigh"]={"TF" : {'sequence':"ZXY", 'labels':   ["RKNE","RHJC","RTHI","RKNE"]} }
        dictRef["Left Shank"]={"TF" : {'sequence':"ZXiY", 'labels':   ["LANK","LKJC","LTIB","LANK"]} }
        dictRef["Right Shank"]={"TF" : {'sequence':"ZXY", 'labels':   ["RANK","RKJC","RTIB","RANK"]} }

        dictRef["Left Foot"]={"TF" : {'sequence':"ZXiY", 'labels':   ["LTOE","LAJC",None,"LAJC"]} } # uncorrected Foot - use shank flexion axis (Y) as second axis
        dictRef["Right Foot"]={"TF" : {'sequence':"ZXiY", 'labels':   ["RTOE","RAJC",None,"RAJC"]} } # uncorrected Foot - use shank flexion axis (Y) as second axis


        dictRefAnatomical={}
        dictRefAnatomical["Pelvis"]= {'sequence':"YZX", 'labels':  ["RASI","LASI","SACR","midASIS"]} # normaly : midHJC
        dictRefAnatomical["Left Thigh"]= {'sequence':"ZXiY", 'labels':  ["LKJC","LHJC","LKNE","LHJC"]} # origin = Proximal ( differ from native)
        dictRefAnatomical["Right Thigh"]= {'sequence':"ZXY", 'labels': ["RKJC","RHJC","RKNE","RHJC"]}
        dictRefAnatomical["Left Shank"]={'sequence':"ZXiY", 'labels':   ["LAJC","LKJC","LANK","LKJC"]}
        dictRefAnatomical["Right Shank"]={'sequence':"ZXY", 'labels':  ["RAJC","RKJC","RANK","RKJC"]}

        dictRefAnatomical["Left Foot"]={'sequence':"ZXiY", 'labels':  ["LTOE","LHEE",None,"LAJC"]}    # corrected foot
        dictRefAnatomical["Right Foot"]={'sequence':"ZXiY", 'labels':  ["RTOE","RHEE",None,"RAJC"]}    # corrected foot


        return dictRef,dictRefAnatomical



    def calibrate(self,aquiStatic, dictRef, dictAnatomic,  options=None):
        """
            Perform full CGM1 calibration.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building **Technical** coordinate system
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building **Anatomical**  coordinate system
               - `options` (dict) - use to pass options, like options altering the standard segment construction.

            .. note:: This method constructs technical and anatomical frane sucessively.

            .. warning : Foot Calibration need attention. Indeed, its technical coordinate system builder requires the anatomical coordinate system of the shank

        """
        #TODO : to input Frane init and Frame end manually

        logging.debug("=====================================================")
        logging.debug("===================CGM CALIBRATION===================")
        logging.debug("=====================================================")

        ff=aquiStatic.GetFirstFrame()
        lf=aquiStatic.GetLastFrame()
        frameInit=ff-ff
        frameEnd=lf-ff+1

        if not self.decoratedModel:
            logging.warning(" Native CGM")
            if not btkTools.isPointExist(aquiStatic,"LKNE"):
                btkTools.smartAppendPoint(aquiStatic,"LKNE",np.zeros((aquiStatic.GetPointFrameNumber(),3) ))
            if not btkTools.isPointExist(aquiStatic,"RKNE"):
                btkTools.smartAppendPoint(aquiStatic,"RKNE",np.zeros((aquiStatic.GetPointFrameNumber(),3) ))

        else:
            logging.warning(" Decorated CGM")

        # ---- Pelvis-THIGH-SHANK CALIBRATION
        #-------------------------------------
        # calibration of technical Referentials
        logging.debug(" --- Pelvis - TF calibration ---")
        logging.debug(" -------------------------------")

        self._pelvis_calibrate(aquiStatic,dictRef,frameInit,frameEnd,options=options)

        logging.debug(" --- Left Thigh- TF calibration ---")
        logging.debug(" ----------------------------------")
        self._left_thigh_calibrate(aquiStatic, dictRef,frameInit,frameEnd,options=options)

        logging.debug(" --- Right Thigh - TF calibration ---")
        logging.debug(" ------------------------------------")
        self._right_thigh_calibrate(aquiStatic, dictRef,frameInit,frameEnd,options=options)

        logging.debug(" --- Left Shank - TF calibration ---")
        logging.debug(" -----------------------------------")
        self._left_shank_calibrate(aquiStatic, dictRef,frameInit,frameEnd,options=options)


        logging.debug(" --- Richt Shank - TF calibration ---")
        logging.debug(" ------------------------------------")
        self._right_shank_calibrate(aquiStatic, dictRef,frameInit,frameEnd,options=options)



        # calibration of anatomical Referentials
        logging.debug(" --- Pelvis - AF calibration ---")
        logging.debug(" -------------------------------")
        self._pelvis_Anatomicalcalibrate(aquiStatic, dictAnatomic,frameInit,frameEnd)

        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Pelvis","Pelvis",referential = "Anatomic"  )

        logging.debug(" --- Left Thigh - AF calibration ---")
        logging.debug(" -----------------------------------")
        self._left_thigh_Anatomicalcalibrate(aquiStatic, dictAnatomic,frameInit,frameEnd)

        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
             self.displayStaticCoordinateSystem( aquiStatic, "Left Thigh","LThigh",referential = "Anatomic"  )


        logging.debug(" --- Right Thigh - AF calibration ---")
        logging.debug(" ------------------------------------")
        self._right_thigh_Anatomicalcalibrate(aquiStatic, dictAnatomic,frameInit,frameEnd)

        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
             self.displayStaticCoordinateSystem( aquiStatic, "Right Thigh","RThigh",referential = "Anatomic"  )


        logging.debug(" --- Thigh Offsets ---")
        logging.debug(" --------------------")


        logging.debug(" ------Left-------")
        if self.mp.has_key("LeftThighRotation") and self.mp["LeftThighRotation"] != 0:
            self.mp_computed["LeftThighRotationOffset"]= -self.mp["LeftThighRotation"]

        else:
            self.getThighOffset(side="left")

        # management of Functional method

        if self.mp_computed["LeftKneeFuncCalibrationOffset"] != 0:

            offset = self.mp_computed["LeftKneeFuncCalibrationOffset"]

            # SARA
            if self.checkCalibrationProperty("LeftFuncKneeMethod","SARA"):
                logging.info("Left knee functional calibration : SARA ")

            # 2DOF
            elif self.checkCalibrationProperty("LeftFuncKneeMethod","2DOF"):
                logging.info("Left knee functional calibration : 2Dof ")

            self._rotateAnatomicalFrame("Left Thigh",offset,
                                        aquiStatic, dictAnatomic,frameInit,frameEnd)



        logging.debug(" ------Right-------")
        if self.mp.has_key("RightThighRotation") and self.mp["RightThighRotation"] != 0:
            self.mp_computed["RightThighRotationOffset"]= self.mp["RightThighRotation"]
        else:
            self.getThighOffset(side="right")

        # management of Functional method
        if self.mp_computed["RightKneeFuncCalibrationOffset"] != 0:

            offset = self.mp_computed["RightKneeFuncCalibrationOffset"]

            # SARA
            if self.checkCalibrationProperty("RightFuncKneeMethod","SARA"):
                logging.info("Left knee functional calibration : SARA ")

            # 2DOF
            elif self.checkCalibrationProperty("RightFuncKneeMethod","2DOF"):
                logging.info("Left knee functional calibration : 2Dof ")

            self._rotateAnatomicalFrame("Right Thigh",offset,
                                        aquiStatic, dictAnatomic,frameInit,frameEnd)




        logging.debug(" --- Left Shank - AF calibration ---")
        logging.debug(" -------------------------------")
        self._left_shank_Anatomicalcalibrate(aquiStatic, dictAnatomic,frameInit,frameEnd)
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Left Shank","LShank",referential = "Anatomic"  )


        logging.debug(" --- Right Shank - AF calibration ---")
        logging.debug(" -------------------------------")
        self._right_shank_Anatomicalcalibrate(aquiStatic, dictAnatomic,frameInit,frameEnd)
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Right Shank","RShank",referential = "Anatomic"  )


        logging.debug(" ---Shank  Offsets ---")
        logging.debug(" ---------------------")

        # shakRotation
        if self.mp.has_key("LeftShankRotation") and self.mp["LeftShankRotation"] != 0:
            self.mp_computed["LeftShankRotationOffset"]= -self.mp["LeftShankRotation"]
        else:
            self.getShankOffsets(side="left")

        if self.mp.has_key("RightShankRotation") and self.mp["RightShankRotation"] != 0:
            self.mp_computed["RightShankRotationOffset"]= self.mp["RightShankRotation"]
        else:
            self.getShankOffsets(side="right")

        # tibial Torsion

        if self.mp.has_key("LeftTibialTorsion") and self.mp["LeftTibialTorsion"] != 0: #   - check if TibialTorsion whithin main mp
            self.mp_computed["LeftTibialTorsionOffset"]= -self.mp["LeftTibialTorsion"]
            self.m_useLeftTibialTorsion=True
        else:
            if self.m_useLeftTibialTorsion: # if useTibialTorsion flag enable from a decorator
                self.getTibialTorsionOffset(side="left")
            else:
                self.mp_computed["LeftTibialTorsionOffset"]= 0

        #   right
        if self.mp.has_key("RightTibialTorsion") and self.mp["RightTibialTorsion"] != 0:
            self.mp_computed["RightTibialTorsionOffset"]= self.mp["RightTibialTorsion"]
            self.m_useRightTibialTorsion=True
        else:
            if self.m_useRightTibialTorsion:
                self.getTibialTorsionOffset(side="right")
            else:
                self.mp_computed["RightTibialTorsionOffset"]= 0


        # AbdAdd offset
        self.getAbdAddAnkleJointOffset(side="left")
        self.getAbdAddAnkleJointOffset(side="right")


        logging.debug(" --- Left Shank Proximal- AF calibration ---")
        logging.debug(" -------------------------------------------")
        #   shank Prox ( copy )
        self.updateSegmentFromCopy("Left Shank Proximal", self.getSegment("Left Shank")) # look out . I copied the shank instance and rename it
        self._left_shankProximal_AnatomicalCalibrate(aquiStatic,dictAnatomic,frameInit,frameEnd,options=options) # alter static Frame
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Left Shank Proximal","LShankProx",referential = "Anatomic"  )

        logging.debug(" --- Right Shank Proximal- AF calibration ---")
        logging.debug(" --------------------------------------------")
        self.updateSegmentFromCopy("Right Shank Proximal", self.getSegment("Right Shank"))
        self._right_shankProximal_AnatomicalCalibrate(aquiStatic,dictAnatomic,frameInit,frameEnd,options=options) # alter static Frame
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Right Shank Proximal","RShankProx",referential = "Anatomic"  )


        # ---- FOOT CALIBRATION
        #-------------------------------------
        # foot ( need  Y-axis of the shank anatomic Frame)
        logging.debug(" --- Left Foot - TF calibration (uncorrected) ---")
        logging.debug(" -------------------------------------------------")
        self._left_unCorrectedFoot_calibrate(aquiStatic, dictRef,frameInit,frameEnd,options=options)
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Left Foot","LFootUncorrected",referential = "technic"  )

        logging.debug(" --- Left Foot - AF calibration (corrected) ---")
        logging.debug(" ----------------------------------------------")
        self._left_foot_corrected_calibrate(aquiStatic, dictAnatomic,frameInit,frameEnd,options=options)
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Left Foot","LFoot",referential = "Anatomic"  )


        logging.debug(" --- Right Foot - TF calibration (uncorrected) ---")
        logging.debug(" -------------------------------------------------")
        self._right_unCorrectedFoot_calibrate(aquiStatic, dictRef,frameInit,frameEnd,options=options)
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Right Foot","RFootUncorrected",referential = "technic"  )

        logging.debug(" --- Right Foot - AF calibration (corrected) ---")
        logging.debug(" -----------------------------------------------")
        self._right_foot_corrected_calibrate(aquiStatic, dictAnatomic,frameInit,frameEnd,options=options)
        if "useDisplayPyCGM2_CoordinateSystem" in options.keys():
            self.displayStaticCoordinateSystem( aquiStatic, "Right Foot","RFoot",referential = "Anatomic"  )

        logging.debug(" --- Foot Offsets ---")
        logging.debug(" --------------------")
        self.getFootOffset(side = "both")


    # ---- Technical Referential Calibration
    def _pelvis_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the pelvis.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `options` (dict) - use to pass options

        """

        pfn = aquiStatic.GetPointFrameNumber()

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0

        seg=self.getSegment("Pelvis")
        seg.resetMarkerLabels()

        # ---  additional markers and Update of the marker segment list

        # new markers
        valSACR=(aquiStatic.GetPoint("LPSI").GetValues() + aquiStatic.GetPoint("RPSI").GetValues()) / 2.0
        btkTools.smartAppendPoint(aquiStatic,"SACR",valSACR,desc="")

        valMidAsis=(aquiStatic.GetPoint("LASI").GetValues() + aquiStatic.GetPoint("RASI").GetValues()) / 2.0
        btkTools.smartAppendPoint(aquiStatic,"midASIS",valMidAsis,desc="")

        seg.addCalibrationMarkerLabel("SACR")
        seg.addCalibrationMarkerLabel("midASIS")

        # new mp
        if self.mp.has_key("PelvisDepth") and self.mp["PelvisDepth"] != 0:
            logging.warning("PelvisDepth defined from your vsk file")
            self.mp_computed["PelvisDepth"] = self.mp["PelvisDepth"]
        else:
            logging.warning("Pelvis Depth computed and added to model parameters")
            self.mp_computed["PelvisDepth"] = np.linalg.norm( valMidAsis.mean(axis=0)-valSACR.mean(axis=0)) - 2.0* (markerDiameter/2.0) -2.0* (basePlate/2.0)

        if self.mp.has_key("InterAsisDistance") and self.mp["InterAsisDistance"] != 0:
            logging.warning("InterAsisDistance defined from your vsk file")
            self.mp_computed["InterAsisDistance"] = self.mp["InterAsisDistance"]
        else:
            logging.warning("asisDistance computed and added to model parameters")
            self.mp_computed["InterAsisDistance"] = np.linalg.norm( aquiStatic.GetPoint("LASI").GetValues().mean(axis=0) - aquiStatic.GetPoint("RASI").GetValues().mean(axis=0))



        # --- Construction of the technical referential
        tf=seg.getReferential("TF")

        #   referential construction
        pt1=aquiStatic.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Pelvis"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)


        # --- Hip Joint centers location
        # anthropometric parameter computed
        if self.mp.has_key("LeftAsisTrocanterDistance") and self.mp["LeftAsisTrocanterDistance"] != 0:
            logging.warning("LeftAsisTrocanterDistance defined from your vsk file")
            self.mp_computed['LeftAsisTrocanterDistance'] = self.mp["LeftAsisTrocanterDistance"]
        else:
            self.mp_computed['LeftAsisTrocanterDistance'] = 0.1288*self.mp['LeftLegLength']-48.56

        if self.mp.has_key("RightAsisTrocanterDistance") and self.mp["RightAsisTrocanterDistance"] != 0:
            logging.warning("RightAsisTrocanterDistance defined from your vsk file")
            self.mp_computed['RightAsisTrocanterDistance'] = self.mp["RightAsisTrocanterDistance"]
        else:
            self.mp_computed['RightAsisTrocanterDistance'] = 0.1288*self.mp['RightLegLength']-48.56

        self.mp_computed['MeanlegLength'] = np.mean( [self.mp['LeftLegLength'],self.mp['RightLegLength'] ])

        # local Position of the hip joint centers

        LHJC_loc,RHJC_loc= modelDecorator.davisRegression(self.mp,self.mp_computed,
                                                    markerDiameter = markerDiameter,
                                                    basePlate = basePlate)


        # left
        if tf.static.isNodeExist("LHJC"):
            nodeLHJC = tf.static.getNode_byLabel("LHJC")

        else:
            tf.static.addNode("LHJC_cgm1",LHJC_loc,positionType="Local",desc = "Davis")
            tf.static.addNode("LHJC",LHJC_loc,positionType="Local",desc = "Davis")
            nodeLHJC = tf.static.getNode_byLabel("LHJC")

        btkTools.smartAppendPoint(aquiStatic,"LHJC",
                    nodeLHJC.m_global* np.ones((pfn,3)),
                    desc=nodeLHJC.m_desc)

        # right
        if tf.static.isNodeExist("RHJC"):
            nodeRHJC = tf.static.getNode_byLabel("RHJC")
        else:
            tf.static.addNode("RHJC_cgm1",RHJC_loc,positionType="Local",desc = "Davis")
            tf.static.addNode("RHJC",RHJC_loc,positionType="Local",desc = "Davis")
            nodeRHJC = tf.static.getNode_byLabel("RHJC")

        btkTools.smartAppendPoint(aquiStatic,"RHJC",
                    nodeRHJC.m_global*np.ones((pfn,3)),
                    desc=nodeRHJC.m_desc)

        val=(aquiStatic.GetPoint("LHJC").GetValues() + aquiStatic.GetPoint("RHJC").GetValues()) / 2.0
        btkTools.smartAppendPoint(aquiStatic,"midHJC",val,desc="")
        seg.addCalibrationMarkerLabel("midHJC")

        #nodes
        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        for label in seg.m_calibration_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # seg.addCalibrationMarkerLabel("LHJC")
        # seg.addCalibrationMarkerLabel("RHJC")

        # TODO how to deal with self.setCalibrationProperty( "LHJC_node",  "LHJC_cgm1")

    def _left_thigh_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the left thigh.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `options` (dict) - use to pass options

        """
        pfn = aquiStatic.GetPointFrameNumber()

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0

        seg = self.getSegment("Left Thigh")
        seg.resetMarkerLabels()

        # --- Construction of the technical referential
        tf=seg.getReferential("TF")

        pt1=aquiStatic.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Left Thigh"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)

        # --- knee Joint centers location from chord method
        if self.mp.has_key("LeftThighRotation") and self.mp["LeftThighRotation"] != 0:
            logging.warning("LeftThighRotation defined from your vsk file")
            self.mp_computed["LeftThighRotationOffset"] = self.mp["LeftThighRotation"]* -1.0
        else:
            self.mp_computed["LeftThighRotationOffset"] = 0.0

        LKJC = modelDecorator.chord( (self.mp["LeftKneeWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["LeftThighRotationOffset"] )

        if tf.static.isNodeExist("LKJC"):
            nodeLKJC = tf.static.getNode_byLabel("LKJC")
        else:
            tf.static.addNode("LKJC_chord",LKJC,positionType="Global",desc = "Chord")
            tf.static.addNode("LKJC",LKJC,positionType="Global",desc = "Chord")
            nodeLKJC = tf.static.getNode_byLabel("LKJC")

        btkTools.smartAppendPoint(aquiStatic,"LKJC",
                    nodeLKJC.m_global* np.ones((pfn,3)),
                    desc=nodeLKJC.m_desc)

        # node for all markers
        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # for label in seg.m_calibration_markers:
        #     globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #     tf.static.addNode(label,globalPosition,positionType="Global")

        node_prox = self.getSegment("Pelvis").getReferential("TF").static.getNode_byLabel("LHJC")
        tf.static.addNode("LHJC",node_prox.m_global,positionType="Global",desc = node_prox.m_desc)

        #seg.addTrackingMarkerLabel("LHJC")
        #seg.addCalibrationMarkerLabel("LKJC")


    def _right_thigh_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the right thigh.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `options` (dict) - use to pass options

        """
        pfn = aquiStatic.GetPointFrameNumber()

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0


        seg = self.getSegment("Right Thigh")
        seg.resetMarkerLabels()


        # --- Construction of the technical referential
        tf=seg.getReferential("TF")

        pt1=aquiStatic.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Right Thigh"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)


        # --- knee Joint centers location
        if self.mp.has_key("RightThighRotation") and self.mp["RightThighRotation"] != 0:
            logging.warning("RightThighRotation defined from your vsk file")
            self.mp_computed["RightThighRotationOffset"] = self.mp["RightThighRotation"]
        else:
            self.mp_computed["RightThighRotationOffset"] = 0.0

        RKJC = modelDecorator.chord( (self.mp["RightKneeWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3,beta=self.mp_computed["RightThighRotationOffset"] ) # could consider a previous offset

        if tf.static.isNodeExist("RKJC"):
            nodeRKJC = tf.static.getNode_byLabel("RKJC")
        else:
            tf.static.addNode("RKJC_chord",RKJC,positionType="Global",desc = "Chord")
            tf.static.addNode("RKJC",RKJC,positionType="Global",desc = "Chord")
            nodeRKJC = tf.static.getNode_byLabel("RKJC")

        btkTools.smartAppendPoint(aquiStatic,"RKJC",
                    nodeRKJC.m_global* np.ones((pfn,3)),
                    desc=nodeRKJC.m_desc)


        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # for label in seg.m_calibration_markers:
        #     globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #     tf.static.addNode(label,globalPosition,positionType="Global")

        node_prox = self.getSegment("Pelvis").getReferential("TF").static.getNode_byLabel("RHJC")
        tf.static.addNode("RHJC",node_prox.m_global,positionType="Global",desc = node_prox.m_desc)

        # seg.addTrackingMarkerLabel("RHJC")
        # seg.addCalibrationMarkerLabel("RKJC")

    def _left_shank_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the left shank.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `options` (dict) - use to pass options

        """
        pfn = aquiStatic.GetPointFrameNumber()

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0


        seg = self.getSegment("Left Shank")
        seg.resetMarkerLabels()

        # ---  additional markers and Update of the marker segment list


        # --- Construction of the technical referential
        tf=seg.getReferential("TF")

        pt1=aquiStatic.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Left Shank"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)


        # --- ankle Joint centers location
        if self.mp.has_key("LeftShankRotation") and self.mp["LeftShankRotation"] != 0:
            logging.warning("LeftShankRotation defined from your vsk file")
            self.mp_computed["LeftShankRotationOffset"] = self.mp["LeftShankRotation"]*-1.0
        else:
            self.mp_computed["LeftShankRotationOffset"]=0.0

        LAJC = modelDecorator.chord( (self.mp["LeftAnkleWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["LeftShankRotationOffset"] )

        # --- node manager
        if tf.static.isNodeExist("LAJC"):
            nodeLAJC = tf.static.getNode_byLabel("LAJC")
        else:
            tf.static.addNode("LAJC_chord",LAJC,positionType="Global",desc = "Chord")
            tf.static.addNode("LAJC",LAJC,positionType="Global",desc = "Chord")
            nodeLAJC = tf.static.getNode_byLabel("LAJC")

        btkTools.smartAppendPoint(aquiStatic,"LAJC",
                    nodeLAJC.m_global* np.ones((pfn,3)),
                    desc=nodeLAJC.m_desc)


        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # for label in seg.m_calibration_markers:
        #     globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #     tf.static.addNode(label,globalPosition,positionType="Global")

        node_prox = self.getSegment("Left Thigh").getReferential("TF").static.getNode_byLabel("LKJC")
        tf.static.addNode("LKJC",node_prox.m_global,positionType="Global",desc = node_prox.m_desc)

        # seg.addTrackingMarkerLabel("LKJC")
        # seg.addCalibrationMarkerLabel("LAJC")

    def _right_shank_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the right shank.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `options` (dict) - use to pass options
        """
        pfn = aquiStatic.GetPointFrameNumber()

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0



        seg = self.getSegment("Right Shank")
        seg.resetMarkerLabels()


        # --- Construction of the technical Referential
        tf=seg.getReferential("TF")

        pt1=aquiStatic.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Right Shank"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)

        # --- ankle Joint centers location
        if self.mp.has_key("RightShankRotation") and self.mp["RightShankRotation"] != 0:
            logging.warning("RightShankRotation defined from your vsk file")
            self.mp_computed["RightShankRotationOffset"] = self.mp["RightShankRotation"]
        else:
            self.mp_computed["RightShankRotationOffset"]=0.0

        RAJC = modelDecorator.chord( (self.mp["RightAnkleWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["RightShankRotationOffset"] )

        # --- node manager
        if tf.static.isNodeExist("RAJC"):
            nodeRAJC = tf.static.getNode_byLabel("RAJC")
        else:
            tf.static.addNode("RAJC_chord",RAJC,positionType="Global",desc = "Chord")
            tf.static.addNode("RAJC",RAJC,positionType="Global",desc = "Chord")
            nodeRAJC = tf.static.getNode_byLabel("RAJC")

        btkTools.smartAppendPoint(aquiStatic,"RAJC",
                    nodeRAJC.m_global* np.ones((pfn,3)),
                    desc=nodeRAJC.m_desc)


        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # for label in seg.m_calibration_markers:
        #     globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #     tf.static.addNode(label,globalPosition,positionType="Global")

        node_prox = self.getSegment("Right Thigh").getReferential("TF").static.getNode_byLabel("RKJC")
        tf.static.addNode("RKJC",node_prox.m_global,positionType="Global",desc = node_prox.m_desc)

        # seg.addTrackingMarkerLabel("RKJC")
        # seg.addCalibrationMarkerLabel("RAJC")

    def _left_unCorrectedFoot_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the left Foot.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `options` (dict) - use to pass options



            .. warning:: Need shank anatomical Coordinate system

        """
        seg = self.getSegment("Left Foot")
        #seg.resetMarkerLabels()

        # ---  additional markers and Update of the marker segment list
        #seg.addMarkerLabel("LKJC") !!!

        if "useBodyBuilderFoot" in options.keys() and options["useBodyBuilderFoot"]:
            logging.warning("You use a Left uncorrected foot sequence different than native CGM1")
            dictRef["Left Foot"]={"TF" : {'sequence':"ZYX", 'labels':   ["LTOE","LAJC","LKJC","LAJC"]} } # uncorrected Foot - use shank flexion axis (Y) as second axis


        # --- Construction of the technical Referential
        tf=seg.getReferential("TF")

        pt1=aquiStatic.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)#LTOE
        pt2=aquiStatic.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)#AJC


        if dictRef["Left Foot"]["TF"]['labels'][2] is not None:
            pt3=aquiStatic.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            v=(pt3-pt1)
        else:
            v=self.getSegment("Left Shank").anatomicalFrame.static.m_axisY #(pt3-pt1)


        ptOrigin=aquiStatic.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Left Foot"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)

        # --- node manager
        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # for label in seg.m_calibration_markers:
        #     globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #     tf.static.addNode(label,globalPosition,positionType="Global")

        node_prox = self.getSegment("Left Shank").getReferential("TF").static.getNode_byLabel("LAJC")
        tf.static.addNode("LAJC",node_prox.m_global,positionType="Global",desc = node_prox.m_desc)

        # seg.addTrackingMarkerLabel("LAJC") # for LS fitting


    def _right_unCorrectedFoot_calibrate(self,aquiStatic, dictRef,frameInit,frameEnd, options=None):
        """
            Construct the Technical Coordinate system of the right Foot.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical referentials
               - `options` (dict) - use to pass options

            .. note:: uncorrected foot defined a technical coordinate system of the foot

            .. warning:: Need shank anatomical Coordinate system

        """


        seg = self.getSegment("Right Foot")
        seg.resetMarkerLabels()

        # ---  additional markers and Update of the marker segment list
        #seg.addMarkerLabel("RKJC")


        if "useBodyBuilderFoot" in options.keys() and options["useBodyBuilderFoot"]:
            logging.warning("You use a right uncorrected foot sequence different than native CGM1")
            dictRef["Right Foot"]={"TF" : {'sequence':"ZYX", 'labels':   ["RTOE","RAJC","RKJC","RAJC"]} } # uncorrected Foot - use shank flexion axis (Y) as second axis



        # --- Construction of the anatomical Referential
        tf=seg.getReferential("TF")

        pt1=aquiStatic.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        if dictRef["Right Foot"]["TF"]['labels'][2] is not None:
            pt3=aquiStatic.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            v=(pt3-pt1)
        else:
            v=self.getSegment("Right Shank").anatomicalFrame.static.m_axisY #(pt3-pt1)



        ptOrigin=aquiStatic.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictRef["Right Foot"]["TF"]['sequence'])

        tf.static.m_axisX=x
        tf.static.m_axisY=y
        tf.static.m_axisZ=z
        tf.static.setRotation(R)
        tf.static.setTranslation(ptOrigin)

        # --- node manager
        for label in seg.m_tracking_markers:
            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            tf.static.addNode(label,globalPosition,positionType="Global")

        # for label in seg.m_calibration_markers:
        #     globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #     tf.static.addNode(label,globalPosition,positionType="Global")

        node_prox = self.getSegment("Right Shank").getReferential("TF").static.getNode_byLabel("RAJC")
        tf.static.addNode("RAJC",node_prox.m_global,positionType="Global",desc = node_prox.m_desc)
        # seg.addTrackingMarkerLabel("RAJC")


    def _pelvis_Anatomicalcalibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd):

        """
            Construct the Anatomical Coordinate system of the pelvis.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame


        """



        seg=self.getSegment("Pelvis")


        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Pelvis"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Pelvis"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictAnatomic["Pelvis"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Pelvis"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Pelvis"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # --- node manager
        for node in seg.getReferential("TF").static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())

        # length
        lhjc = seg.anatomicalFrame.static.getNode_byLabel("LHJC").m_local
        rhjc = seg.anatomicalFrame.static.getNode_byLabel("RHJC").m_local
        seg.setLength(np.linalg.norm(lhjc-rhjc))


    def _left_thigh_Anatomicalcalibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd):
        """
            Construct the Anatomical Coordinate system of the left thigh.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame


        """

        seg=self.getSegment("Left Thigh")

        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Left Thigh"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Left Thigh"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictAnatomic["Left Thigh"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Left Thigh"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Left Thigh"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)


        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))


        # --- node manager
        for node in seg.getReferential("TF").static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())

        # --- compute length
        hjc = seg.anatomicalFrame.static.getNode_byLabel("LHJC").m_local
        kjc = seg.anatomicalFrame.static.getNode_byLabel("LKJC").m_local

        seg.setLength(np.linalg.norm(kjc-hjc))






    def _right_thigh_Anatomicalcalibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd):
        """
            Construct the Anatomical Coordinate system of the right thigh.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
        """

        seg=self.getSegment("Right Thigh")

        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Right Thigh"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Right Thigh"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictAnatomic["Right Thigh"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Right Thigh"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Right Thigh"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # --- node manager
        for node in seg.getReferential("TF").static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())

        # --- compute lenght
        hjc = seg.anatomicalFrame.static.getNode_byLabel("RHJC").m_local
        kjc = seg.anatomicalFrame.static.getNode_byLabel("RKJC").m_local

        seg.setLength(np.linalg.norm(kjc-hjc))

    def _left_shank_Anatomicalcalibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd):
        """
            Construct the Anatomical Coordinate system of the left shank.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
        """

        seg=self.getSegment("Left Shank")

        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Left Shank"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Left Shank"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictAnatomic["Left Shank"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Left Shank"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Left Shank"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # --- node manager
        for node in seg.getReferential("TF").static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())

        # --- compute length
        kjc = seg.anatomicalFrame.static.getNode_byLabel("LKJC").m_local
        ajc = seg.anatomicalFrame.static.getNode_byLabel("LAJC").m_local

        seg.setLength(np.linalg.norm(ajc-kjc))

    def _left_shankProximal_AnatomicalCalibrate(self,aquiStatic,dictAnat,frameInit,frameEnd,options=None):
        """
            Construct the Anatomical Coordinate system of the left proximal shank.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
        """

        if self.m_useLeftTibialTorsion:
            tibialTorsion = np.deg2rad(self.mp_computed["LeftTibialTorsionOffset"])
        else:
            tibialTorsion = 0.0


        seg=self.getSegment("Left Shank Proximal")


        # --- set static anatomical Referential
        # Rotation of the static anatomical Referential by the tibial Torsion angle
        rotZ_tibRot = np.eye(3,3)
        rotZ_tibRot[0,0] = np.cos(tibialTorsion)
        rotZ_tibRot[0,1] = np.sin(tibialTorsion)
        rotZ_tibRot[1,0] = - np.sin(tibialTorsion)
        rotZ_tibRot[1,1] = np.cos(tibialTorsion)

        R = np.dot(seg.anatomicalFrame.static.getRotation(),rotZ_tibRot)

        # update frame
        csFrame=frame.Frame()
        csFrame.update(R,seg.anatomicalFrame.static.getTranslation())
        seg.anatomicalFrame.setStaticFrame(csFrame)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # --- node manager
        for node in tf.static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())


    def _right_shank_Anatomicalcalibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd):
        """
            Construct the Anatomical Coordinate system of the right shank.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
        """

        seg=self.getSegment("Right Shank")

        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Right Shank"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Right Shank"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt3=aquiStatic.GetPoint(str(dictAnatomic["Right Shank"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Right Shank"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=(pt3-pt1)
        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Right Shank"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # --- node manager
        for node in tf.static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())


        # --- compute length
        kjc = seg.anatomicalFrame.static.getNode_byLabel("RKJC").m_local
        ajc = seg.anatomicalFrame.static.getNode_byLabel("RAJC").m_local
        seg.setLength(np.linalg.norm(ajc-kjc))


    def _right_shankProximal_AnatomicalCalibrate(self,aquiStatic,dictAnat,frameInit,frameEnd,options=None):
        """
            Construct the Anatomical Coordinate system of the right proximal shank.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
        """

        if self.m_useRightTibialTorsion:
            tibialTorsion = np.deg2rad(self.mp_computed["RightTibialTorsionOffset"])
        else:
            tibialTorsion = 0.0


        seg=self.getSegment("Right Shank Proximal")

        # --- set static anatomical Referential
        # Rotation of the static anatomical Referential by the tibial Torsion angle
        rotZ_tibRot = np.eye(3,3)
        rotZ_tibRot[0,0] = np.cos(tibialTorsion)
        rotZ_tibRot[0,1] = np.sin(tibialTorsion)
        rotZ_tibRot[1,0] = - np.sin(tibialTorsion)
        rotZ_tibRot[1,1] = np.cos(tibialTorsion)

        R = np.dot(seg.anatomicalFrame.static.getRotation(),rotZ_tibRot)

        csFrame=frame.Frame()
        csFrame.update(R,seg.anatomicalFrame.static.getTranslation() )
        seg.anatomicalFrame.setStaticFrame(csFrame)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # node manager
        # --- node manager
        for node in tf.static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())


    def _left_foot_corrected_calibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd,options = None):
        """
            Construct the Anatomical Coordinate system of the left foot.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `options` (dict) - use to pass options
        """

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0


        seg=self.getSegment("Left Foot")

        if "useBodyBuilderFoot" in options.keys() and options["useBodyBuilderFoot"]:
            logging.warning("You use a Left corrected foot sequence different than native CGM1")
            dictAnatomic["Left Foot"]={'sequence':"ZYX", 'labels':  ["LTOE","LHEE","LKJC","LAJC"]}    # corrected foot


        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Left Foot"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0) # LTOE
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Left Foot"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0) # LHEE

        if ("leftFlatFoot" in options.keys() and options["leftFlatFoot"]):
            logging.warning ("option (leftFlatFoot) enable")
            if ("LeftSoleDelta" in self.mp.keys() and self.mp["LeftSoleDelta"]!=0):
                logging.warning ("option (LeftSoleDelta) compensation")

            pt2[2] = pt1[2]+self.mp['LeftSoleDelta']


        if dictAnatomic["Left Foot"]['labels'][2] is not None:
            pt3=aquiStatic.GetPoint(str(dictAnatomic["Left Foot"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            v=(pt3-pt1)
        else:
            v=self.getSegment("Left Shank").anatomicalFrame.static.m_axisY #(pt3-pt1)

        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Left Foot"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Left Foot"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        # This section compute the actual Relative Rotation between anatomical and technical Referential
        trueRelativeMatrixAnatomic = np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation())
        y,x,z = euler.euler_yxz(trueRelativeMatrixAnatomic)

        # the native CGM relative rotation leaves out the rotation around Z
        rotX =np.array([[1,0,0],
                        [0,np.cos(x),-np.sin(x)],
                         [0,np.sin(x),np.cos(x)]])
        rotY =np.array([[np.cos(y),0,np.sin(y)],
                        [0,1,0],
                         [-np.sin(y),0,np.cos(y)]])

        relativeMatrixAnatomic = np.dot(rotY,rotX)

        tf.setRelativeMatrixAnatomic( relativeMatrixAnatomic)
        tf.additionalInfos["trueRelativeMatrix"] = trueRelativeMatrixAnatomic

        # --- node manager
        for node in tf.static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())


        # --- compute amthropo
        # length
        toe = seg.anatomicalFrame.static.getNode_byLabel("LTOE").m_local
        hee = seg.anatomicalFrame.static.getNode_byLabel("LHEE").m_local
        seg.setLength(np.linalg.norm(toe-hee)- markerDiameter/2.0)

        # com
        toe = seg.anatomicalFrame.static.getNode_byLabel("LTOE").m_global
        hee = seg.anatomicalFrame.static.getNode_byLabel("LHEE").m_global
        footLongAxis = (toe-hee)/np.linalg.norm(toe-hee)

        com = hee + 0.5 * seg.m_bsp["length"] * footLongAxis

        seg.anatomicalFrame.static.addNode("com",com,positionType="Global")


        # foot origin offset and Toe origin
        local_oo = np.array([-11, -11, -120])/169.0*seg.m_bsp["length"]
        local_to =local_oo + np.array([0, 0, -seg.m_bsp["length"]/3.0])

        seg.anatomicalFrame.static.addNode("FootOriginOffset",local_oo,positionType="Local")
        seg.anatomicalFrame.static.addNode("ToeOrigin",local_to,positionType="Local")

    def _right_foot_corrected_calibrate(self,aquiStatic, dictAnatomic,frameInit,frameEnd,options = None):
        """
            Construct the Anatomical Coordinate system of the right foot.

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame
               - `options` (dict) - use to pass options
        """

        seg=self.getSegment("Right Foot")

        if "useBodyBuilderFoot" in options.keys() and options["useBodyBuilderFoot"]:
            logging.warning("You use a Right corrected foot sequence different than native CGM1")
            dictAnatomic["Right Foot"]={'sequence':"ZYX", 'labels':  ["RTOE","RHEE","RKJC","RAJC"]}    # corrected foot

        # --- Construction of the anatomical Referential
        pt1=aquiStatic.GetPoint(str(dictAnatomic["Right Foot"]['labels'][0])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        pt2=aquiStatic.GetPoint(str(dictAnatomic["Right Foot"]['labels'][1])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
        #pt3=aquiStatic.GetPoint(str(dictAnatomic["Right Foot"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        if ("rightFlatFoot" in options.keys() and options["rightFlatFoot"]):
            logging.warning ("option (rightFlatFoot) enable")

            if ("RightSoleDelta" in self.mp.keys() and self.mp["RightSoleDelta"]!=0):
                logging.warning ("option (RightSoleDelta) compensation")

            pt2[2] = pt1[2]+self.mp['RightSoleDelta']


        if dictAnatomic["Right Foot"]['labels'][2] is not None:
            pt3=aquiStatic.GetPoint(str(dictAnatomic["Right Foot"]['labels'][2])).GetValues()[frameInit:frameEnd,:].mean(axis=0)
            v=(pt3-pt1)
        else:
            v=self.getSegment("Right Shank").anatomicalFrame.static.m_axisY #(pt3-pt1)


        ptOrigin=aquiStatic.GetPoint(str(dictAnatomic["Right Foot"]['labels'][3])).GetValues()[frameInit:frameEnd,:].mean(axis=0)

        a1=(pt2-pt1)
        a1=a1/np.linalg.norm(a1)

        v=v/np.linalg.norm(v)

        a2=np.cross(a1,v)
        a2=a2/np.linalg.norm(a2)

        x,y,z,R=frame.setFrameData(a1,a2,dictAnatomic["Right Foot"]['sequence'])

        seg.anatomicalFrame.static.m_axisX=x
        seg.anatomicalFrame.static.m_axisY=y
        seg.anatomicalFrame.static.m_axisZ=z
        seg.anatomicalFrame.static.setRotation(R)
        seg.anatomicalFrame.static.setTranslation(ptOrigin)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        # actual Relative Rotation
        trueRelativeMatrixAnatomic = np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation())
        y,x,z = euler.euler_yxz(trueRelativeMatrixAnatomic)

        # native CGM relative rotation
        rotX =np.array([[1,0,0],
                        [0,np.cos(x),-np.sin(x)],
                         [0,np.sin(x),np.cos(x)]])

        rotY =np.array([[np.cos(y),0,np.sin(y)],
                        [0,1,0],
                         [-np.sin(y),0,np.cos(y)]])

        relativeMatrixAnatomic = np.dot(rotY,rotX)

        tf.setRelativeMatrixAnatomic(relativeMatrixAnatomic)

        # --- node manager
        for node in seg.getReferential("TF").static.getNodes():
            seg.anatomicalFrame.static.addNode(node.getLabel(),node.getGlobal(),positionType="Global", desc = node.getDescription())

        # --- anthropo
        # length
        toe = seg.anatomicalFrame.static.getNode_byLabel("RTOE").m_local
        hee = seg.anatomicalFrame.static.getNode_byLabel("RHEE").m_local
        seg.setLength(np.linalg.norm(toe-hee))

        # com
        toe = seg.anatomicalFrame.static.getNode_byLabel("RTOE").m_global
        hee = seg.anatomicalFrame.static.getNode_byLabel("RHEE").m_global
        com = (toe+hee)/2.0

        seg.anatomicalFrame.static.addNode("com",com,positionType="Global")


        # foot origin offset and Toe origin
        local_oo = np.array([-11, 11, -120])/169.0*seg.m_bsp["length"]
        local_to =local_oo + np.array([0, 0, -seg.m_bsp["length"]/3.0])

        seg.anatomicalFrame.static.addNode("FootOriginOffset",local_oo,positionType="Local")
        seg.anatomicalFrame.static.addNode("ToeOrigin",local_to,positionType="Local")


    def _rotateAnatomicalFrame(self,segmentLabel, angle, aquiStatic, dictAnatomic,frameInit,frameEnd,):
        """
           Rotate the anatomical frame along its longitudnial axis

            :Parameters:
               - `aquiStatic` (btkAcquisition) - btkAcquisition instance from a static c3d
               - `dictAnatomic` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `frameInit` (dict) - first frame
               - `frameEnd` (dict) - end frame


        """

        seg=self.getSegment(segmentLabel)

        angle = np.deg2rad(angle)

        # --- set static anatomical Referential
        # Rotation of the static anatomical Referential by the tibial Torsion angle
        rotZ = np.eye(3,3)
        rotZ[0,0] = np.cos(angle)
        rotZ[0,1] = -np.sin(angle)
        rotZ[1,0] = np.sin(angle)
        rotZ[1,1] = np.cos(angle)

        R = np.dot(seg.anatomicalFrame.static.getRotation(),rotZ) # apply rotation




        csFrame=frame.Frame() # NOTE : Creation of a new Frame remove all former node
        csFrame.update(R,seg.anatomicalFrame.static.getTranslation() )
        seg.anatomicalFrame.setStaticFrame(csFrame)

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

        # add node
        # get previous nodes
        previous_nodes = seg.anatomicalFrame.static.getNodes()

        for node in previous_nodes:
            globalPosition=node.getGlobal()
            seg.anatomicalFrame.static.addNode(node.getLabel(),globalPosition,positionType="Global",desc = node.getDescription())

#        # node manager
#        for label in seg.m_markerLabels:
#            globalPosition=aquiStatic.GetPoint(str(label)).GetValues()[frameInit:frameEnd,:].mean(axis=0)
#            seg.anatomicalFrame.static.addNode(label,globalPosition,positionType="Global")

        # --- relative rotation Technical Anatomical
        tf=seg.getReferential("TF")
        tf.setRelativeMatrixAnatomic( np.dot(tf.static.getRotation().T,seg.anatomicalFrame.static.getRotation()))

    # ---- Offsets -------

    def getThighOffset(self,side= "both"):
        """
            Get Thigh offset. Angle between the projection of the lateral thigh marker and the knee flexion axis

            :Parameters:
               - `side` (str) - body side  (both, left, right)
        """

        if side == "both" or side=="left":

            # Left --------
            kneeFlexionAxis=    np.dot(self.getSegment("Left Thigh").anatomicalFrame.static.getRotation().T,
                                           self.getSegment("Left Thigh").anatomicalFrame.static.m_axisY)


            proj_kneeFlexionAxis = np.array([ kneeFlexionAxis[0],
                                   kneeFlexionAxis[1],
                                     0])
            v_kneeFlexionAxis = proj_kneeFlexionAxis/np.linalg.norm(proj_kneeFlexionAxis)


            thiLocal = self.getSegment("Left Thigh").anatomicalFrame.static.getNode_byLabel("LTHI").m_local
            proj_thi = np.array([ thiLocal[0],
                                   thiLocal[1],
                                     0])
            v_thi = proj_thi/np.linalg.norm(proj_thi)

            angle=np.rad2deg(geometry.angleFrom2Vectors(v_kneeFlexionAxis, v_thi, self.getSegment("Left Thigh").anatomicalFrame.static.m_axisZ))

            self.mp_computed["LeftThighRotationOffset"]= -angle # angle needed : Thi toward knee flexion
            logging.debug(" left Thigh Offset => %s " % str(self.mp_computed["LeftThighRotationOffset"]))


        if side == "both" or side=="right":


            kneeFlexionAxis=    np.dot(self.getSegment("Right Thigh").anatomicalFrame.static.getRotation().T,
                                           self.getSegment("Right Thigh").anatomicalFrame.static.m_axisY)


            proj_kneeFlexionAxis = np.array([ kneeFlexionAxis[0],
                                   kneeFlexionAxis[1],
                                     0])
            v_kneeFlexionAxis = proj_kneeFlexionAxis/np.linalg.norm(proj_kneeFlexionAxis)


            thiLocal = self.getSegment("Right Thigh").anatomicalFrame.static.getNode_byLabel("RTHI").m_local
            proj_thi = np.array([ thiLocal[0],
                                   thiLocal[1],
                                     0])
            v_thi = proj_thi/np.linalg.norm(proj_thi)

            v_kneeFlexionAxis_opp = geometry.oppositeVector(v_kneeFlexionAxis)

            angle=np.rad2deg(geometry.angleFrom2Vectors(v_kneeFlexionAxis_opp, v_thi,self.getSegment("Right Thigh").anatomicalFrame.static.m_axisZ))

            self.mp_computed["RightThighRotationOffset"]=-angle # angle needed : Thi toward knee flexion
            logging.debug(" right Thigh Offset => %s " % str(self.mp_computed["RightThighRotationOffset"]))



    def getShankOffsets(self, side = "both"):
        """
            Get shank offsets :

             - Angle between the projection of the lateral shank marker and the ankle flexion axis
             - Angle between the projection of the lateral ankle marker and the ankle flexion axis

            :Parameters:
               - `side` (str) - body side  (both, left, right)
        """

        if side == "both" or side == "left" :

            ankleFlexionAxis=    np.dot(self.getSegment("Left Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Left Shank").anatomicalFrame.static.m_axisY)


            proj_ankleFlexionAxis = np.array([ ankleFlexionAxis[0],
                               ankleFlexionAxis[1],
                                 0])

            v_ankleFlexionAxis = proj_ankleFlexionAxis/np.linalg.norm(proj_ankleFlexionAxis)

            #"****** left angle beetween tib and flexion axis **********"
            tibLocal = self.getSegment("Left Shank").anatomicalFrame.static.getNode_byLabel("LTIB").m_local
            proj_tib = np.array([ tibLocal[0],
                               tibLocal[1],
                                 0])
            v_tib = proj_tib/np.linalg.norm(proj_tib)

            angle=np.rad2deg(geometry.angleFrom2Vectors(v_ankleFlexionAxis,v_tib,self.getSegment("Left Shank").anatomicalFrame.static.m_axisZ))
            self.mp_computed["LeftShankRotationOffset"]= -angle
            logging.debug(" left shank offset => %s " % str(self.mp_computed["LeftShankRotationOffset"]))


            #"****** left angle beetween ank and flexion axis (not used by native pig)**********"
            ANK =  self.getSegment("Left Shank").anatomicalFrame.static.getNode_byLabel("LANK").m_local
            v_ank = ANK/np.linalg.norm(ANK)
            angle = np.rad2deg(geometry.angleFrom2Vectors(v_ankleFlexionAxis,v_ank,self.getSegment("Left Shank").anatomicalFrame.static.m_axisZ))

            self.mp_computed["leftProjectionAngle_AnkleFlexion_LateralAnkle"] = angle
            #logging.info(" left projection offset => %s " % str(self.mp_computed["leftProjectionAngle_AnkleFlexion_LateralAnkle"]))



        if side == "both" or side == "right" :

            ankleFlexionAxis=    np.dot(self.getSegment("Right Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Right Shank").anatomicalFrame.static.m_axisY)


            proj_ankleFlexionAxis = np.array([ ankleFlexionAxis[0],
                               ankleFlexionAxis[1],
                                 0])

            v_ankleFlexionAxis = proj_ankleFlexionAxis/np.linalg.norm(proj_ankleFlexionAxis)

            #"****** right angle beetween tib and flexion axis **********"
            tibLocal = self.getSegment("Right Shank").anatomicalFrame.static.getNode_byLabel("RTIB").m_local
            proj_tib = np.array([ tibLocal[0],
                               tibLocal[1],
                                 0])

            v_tib = proj_tib/np.linalg.norm(proj_tib)
            v_ankleFlexionAxis_opp = geometry.oppositeVector(v_ankleFlexionAxis)


            angle = np.rad2deg(geometry.angleFrom2Vectors(v_ankleFlexionAxis_opp,v_tib,self.getSegment("Right Shank").anatomicalFrame.static.m_axisZ))
            self.mp_computed["RightShankRotationOffset"]= -angle
            logging.debug(" right shank offset => %s " % str(self.mp_computed["RightShankRotationOffset"]))



            #"****** right angle beetween ank and flexion axis ( Not used by Native Pig)**********"
            ANK =  self.getSegment("Right Shank").anatomicalFrame.static.getNode_byLabel("RANK").m_local
            v_ank = ANK/np.linalg.norm(ANK)

            angle = np.rad2deg(geometry.angleFrom2Vectors(v_ankleFlexionAxis_opp,v_ank,self.getSegment("Right Shank").anatomicalFrame.static.m_axisZ))

            self.mp_computed["rightProjectionAngle_AnkleFlexion_LateralAnkle"] = angle
            #logging.info(" right projection offset => %s " % str(self.mp_computed["rightProjectionAngle_AnkleFlexion_LateralAnkle"]))


    def getTibialTorsionOffset(self, side = "both"):
        """
            Get tibial torsion offset :

            :Parameters:
               - `side` (str) - body side  (both, left, right)
        """

        if side == "both" or side == "left" :

            #"****** right angle beetween anatomical axis **********"
            kneeFlexionAxis=    np.dot(self.getSegment("Left Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Left Thigh").anatomicalFrame.static.m_axisY)


            proj_kneeFlexionAxis = np.array([ kneeFlexionAxis[0],
                               kneeFlexionAxis[1],
                                 0])

            v_kneeFlexionAxis= proj_kneeFlexionAxis/np.linalg.norm(proj_kneeFlexionAxis)

            ankleFlexionAxis=    np.dot(self.getSegment("Left Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Left Shank").anatomicalFrame.static.m_axisY)


            proj_ankleFlexionAxis = np.array([ ankleFlexionAxis[0],
                               ankleFlexionAxis[1],
                                 0])

            v_ankleFlexionAxis = proj_ankleFlexionAxis/np.linalg.norm(proj_ankleFlexionAxis)

            angle= np.rad2deg( geometry.angleFrom2Vectors(v_kneeFlexionAxis,v_ankleFlexionAxis,self.getSegment("Left Shank").anatomicalFrame.static.m_axisZ))
            self.mp_computed["LeftTibialTorsionOffset"] = angle
            logging.debug(" left tibial torsion => %s " % str(self.mp_computed["LeftTibialTorsionOffset"]))


        if side == "both" or side == "right" :

            #"****** right angle beetween anatomical axis **********"
            kneeFlexionAxis=    np.dot(self.getSegment("Right Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Right Thigh").anatomicalFrame.static.m_axisY)


            proj_kneeFlexionAxis = np.array([ kneeFlexionAxis[0],
                               kneeFlexionAxis[1],
                                 0])

            v_kneeFlexionAxis= proj_kneeFlexionAxis/np.linalg.norm(proj_kneeFlexionAxis)

            ankleFlexionAxis=    np.dot(self.getSegment("Right Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Right Shank").anatomicalFrame.static.m_axisY)


            proj_ankleFlexionAxis = np.array([ ankleFlexionAxis[0],
                               ankleFlexionAxis[1],
                                 0])

            v_ankleFlexionAxis = proj_ankleFlexionAxis/np.linalg.norm(proj_ankleFlexionAxis)


            angle= np.rad2deg(geometry.angleFrom2Vectors(v_kneeFlexionAxis,v_ankleFlexionAxis,self.getSegment("Right Shank").anatomicalFrame.static.m_axisZ))
            self.mp_computed["RightTibialTorsionOffset"] = angle
            logging.debug(" Right tibial torsion => %s " % str(self.mp_computed["RightTibialTorsionOffset"]))

    def getAbdAddAnkleJointOffset(self,side="both"):
        """
            Get Abd/Add ankle offset : angle n the frontal plan between the ankle marker and the ankle flexion axis

            :Parameters:
               - `side` (str) - body side  (both, left, right)
        """
        if side == "both" or side == "left" :

            ankleFlexionAxis=    np.dot(self.getSegment("Left Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Left Shank").anatomicalFrame.static.m_axisY)



            v_ankleFlexionAxis = ankleFlexionAxis/np.linalg.norm(ankleFlexionAxis)

            ANK =  self.getSegment("Left Shank").anatomicalFrame.static.getNode_byLabel("LANK").m_local - \
                   self.getSegment("Left Shank").anatomicalFrame.static.getNode_byLabel("LAJC").m_local
            v_ank = ANK/np.linalg.norm(ANK)

            angle = np.rad2deg(geometry.angleFrom2Vectors(v_ankleFlexionAxis,v_ank,self.getSegment("Left Shank").anatomicalFrame.static.m_axisX))
            self.mp_computed["LeftAnkleAbAddOffset"] = angle
            logging.debug(" LeftAnkleAbAddOffset => %s " % str(self.mp_computed["LeftAnkleAbAddOffset"]))


        if side == "both" or side == "right" :
            ankleFlexionAxis=    np.dot(self.getSegment("Right Shank").anatomicalFrame.static.getRotation().T,
                                       self.getSegment("Right Shank").anatomicalFrame.static.m_axisY)


            v_ankleFlexionAxis = ankleFlexionAxis/np.linalg.norm(ankleFlexionAxis)

            v_ankleFlexionAxis_opp = geometry.oppositeVector(v_ankleFlexionAxis)
            ANK =  self.getSegment("Right Shank").anatomicalFrame.static.getNode_byLabel("RANK").m_local - \
                   self.getSegment("Right Shank").anatomicalFrame.static.getNode_byLabel("RAJC").m_local
            v_ank = ANK/np.linalg.norm(ANK)

            angle = np.rad2deg(geometry.angleFrom2Vectors(v_ankleFlexionAxis_opp,v_ank,self.getSegment("Right Shank").anatomicalFrame.static.m_axisX))
            self.mp_computed["RightAnkleAbAddOffset"] = angle
            logging.debug(" RightAnkleAbAddOffset => %s " % str(self.mp_computed["RightAnkleAbAddOffset"]))


    def getFootOffset(self, side = "both"):
        """
            Get foot offsets :

              -  plantar flexion offset
              -  rotation offset

            :Parameters:
               - `side` (str) - body side  (both, left, right)
        """


        if side == "both" or side == "left" :
            R = self.getSegment("Left Foot").getReferential("TF").relativeMatrixAnatomic
            y,x,z = euler.euler_yxz(R)

            self.mp_computed["LeftStaticPlantFlexOffset"] = np.rad2deg(y)
            logging.debug(" LeftStaticPlantFlexOffset => %s " % str(self.mp_computed["LeftStaticPlantFlexOffset"]))

            self.mp_computed["LeftStaticRotOffset"] = np.rad2deg(x)
            logging.debug(" LeftStaticRotOffset => %s " % str(self.mp_computed["LeftStaticRotOffset"]))


        if side == "both" or side == "right" :
            R = self.getSegment("Right Foot").getReferential("TF").relativeMatrixAnatomic
            y,x,z = euler.euler_yxz(R)

            self.mp_computed["RightStaticPlantFlexOffset"] = np.rad2deg(y)
            logging.debug(" RightStaticPlantFlexOffset => %s " % str(self.mp_computed["RightStaticPlantFlexOffset"]))

            self.mp_computed["RightStaticRotOffset"] = np.rad2deg(x)
            logging.debug(" RightStaticRotOffset => %s " % str(self.mp_computed["RightStaticRotOffset"]))



    def getViconFootOffset(self, side):
        """
            Get vicon compatible foot offsets :

            :Parameters:
               - `side` (str) - body side  (left, right)

            .. note:  standard vicon CGM consider positive = dorsiflexion  and  abduction

        """
        if side  == "Left":
            spf = self.mp_computed["LeftStaticPlantFlexOffset"] * -1.0
            logging.debug(" Left staticPlantarFlexion offset (Vicon compatible)  => %s " % str(spf))


            sro = self.mp_computed["LeftStaticRotOffset"] * -1.0
            logging.debug("Left staticRotation offset (Vicon compatible)  => %s " % str(sro))

        if side  == "Right":
            spf = self.mp_computed["RightStaticPlantFlexOffset"] * -1.0
            logging.debug("Right staticRotation offset (Vicon compatible)  => %s " % str(spf))

            sro = self.mp_computed["RightStaticRotOffset"]
            logging.debug("Right staticRotation offset (Vicon compatible)  => %s " % str(sro))

        return spf,sro


    def getViconAnkleAbAddOffset(self, side):
        """
            Get vicon compatible foot offsets :

            :Parameters:
               - `side` (str) - body side  (left, right)

            .. note:  standard vicon CGM consider positive = dorsiflexion  and  abduction

        """
        if side  == "Left":
            abdAdd = self.mp_computed["LeftAnkleAbAddOffset"] * -1.0
            logging.debug(" Left AnkleAbAddOffset offset (Vicon compatible)  => %s " % str(abdAdd))


        if side  == "Right":
            abdAdd = self.mp_computed["RightAnkleAbAddOffset"]
            logging.debug(" Right AnkleAbAddOffset offset (Vicon compatible)  => %s " % str(abdAdd))

        return abdAdd


    def getViconThighOffset(self, side):
        """
            Get vicon compatible thigh offset

            :Parameters:
               - `side` (str) - body side  (both, left, right)

            .. note:  standard vicon CGM consider positive = internal rotation

        """


        if side  == "Left":
            val = self.mp_computed["LeftThighRotationOffset"] * -1.0
            logging.debug(" Left thigh offset (Vicon compatible)  => %s " % str(val))
            return val

        if side  == "Right":
            val = self.mp_computed["RightThighRotationOffset"]
            logging.debug(" Right thigh offset (Vicon compatible)  => %s " % str(val))
            return val


    def getViconShankOffset(self, side):
        """
            Get vicon compatible shank offset

            :Parameters:
               - `side` (str) - body side  (both, left, right)

            .. note:  standard vicon CGM consider positive = internal rotation

        """

        if side  == "Left":
            val = self.mp_computed["LeftShankRotationOffset"] * -1.0
            logging.debug(" Left shank offset (Vicon compatible)  => %s " % str(val))
            return val

        if side  == "Right":
            val = self.mp_computed["RightShankRotationOffset"]
            logging.debug(" Right shank offset (Vicon compatible)  => %s " % str(val))
            return val

    def getViconTibialTorsion(self, side):
        """
            Get vicon compatible tibial tosion offset

            :Parameters:
               - `side` (str) - body side  (both, left, right)

            .. note:  standard vicon CGM consider positive = internal rotation

        """

        if side  == "Left":
            val = self.mp_computed["LeftTibialTorsionOffset"] * -1.0
            logging.debug(" Left tibial torsion (Vicon compatible)  => %s " % str(val))
            return val

        if side  == "Right":
            val = self.mp_computed["RightTibialTorsionOffset"]
            logging.debug(" Right tibial torsion  (Vicon compatible)  => %s " % str(val))
            return val

    # ----- Motion --------------
    def computeOptimizedSegmentMotion(self,aqui,segments, dictRef,dictAnat,motionMethod,options ):
        """
        warning : look at the origin, it s not the procimal joint ! this process break down the dependancy to other segment
        """

        # ---remove all  direction marker from tracking markers.
        for seg in self.m_segmentCollection:
            selectedTrackingMarkers=list()
            for marker in seg.m_tracking_markers:
                if marker in self.__class__.MARKERS : # get class variable MARKER even from child
                    selectedTrackingMarkers.append(marker)
            seg.m_tracking_markers= selectedTrackingMarkers


        logging.debug("--- Segmental Least-square motion process ---")
        if "Pelvis" in segments:
            self._pelvis_motion_optimize(aqui, dictRef, motionMethod)
            self._anatomical_motion(aqui,"Pelvis",originLabel = str(dictAnat["Pelvis"]['labels'][3]))

        if "Left Thigh" in segments:
            self._left_thigh_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Left Thigh",originLabel = "LKJC")


        if "Right Thigh" in segments:
            self._right_thigh_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Right Thigh",originLabel = "RKJC")


        if "Left Shank" in segments:
            self._left_shank_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Left Shank",originLabel = "LAJC")

        if "Right Shank" in segments:
            self._right_shank_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Right Shank",originLabel = "RAJC")

        if "Left Foot" in segments:
            self._left_foot_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Left Foot",originLabel = "LHEE")

        if "Right Foot" in segments:
            self._right_foot_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Right Foot",originLabel = "RHEE")





    def computeMotion(self,aqui, dictRef,dictAnat, motionMethod,options=None ):
        """
        Compute Motion of both **Technical and Anatomical** coordinate systems

        :Parameters:

           - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
           - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
           - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
           - `motionMethod` (pyCGM2.enums) - method use to compute segment pose
           - `options` (dict) - dictionnary use to pass options

        """
        logging.debug("=====================================================")
        logging.debug("===================  CGM MOTION   ===================")
        logging.debug("=====================================================")

        pigStaticProcessing= True if "pigStatic" in options.keys() and options["pigStatic"] else False


        if motionMethod == enums.motionMethod.Determinist: #cmf.motionMethod.Native:


            #if not pigStaticProcessing:
            logging.debug(" - Pelvis - motion -")
            logging.debug(" -------------------")
            self._pelvis_motion(aqui, dictRef, dictAnat)

            logging.debug(" - Left Thigh - motion -")
            logging.debug(" -----------------------")
            self._left_thigh_motion(aqui, dictRef, dictAnat,options=options)


            # if rotation offset from knee functional calibration methods
            if self.mp_computed["LeftKneeFuncCalibrationOffset"]:
                offset = self.mp_computed["LeftKneeFuncCalibrationOffset"]
                self._rotate_anatomical_motion("Left Thigh",offset,
                                        aqui,options=options)

            logging.debug(" - Right Thigh - motion -")
            logging.debug(" ------------------------")
            self._right_thigh_motion(aqui, dictRef, dictAnat,options=options)


            if  self.mp_computed["RightKneeFuncCalibrationOffset"]:
                offset = self.mp_computed["RightKneeFuncCalibrationOffset"]
                self._rotate_anatomical_motion("Right Thigh",offset,
                                        aqui,options=options)


            logging.debug(" - Left Shank - motion -")
            logging.debug(" -----------------------")
            self._left_shank_motion(aqui, dictRef, dictAnat,options=options)


            logging.debug(" - Left Shank-proximal - motion -")
            logging.debug(" --------------------------------")
            self._left_shankProximal_motion(aqui,dictAnat,options=options)

            logging.debug(" - Right Shank - motion -")
            logging.debug(" ------------------------")
            self._right_shank_motion(aqui, dictRef, dictAnat,options=options)

            logging.debug(" - Right Shank-proximal - motion -")
            logging.debug(" ---------------------------------")
            self._right_shankProximal_motion(aqui,dictAnat,options=options)

            logging.debug(" - Left foot - motion -")
            logging.debug(" ----------------------")

            if pigStaticProcessing:
                self._left_foot_motion_static(aqui, dictAnat,options=options)
            else:
                self._left_foot_motion(aqui, dictRef, dictAnat,options=options)

            logging.debug(" - Right foot - motion -")
            logging.debug(" ----------------------")

            if pigStaticProcessing:
                self._right_foot_motion_static(aqui, dictAnat,options=options)
            else:
                self._right_foot_motion(aqui, dictRef, dictAnat,options=options)

        if motionMethod == enums.motionMethod.Sodervisk:

            # ---remove all  direction marker from tracking markers.
            for seg in self.m_segmentCollection:

                selectedTrackingMarkers=list()

                for marker in seg.m_tracking_markers:
                    if marker in self.__class__.MARKERS :
                        selectedTrackingMarkers.append(marker)

                seg.m_tracking_markers= selectedTrackingMarkers


            logging.debug("--- Segmental Least-square motion process ---")
            self._pelvis_motion_optimize(aqui, dictRef, motionMethod)
            self._anatomical_motion(aqui,"Pelvis",originLabel = str(dictAnat["Pelvis"]['labels'][3]))

            self._left_thigh_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Left Thigh",originLabel = str(dictAnat["Left Thigh"]['labels'][3]))


            self._right_thigh_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Right Thigh",originLabel = str(dictAnat["Right Thigh"]['labels'][3]))



            self._left_shank_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Left Shank",originLabel = str(dictAnat["Left Shank"]['labels'][3]))

            self._right_shank_motion_optimize(aqui, dictRef,motionMethod)
            self._anatomical_motion(aqui,"Right Shank",originLabel = str(dictAnat["Right Shank"]['labels'][3]))

            # foot
            # issue with least-square optimization :  AJC - HEE and TOE may be inline -> singularities !!
#            self._leftFoot_motion_optimize(aqui, dictRef,dictAnat, motionMethod)
#            self._rightFoot_motion_optimize(aqui, dictRef,dictAnat, motionMethod)

            self._left_foot_motion(aqui, dictRef, dictAnat,options=options)
            self._right_foot_motion(aqui, dictRef, dictAnat,options=options)


        logging.debug("--- Display Coordinate system ---")
        logging.debug(" --------------------------------")



        if not pigStaticProcessing:
            if "usePyCGM2_coordinateSystem" in options.keys() and options["usePyCGM2_coordinateSystem"]:
                self.displayMotionCoordinateSystem( aqui,  "Pelvis" , "Pelvis" )
                self.displayMotionCoordinateSystem( aqui,  "Left Thigh" , "LThigh" )
                self.displayMotionCoordinateSystem( aqui,  "Right Thigh" , "RThigh" )
                self.displayMotionCoordinateSystem( aqui,  "Left Shank" , "LShank" )
                self.displayMotionCoordinateSystem( aqui,  "Left Shank Proximal" , "LShankProx" )
                self.displayMotionCoordinateSystem( aqui,  "Right Shank" , "RShank" )
                self.displayMotionCoordinateSystem( aqui,  "Right Shank Proximal" , "RShankProx" )
                self.displayMotionCoordinateSystem( aqui,  "Left Foot" , "LFoot" )
                self.displayMotionCoordinateSystem( aqui,  "Right Foot" , "RFoot" )
                self.displayMotionCoordinateSystem( aqui,  "Left Foot" , "LFootUncorrected",referential="technical")
                self.displayMotionCoordinateSystem( aqui,  "Right Foot" , "RFootUncorrected",referential="technical")


            else:

                self.displayMotionViconCoordinateSystem(aqui,"Pelvis","PELO","PELA","PELL","PELP")
                self.displayMotionViconCoordinateSystem(aqui,"Left Thigh","LFEO","LFEA","LFEL","LFEP")
                self.displayMotionViconCoordinateSystem(aqui,"Right Thigh","RFEO","RFEA","RFEL","RFEP")
                self.displayMotionViconCoordinateSystem(aqui,"Left Shank","LTIO","LTIA","LTIL","LTIP")
                self.displayMotionViconCoordinateSystem(aqui,"Left Shank Proximal","LTPO","LTPA","LTPL","LTPP")
                self.displayMotionViconCoordinateSystem(aqui,"Right Shank","RTIO","RTIA","RTIL","RTIP")
                self.displayMotionViconCoordinateSystem(aqui,"Right Shank Proximal","RTPO","RTPA","RTPL","RTPP")
                self.displayMotionViconCoordinateSystem(aqui,"Left Foot","LFOO","LFOA","LFOL","LFOP")
                self.displayMotionViconCoordinateSystem(aqui,"Right Foot","RFOO","RFOA","RFOL","RFOP")



    # ----- native motion ------



    def _pelvis_motion(self,aqui, dictRef,dictAnat):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the pelvis

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system

        """

        seg=self.getSegment("Pelvis")

        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]        # reinit Technical Frame Motion (USEFUL if you work with several aquisitions)

        #  additional markers
        val=(aqui.GetPoint("LPSI").GetValues() + aqui.GetPoint("RPSI").GetValues()) / 2.0
        btkTools.smartAppendPoint(aqui,"SACR",val, desc="")

        val=(aqui.GetPoint("LASI").GetValues() + aqui.GetPoint("RASI").GetValues()) / 2.0
        btkTools.smartAppendPoint(aqui,"midASIS",val, desc="")

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictRef["Pelvis"]["TF"]['labels'][3])).GetValues()[i,:]

            a1=(pt2-pt1)

            a1=np.divide(a1,np.linalg.norm(a1))


            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Pelvis"]["TF"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


        # --- HJCs
        desc_L = seg.getReferential('TF').static.getNode_byLabel("LHJC").m_desc
        desc_R = seg.getReferential('TF').static.getNode_byLabel("RHJC").m_desc

        values_LHJCnode=seg.getReferential('TF').getNodeTrajectory("LHJC")
        values_RHJCnode=seg.getReferential('TF').getNodeTrajectory("RHJC")

        btkTools.smartAppendPoint(aqui,"LHJC",values_LHJCnode, desc=desc_L)
        btkTools.smartAppendPoint(aqui,"RHJC",values_RHJCnode, desc=desc_R)


        # --- motion of the anatomical referential

        seg.anatomicalFrame.motion=[]

        # additional markers
        val=(aqui.GetPoint("LHJC").GetValues() + aqui.GetPoint("RHJC").GetValues()) / 2.0
        btkTools.smartAppendPoint(aqui,"midHJC",val,desc="")

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictAnat["Pelvis"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictAnat["Pelvis"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictAnat["Pelvis"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictAnat["Pelvis"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Pelvis"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))



    def _left_thigh_motion(self,aqui, dictRef,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the left thigh

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0

        seg=self.getSegment("Left Thigh")


        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]   # reinit Technical Frame Motion ()

        # additional markers
        # NA

        # computation
        LKJCvalues=np.zeros((aqui.GetPointFrameNumber(),3))

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictRef["Left Thigh"]["TF"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Left Thigh"]["TF"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

            LKJCvalues[i,:] = modelDecorator.chord( (self.mp["LeftKneeWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["LeftThighRotationOffset"] )


        #btkTools.smartAppendPoint(aqui,"LKJC_Chord",LKJCvalues,desc="chord")

        # --- LKJC
        if  "useLeftKJCmarker" in options.keys():
            LKJCvalues = aqui.GetPoint(options["useLeftKJCmarker"]).GetValues()
            desc = aqui.GetPoint(options["useLeftKJCmarker"]).GetDescription()
            btkTools.smartAppendPoint(aqui,"LKJC",LKJCvalues,desc=desc)

        # final LKJC ( just check if KJC already exist)
        if not btkTools.isPointExist(aqui,"LKJC"):
            desc = seg.getReferential('TF').static.getNode_byLabel("LKJC").m_desc
            #LKJCvalues = aqui.GetPoint("LKJC_Chord").GetValues()
            btkTools.smartAppendPoint(aqui,"LKJC",LKJCvalues,desc=str("Chord-"+desc))



        # --- motion of the anatomical referential
        seg.anatomicalFrame.motion=[]

        # additional markers
        # NA
        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictAnat["Left Thigh"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictAnat["Left Thigh"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictAnat["Left Thigh"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictAnat["Left Thigh"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Left Thigh"]['sequence'])


            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))

    def _right_thigh_motion(self,aqui, dictRef,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the right thigh

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0

        seg=self.getSegment("Right Thigh")

        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]

        # additional markers
        # NA

        # computation
        RKJCvalues=np.zeros((aqui.GetPointFrameNumber(),3))

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictRef["Right Thigh"]["TF"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Right Thigh"]["TF"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


            RKJCvalues[i,:] = modelDecorator.chord( (self.mp["RightKneeWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["RightThighRotationOffset"] )

        #btkTools.smartAppendPoint(aqui,"RKJC_Chord",RKJCvalues,desc="chord")

        # --- RKJC
        if  "useRightKJCmarker" in options.keys():
            RKJCvalues = aqui.GetPoint(options["useRightKJCmarker"]).GetValues()
            desc = aqui.GetPoint(options["useRightKJCmarker"]).GetDescription()
            btkTools.smartAppendPoint(aqui,"RKJC",RKJCvalues,desc=desc)

        # final LKJC ( just check if KJC already exist)
        if not btkTools.isPointExist(aqui,"RKJC"):
            desc = seg.getReferential('TF').static.getNode_byLabel("RKJC").m_desc
            #RKJCvalues = aqui.GetPoint("RKJC_Chord").GetValues()
            btkTools.smartAppendPoint(aqui,"RKJC",RKJCvalues,desc=str("Chord-"+desc))


        # --- motion of the anatomical referential

        # additional markers
        # NA

        # computation
        seg.anatomicalFrame.motion=[]
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictAnat["Right Thigh"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictAnat["Right Thigh"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictAnat["Right Thigh"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictAnat["Right Thigh"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Right Thigh"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))





    def _left_shank_motion(self,aqui, dictRef,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the left shank

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0

        seg=self.getSegment("Left Shank")

        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]

        # additional markers
        # NA

        # computation
        LAJCvalues=np.zeros((aqui.GetPointFrameNumber(),3))


        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictRef["Left Shank"]["TF"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Left Shank"]["TF"]['sequence'])


            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


            LAJCvalues[i,:] = modelDecorator.chord( (self.mp["LeftAnkleWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["LeftShankRotationOffset"] )

            # update of the AJC location with rotation around abdAddAxis
            LAJCvalues[i,:] = self._rotateAjc(LAJCvalues[i,:],pt2,pt1,-self.mp_computed["LeftAnkleAbAddOffset"])


        # --- LAJC
        desc_node = seg.getReferential('TF').static.getNode_byLabel("LAJC").m_desc
        if self.mp_computed["LeftAnkleAbAddOffset"] > 0.01:
            desc="chord+AbAdRot-"+desc_node
        else:
            desc="chord"+desc_node


        #btkTools.smartAppendPoint(aqui,"LAJC_Chord",LAJCvalues,desc=desc)


        # --- LAJC
        if  "useLeftAJCmarker" in options.keys():
            LAJCvalues = aqui.GetPoint(options["useLeftAJCmarker"]).GetValues()
            desc = aqui.GetPoint(options["useLeftAJCmarker"]).GetDescription()
            btkTools.smartAppendPoint(aqui,"LAJC",LAJCvalues,desc=desc)

        # final LKJC ( just check if KJC already exist)
        if not btkTools.isPointExist(aqui,"LAJC"):
            #LAJCvalues = aqui.GetPoint("LAJC_Chord").GetValues()
            btkTools.smartAppendPoint(aqui,"LAJC",LAJCvalues,desc=desc)



#        if not "forceAJC" in options.keys() or not options["forceAJC"]:
#            btkTools.smartAppendPoint(aqui,"LAJC",LAJCvalues, desc=desc)


        # --- motion of the anatomical referential
        seg.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictAnat["Left Shank"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictAnat["Left Shank"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictAnat["Left Shank"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictAnat["Left Shank"]['labels'][3])).GetValues()[i,:]

            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Left Shank"]['sequence'])
            csFrame=frame.Frame()

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))




    def _left_shankProximal_motion(self,aqui,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the left proximal shank

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """
        seg=self.getSegment("Left Shank")
        segProx=self.getSegment("Left Shank Proximal")


        # --- managment of tibial torsion

        if self.m_useLeftTibialTorsion:
            tibialTorsion = np.deg2rad(self.mp_computed["LeftTibialTorsionOffset"])
        else:
            tibialTorsion = 0.0

        if "pigStatic" in options.keys() and options["pigStatic"]:
            tibialTorsion = 0.0


        # --- motion of both technical and anatomical referentials of the proximal shank
        segProx.getReferential("TF").motion =[]
        segProx.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        rotZ_tibRot = np.eye(3,3)
        rotZ_tibRot[0,0] = np.cos(tibialTorsion)
        rotZ_tibRot[0,1] = np.sin(tibialTorsion)
        rotZ_tibRot[1,0] = - np.sin(tibialTorsion)
        rotZ_tibRot[1,1] = np.cos(tibialTorsion)
        LKJC = aqui.GetPoint(str(dictAnat["Left Shank"]['labels'][3]))

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):
            ptOrigin=LKJC.GetValues()[i,:]
            segProx.getReferential("TF").addMotionFrame(seg.getReferential("TF").motion[i]) # copy technical shank

            R = np.dot(seg.anatomicalFrame.motion[i].getRotation(),rotZ_tibRot) # affect Tibial torsion to anatomical shank

            csFrame.update(R,ptOrigin)
            segProx.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))



    def _right_shank_motion(self,aqui, dictRef,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the right shank

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options
        """

        if "markerDiameter" in options.keys():
            logging.info(" option (markerDiameter) found ")
            markerDiameter = options["markerDiameter"]
        else:
            markerDiameter=14.0

        if "basePlate" in options.keys():
            logging.info(" option (basePlate) found ")
            basePlate = options["basePlate"]
        else:
            basePlate=2.0

        seg=self.getSegment("Right Shank")


        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]

        # additional markers
        # NA

        # computation
        RAJCvalues=np.zeros((aqui.GetPointFrameNumber(),3))

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][0])).GetValues()[i,:] #ank
            pt2=aqui.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][1])).GetValues()[i,:] #kjc
            pt3=aqui.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][2])).GetValues()[i,:] #tib
            ptOrigin=aqui.GetPoint(str(dictRef["Right Shank"]["TF"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Right Shank"]["TF"]['sequence'])


            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

            # ajc position from chord modified by shank offset
            RAJCvalues[i,:] = modelDecorator.chord( (self.mp["RightAnkleWidth"]+ markerDiameter)/2.0 ,pt1,pt2,pt3, beta=self.mp_computed["RightShankRotationOffset"] )

            # update of the AJC location with rotation around abdAddAxis
            RAJCvalues[i,:] = self._rotateAjc(RAJCvalues[i,:],pt2,pt1,   self.mp_computed["RightAnkleAbAddOffset"])

        # --- RAJC
        desc_node = seg.getReferential('TF').static.getNode_byLabel("RAJC").m_desc
        if self.mp_computed["RightAnkleAbAddOffset"] >0.01:
            desc="chord+AbAdRot-"+desc_node
        else:
            desc="chord"+desc_node

        #btkTools.smartAppendPoint(aqui,"RAJC_Chord",RAJCvalues,desc=desc)

        # --- LAJC
        if  "useRightAJCmarker" in options.keys():
            RAJCvalues = aqui.GetPoint(options["useRightAJCmarker"]).GetValues()
            desc = aqui.GetPoint(options["useRightAJCmarker"]).GetDescription()
            btkTools.smartAppendPoint(aqui,"RAJC",RAJCvalues,desc=desc)

        # final LKJC ( just check if KJC already exist)
        if not btkTools.isPointExist(aqui,"RAJC"):
            #RAJCvalues = aqui.GetPoint("RAJC_Chord").GetValues()
            btkTools.smartAppendPoint(aqui,"RAJC",RAJCvalues,desc=desc)


        # --- motion of the anatomical referential
        seg.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictAnat["Right Shank"]['labels'][0])).GetValues()[i,:]
            pt2=aqui.GetPoint(str(dictAnat["Right Shank"]['labels'][1])).GetValues()[i,:]
            pt3=aqui.GetPoint(str(dictAnat["Right Shank"]['labels'][2])).GetValues()[i,:]
            ptOrigin=aqui.GetPoint(str(dictAnat["Right Shank"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=(pt3-pt1)
            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Right Shank"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))

    def _right_shankProximal_motion(self,aqui,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the right proximal shank

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options
        """


        seg=self.getSegment("Right Shank")
        segProx=self.getSegment("Right Shank Proximal")


        # --- management of the tibial torsion
        if self.m_useRightTibialTorsion:
            tibialTorsion = np.deg2rad(self.mp_computed["RightTibialTorsionOffset"])
        else:
            tibialTorsion = 0.0


        # --- motion of both technical and anatomical referentials of the proximal shank
        segProx.getReferential("TF").motion =[]
        segProx.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        rotZ_tibRot = np.eye(3,3)
        rotZ_tibRot[0,0] = np.cos(tibialTorsion)
        rotZ_tibRot[0,1] = np.sin(tibialTorsion)
        rotZ_tibRot[1,0] = - np.sin(tibialTorsion)
        rotZ_tibRot[1,1] = np.cos(tibialTorsion)

        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):
            ptOrigin=aqui.GetPoint(str(dictAnat["Right Shank"]['labels'][3])).GetValues()[i,:]

            segProx.getReferential("TF").addMotionFrame(seg.getReferential("TF").motion[i]) # copy technical shank

            R = np.dot(seg.anatomicalFrame.motion[i].getRotation(),rotZ_tibRot)

            csFrame.update(R,ptOrigin)
            segProx.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))





    def _left_foot_motion(self,aqui, dictRef,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the left foot

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """
        seg=self.getSegment("Left Foot")

        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][0])).GetValues()[i,:] #toe
            pt2=aqui.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][1])).GetValues()[i,:] #ajc

            if dictRef["Left Foot"]["TF"]['labels'][2] is not None:
                pt3=aqui.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][2])).GetValues()[i,:]
                v=(pt3-pt1)
            else:
                if "viconCGM1compatible" in options.keys() and options["viconCGM1compatible"]:
                    v=self.getSegment("Left Shank Proximal").anatomicalFrame.motion[i].m_axisY

                else:
                    v=self.getSegment("Left Shank").anatomicalFrame.motion[i].m_axisY


            ptOrigin=aqui.GetPoint(str(dictRef["Left Foot"]["TF"]['labels'][3])).GetValues()[i,:]


            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))


            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Left Foot"]["TF"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


        # --- motion of the anatomical referential
        seg.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):
            ptOrigin=aqui.GetPoint(str(dictAnat["Left Foot"]['labels'][3])).GetValues()[i,:]

            R = np.dot(seg.getReferential("TF").motion[i].getRotation(), seg.getReferential("TF").relativeMatrixAnatomic)



            csFrame.update(R,ptOrigin)
            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))



    def _right_foot_motion(self,aqui, dictRef,dictAnat,options=None):
        """
            Compute Motion of both Technical and Anatomical coordinate systems of the right foot

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """
        seg=self.getSegment("Right Foot")


        # --- motion of the technical referential
        seg.getReferential("TF").motion =[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            pt1=aqui.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][0])).GetValues()[i,:] #toe
            pt2=aqui.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][1])).GetValues()[i,:] #ajc

            if dictRef["Right Foot"]["TF"]['labels'][2] is not None:
                pt3=aqui.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][2])).GetValues()[i,:]
                v=(pt3-pt1)
            else:
                if "viconCGM1compatible" in options.keys() and options["viconCGM1compatible"] :
                    v=self.getSegment("Right Shank Proximal").anatomicalFrame.motion[i].m_axisY

                else:
                    v=self.getSegment("Right Shank").anatomicalFrame.motion[i].m_axisY

            ptOrigin=aqui.GetPoint(str(dictRef["Right Foot"]["TF"]['labels'][3])).GetValues()[i,:]

            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))


            x,y,z,R=frame.setFrameData(a1,a2,dictRef["Right Foot"]["TF"]['sequence'])

            csFrame.m_axisX=x
            csFrame.m_axisY=y
            csFrame.m_axisZ=z
            csFrame.setRotation(R)
            csFrame.setTranslation(ptOrigin)

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


        # --- motion of the anatomical referential

        # additional markers
        # NA

        # computation
        seg.anatomicalFrame.motion=[]
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):
            ptOrigin=aqui.GetPoint(str(dictAnat["Right Foot"]['labels'][3])).GetValues()[i,:]

            R = np.dot(seg.getReferential("TF").motion[i].getRotation(), seg.getReferential("TF").relativeMatrixAnatomic)

            csFrame.update(R,ptOrigin)
            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))

    # ---- static PIG -----

    def _left_foot_motion_static(self,aquiStatic, dictAnat,options=None):

        """
        compute foot anatomicalFrame from marker
        """

        seg=self.getSegment("Left Foot")

        seg.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aquiStatic.GetPointFrameNumber()):
            ptOrigin=aquiStatic.GetPoint(str(dictAnat["Left Foot"]['labels'][3])).GetValues()[i,:]


            pt1=aquiStatic.GetPoint(str(dictAnat["Left Foot"]['labels'][0])).GetValues()[i,:] #toe
            pt2=aquiStatic.GetPoint(str(dictAnat["Left Foot"]['labels'][1])).GetValues()[i,:] #hee

            if dictAnat["Left Foot"]['labels'][2] is not None:
                pt3=aquiStatic.GetPoint(str(dictAnat["Left Foot"]['labels'][2])).GetValues()[i,:]
                v=(pt3-pt1)
            else:
                v=self.getSegment("Left Shank").anatomicalFrame.motion[i].m_axisY # distal segment

            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))


            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Left Foot"]['sequence'])

            csFrame.update(R,ptOrigin)
            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))


    def _right_foot_motion_static(self,aquiStatic, dictAnat,options=None):

        seg=self.getSegment("Right Foot")

        seg.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        csFrame=frame.Frame()
        for i in range(0,aquiStatic.GetPointFrameNumber()):
            ptOrigin=aquiStatic.GetPoint(str(dictAnat["Right Foot"]['labels'][3])).GetValues()[i,:]


            pt1=aquiStatic.GetPoint(str(dictAnat["Right Foot"]['labels'][0])).GetValues()[i,:] #toe
            pt2=aquiStatic.GetPoint(str(dictAnat["Right Foot"]['labels'][1])).GetValues()[i,:] #hee

            if dictAnat["Right Foot"]['labels'][2] is not None:
                pt3=aquiStatic.GetPoint(str(dictAnat["Right Foot"]['labels'][2])).GetValues()[i,:]
                v=(pt3-pt1)
            else:
                v=self.getSegment("Right Shank").anatomicalFrame.motion[i].m_axisY # distal segment

            a1=(pt2-pt1)
            a1=np.divide(a1,np.linalg.norm(a1))

            v=np.divide(v,np.linalg.norm(v))

            a2=np.cross(a1,v)
            a2=np.divide(a2,np.linalg.norm(a2))

            x,y,z,R=frame.setFrameData(a1,a2,dictAnat["Right Foot"]['sequence'])


            csFrame.update(R,ptOrigin)
            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))

    # ----- least-square Segmental motion ------
    def _pelvis_motion_optimize(self,aqui, dictRef, motionMethod,anatomicalFrameMotionEnable=True):
        """
            Compute Motion of the anatomical coordinate system of the pelvis from rigid transformation with motion of the technical coordinate system.
            Least-square optimization can be used.

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
        """
        seg=self.getSegment("Pelvis")


        #  --- check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            btkTools.isPointsExist(aqui,seg.m_tracking_markers)

        # --- Motion of the Technical frame
        seg.getReferential("TF").motion =[]

        # part 1: get global location in Static
        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers:
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1

        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1

            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm=motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt


                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

        # --- HJC
        values_LHJCnode=seg.getReferential('TF').getNodeTrajectory("LHJC")
        values_RHJCnode=seg.getReferential('TF').getNodeTrajectory("RHJC")

        desc_L = seg.getReferential('TF').static.getNode_byLabel("LHJC").m_desc
        desc_R = seg.getReferential('TF').static.getNode_byLabel("RHJC").m_desc
        btkTools.smartAppendPoint(aqui,"LHJC",values_LHJCnode, desc=str("opt-"+desc_L))
        btkTools.smartAppendPoint(aqui,"RHJC",values_RHJCnode, desc=str("opt-"+desc_R))

        # --- midASIS
        values_midASISnode = seg.getReferential('TF').getNodeTrajectory("midASIS")
        btkTools.smartAppendPoint(aqui,"midASIS",values_midASISnode, desc="opt")

#        if anatomicalFrameMotionEnable:
#            # --- Motion of the Anatomical frame
#            seg.anatomicalFrame.motion=[]
#
#              # computation
#            for i in range(0,aqui.GetPointFrameNumber()):
#                ptOrigin=aqui.GetPoint(str(dictAnat["Pelvis"]['labels'][3])).GetValues()[i,:]
#                #R = np.dot(seg.getReferential("TF").motion[i].getRotation(),relativeSegTech )
#                R = np.dot(seg.getReferential("TF").motion[i].getRotation(), seg.getReferential("TF").relativeMatrixAnatomic)
#                frame=frame.Frame()
#                frame.update(R,ptOrigin)
#                seg.anatomicalFrame.addMotionFrame(frame)



    def _left_thigh_motion_optimize(self,aqui, dictRef, motionMethod):
        """
            Compute Motion of the anatomical coordinate system of the left thigh from rigid transformation with motion of the technical coordinate system.
            Least-square optimization can be used.

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system


        """
        seg=self.getSegment("Left Thigh")

        #  --- add LHJC if list <2 - check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            if len(seg.m_tracking_markers)==2:
                if "LHJC" not in seg.m_tracking_markers:
                    seg.m_tracking_markers.append("LHJC")
                    logging.debug("LHJC added to tracking marker list")

            btkTools.isPointsExist(aqui,seg.m_tracking_markers)


        # --- Motion of the Technical frame
        seg.getReferential("TF").motion =[]

        # part 1: get back static global position ( look out i use nodes)

        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers: # recupere les tracki
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1


        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1


            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm=motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt


                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

                seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

        # --- LKJC
        desc = seg.getReferential('TF').static.getNode_byLabel("LKJC").m_desc
        values_LKJCnode=seg.getReferential('TF').getNodeTrajectory("LKJC")
        btkTools.smartAppendPoint(aqui,"LKJC",values_LKJCnode, desc=str("opt-"+desc))

        # --- LHJC from Thigh
        #values_HJCnode=seg.getReferential('TF').getNodeTrajectory("LHJC")
        #btkTools.smartAppendPoint(aqui,"LHJC-Thigh",values_HJCnode, desc="opt from Thigh")

        # remove LHC from list of tracking markers
        if "LHJC" in seg.m_tracking_markers: seg.m_tracking_markers.remove("LHJC")




    def _right_thigh_motion_optimize(self,aqui, dictRef, motionMethod):
        """
            Compute Motion of the anatomical coordinate system of the right thigh from rigid transformation with motion of the technical coordinate system.
            Least-square optimization can be used.

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system

        """
        seg=self.getSegment("Right Thigh")


        #  --- add RHJC if list <2 - check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            if len(seg.m_tracking_markers)==2:
                if "RHJC" not in seg.m_tracking_markers:
                    seg.m_tracking_markers.append("RHJC")
                    logging.debug("RHJC added to tracking marker list")

        # --- Motion of the Technical frame
        seg.getReferential("TF").motion =[]

        # part 1: get back static global position ( look ou i use nodes)

        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers:
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1

        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1


            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm=motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt


                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

                seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

        # --- RKJC
        desc = seg.getReferential('TF').static.getNode_byLabel("RKJC").m_desc
        values_RKJCnode=seg.getReferential('TF').getNodeTrajectory("RKJC")
        btkTools.smartAppendPoint(aqui,"RKJC",values_RKJCnode, desc=str("opt-"+desc))

        # --- RHJC from Thigh
        #values_HJCnode=seg.getReferential('TF').getNodeTrajectory("RHJC")
        #btkTools.smartAppendPoint(aqui,"RHJC-Thigh",values_HJCnode, desc="opt from Thigh")

        # remove HJC from list of tracking markers
        if "RHJC" in seg.m_tracking_markers: seg.m_tracking_markers.remove("RHJC")

    def _left_shank_motion_optimize(self,aqui, dictRef,  motionMethod):
        """
            Compute Motion of the anatomical coordinate system of the left shank from rigid transformation with motion of the technical coordinate system.
            Least-square optimization can be used.

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system

        """
        seg=self.getSegment("Left Shank")

        #  --- add LKJC if list <2 - check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            if len(seg.m_tracking_markers)==2:
                if "LKJC" not in seg.m_tracking_markers:
                    seg.m_tracking_markers.append("LKJC")
                    logging.debug("LKJC added to tracking marker list")

        # --- Motion of the Technical frame
        seg.getReferential("TF").motion =[]

       # part 1: get back static global position ( look ou i use nodes)
        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers:
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1

        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1


            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm=motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt

                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

                seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

        # --- LAJC
        desc = seg.getReferential('TF').static.getNode_byLabel("LAJC").m_desc
        values_LAJCnode=seg.getReferential('TF').getNodeTrajectory("LAJC")
        btkTools.smartAppendPoint(aqui,"LAJC",values_LAJCnode, desc=str("opt"+desc))

        # --- KJC from Shank
        #values_KJCnode=seg.getReferential('TF').getNodeTrajectory("LKJC")
        #btkTools.smartAppendPoint(aqui,"LKJC-Shank",values_KJCnode, desc="opt from Shank")


        # remove KJC from list of tracking markers
        if "LKJC" in seg.m_tracking_markers: seg.m_tracking_markers.remove("LKJC")



    def _right_shank_motion_optimize(self,aqui, dictRef, motionMethod):
        """
            Compute Motion of the anatomical coordinate system of the right shank from rigid transformation with motion of the technical coordinate system.
            Least-square optimization can be used.

            :Parameters:
               - `aqui` (btkAcquisition) - acquisition instance of a dynamic trial
               - `dictRef` (dict) - dictionnary reporting markers and sequence use for building Technical coordinate system
               - `dictAnat` (dict) - dictionnary reporting markers and sequence use for building Anatomical coordinate system
               - `options` (dict) - dictionnary use to pass options

        """
        seg=self.getSegment("Right Shank")

        #  --- add RKJC if list <2 - check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            if len(seg.m_tracking_markers)==2:
                if "RKJC" not in seg.m_tracking_markers:
                    seg.m_tracking_markers.append("RKJC")
                    logging.debug("RKJC added to tracking marker list")

        # --- Motion of the Technical frame

        seg.getReferential("TF").motion =[]

        # part 1: get back static global position ( look ou i use nodes)

        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers:
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1

        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1


            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm=motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt


                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

                seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))

        # RAJC
        desc = seg.getReferential('TF').static.getNode_byLabel("RAJC").m_desc
        values_RAJCnode=seg.getReferential('TF').getNodeTrajectory("RAJC")
        btkTools.smartAppendPoint(aqui,"RAJC",values_RAJCnode, desc=str("opt-"+desc))

        # --- KJC from Shank
        #values_KJCnode=seg.getReferential('TF').getNodeTrajectory("RKJC")
        #btkTools.smartAppendPoint(aqui,"RKJC-Shank",values_KJCnode, desc="opt from Shank")

        # remove KJC from list of tracking markers
        if "RKJC" in seg.m_tracking_markers: seg.m_tracking_markers.remove("RKJC")

    def _leftFoot_motion_optimize(self,aqui, dictRef, motionMethod):

        seg=self.getSegment("Left Foot")

        #  --- add LAJC if marker list < 2  - check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            if len(seg.m_tracking_markers)==2:
                if "LAJC" not in seg.m_tracking_markers:
                    seg.m_tracking_markers.append("LAJC")
                    logging.debug("LAJC added to tracking marker list")

        # --- Motion of the Technical frame
        seg.getReferential("TF").motion =[]

        # part 1: get global location in Static
        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers:
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1

        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1

            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm= motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt


                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


        # --- AJC from Foot
        values_AJCnode=seg.getReferential('TF').getNodeTrajectory("LAJC")
        #btkTools.smartAppendPoint(aqui,"LAJC-Foot",values_AJCnode, desc="opt from Foot")


        # remove AJC from list of tracking markers
        if "LAJC" in seg.m_tracking_markers: seg.m_tracking_markers.remove("LAJC")


    def _rightFoot_motion_optimize(self,aqui, dictRef, motionMethod):

        seg=self.getSegment("Right Foot")

        #  --- add RAJC if marker list < 2  - check presence of tracking markers in the acquisition
        if seg.m_tracking_markers != []:
            if len(seg.m_tracking_markers)==2:
                if "RAJC" not in seg.m_tracking_markers:
                    seg.m_tracking_markers.append("RAJC")
                    logging.debug("RAJC added to tracking marker list")

        # --- Motion of the Technical frame
        seg.getReferential("TF").motion =[]

        # part 1: get global location in Static
        if seg.m_tracking_markers != []: # work with tracking markers
            staticPos = np.zeros((len(seg.m_tracking_markers),3))
            i=0
            for label in seg.m_tracking_markers:
                staticPos[i,:] = seg.getReferential("TF").static.getNode_byLabel(label).m_global
                i+=1

        # part 2 : get dynamic position ( look out i pick up value in the btkAcquisition)
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):

            if seg.m_tracking_markers != []: # work with traking markers
                dynPos = np.zeros((len(seg.m_tracking_markers),3)) # use
                k=0
                for label in seg.m_tracking_markers:
                    dynPos[k,:] = aqui.GetPoint(label).GetValues()[i,:]
                    k+=1

            if motionMethod == enums.motionMethod.Sodervisk :
                Ropt, Lopt, RMSE, Am, Bm= motion.segmentalLeastSquare(staticPos,
                                                              dynPos)
                R=np.dot(Ropt,seg.getReferential("TF").static.getRotation())
                tOri=np.dot(Ropt,seg.getReferential("TF").static.getTranslation())+Lopt


                csFrame.setRotation(R)
                csFrame.setTranslation(tOri)
                csFrame.m_axisX=R[:,0]
                csFrame.m_axisY=R[:,1]
                csFrame.m_axisZ=R[:,2]

            seg.getReferential("TF").addMotionFrame(copy.deepcopy(csFrame))


        # --- AJC from Foot
        values_AJCnode=seg.getReferential('TF').getNodeTrajectory("RAJC")
        #btkTools.smartAppendPoint(aqui,"RAJC-Foot",values_AJCnode, desc="opt from Foot")


        # remove AJC from list of tracking markers
        if "RAJC" in seg.m_tracking_markers: seg.m_tracking_markers.remove("RAJC")


    def _anatomical_motion(self,aqui,segmentLabel,originLabel=""):

        seg=self.getSegment(segmentLabel)

        # --- Motion of the Anatomical frame
        seg.anatomicalFrame.motion=[]

        # computation
        csFrame=frame.Frame()
        for i in range(0,aqui.GetPointFrameNumber()):
            ptOrigin=aqui.GetPoint(originLabel).GetValues()[i,:]
            R = np.dot(seg.getReferential("TF").motion[i].getRotation(), seg.getReferential("TF").relativeMatrixAnatomic)
            csFrame.update(R,ptOrigin)
            seg.anatomicalFrame.addMotionFrame(copy.deepcopy(csFrame))


    def _rotate_anatomical_motion(self,segmentLabel,angle,aqui,options=None):
        """
            rotate an anatomical frame along its long axis

            :Parameters:
               - `` () -


        """

        seg=self.getSegment(segmentLabel)


        angle = np.deg2rad(angle)

        # --- motion of both technical and anatomical referentials of the proximal shank

        #seg.anatomicalFrame.motion=[]

        # additional markers
        # NA

        # computation
        rotZ = np.eye(3,3)
        rotZ[0,0] = np.cos(angle)
        rotZ[0,1] = -np.sin(angle)
        rotZ[1,0] =  np.sin(angle)
        rotZ[1,1] = np.cos(angle)

        for i in range(0,aqui.GetPointFrameNumber()):

            ptOrigin=seg.anatomicalFrame.motion[i].getTranslation()

            R = np.dot(seg.anatomicalFrame.motion[i].getRotation(),rotZ)

            seg.anatomicalFrame.motion[i].update(R,ptOrigin)




    # ---- tools ----
    def _rotateAjc(self,ajc,kjc,ank, offset):
        """
            get AJC from abd/add rotation offset

            :Parameters:
               - `ajc` (numpy.array(1,3)) - global location of the ankle joint centre
               - `kjc` (numpy.array(1,3)) - global location of the knee joint centre
               - `ank` (numpy.array(1,3)) - global location of the lateral ankle marker
               - `offset` (double) - abd/add rotation offset

            :return:
                - final location of AJC after offset rotation
        """


        a1=(kjc-ajc)
        a1=np.divide(a1,np.linalg.norm(a1))

        v=(ank-ajc)
        v=np.divide(v,np.linalg.norm(v))

        a2=np.cross(a1,v)
        a2=np.divide(a2,np.linalg.norm(a2))

        x,y,z,R=frame.setFrameData(a1,a2,"ZXY")
        csFrame=frame.Frame()

        csFrame.m_axisX=x
        csFrame.m_axisY=y
        csFrame.m_axisZ=z
        csFrame.setRotation(R)
        csFrame.setTranslation(ank)

        loc=np.dot(R.T,ajc-ank)

        abAdangle = np.deg2rad(offset)

        rotAbdAdd = np.array([[1, 0, 0],[0, np.cos(abAdangle), -1.0*np.sin(abAdangle)], [0, np.sin(abAdangle), np.cos(abAdangle) ]])

        finalRot= np.dot(R,rotAbdAdd)

        return  np.dot(finalRot,loc)+ank


    # --- opensim --------
    def opensimTrackingMarkers(self):


        out={}
        for segIt in self.m_segmentCollection:
            if "Proximal" not in segIt.name:
                out[segIt.name] = segIt.m_tracking_markers

        return out



    def opensimGeometry(self):
        """
        TODO require : joint name from opensim -> find alternative

        rather a class method than a method instance
        """

        out={}
        out["hip_r"]= {"joint label":"RHJC", "proximal segment label":"Pelvis", "distal segment label":"Right Thigh" }
        out["knee_r"]= {"joint label":"RKJC", "proximal segment label":"Right Thigh", "distal segment label":"Right Shank" }
        out["ankle_r"]= {"joint label":"RAJC", "proximal segment label":"Right Shank", "distal segment label":"Right Foot" }
        #out["mtp_r"]=


        out["hip_l"]= {"joint label":"LHJC", "proximal segment label":"Pelvis", "distal segment label":"Left Thigh" }
        out["knee_l"]= {"joint label":"LKJC", "proximal segment label":"Left Thigh", "distal segment label":"Left Shank" }
        out["ankle_l"]= {"joint label":"LAJC", "proximal segment label":"Left Shank", "distal segment label":"Left Foot" }
        #out["mtp_l"]=

        return out

    def opensimIkTask(self,expert=False):
        out={}

        if expert:

            out={"LASI":0,
                 "LASI_posAnt":100,
                 "LASI_medLat":100,
                 "LASI_supInf":100,
                 "RASI":0,
                 "RASI_posAnt":100,
                 "RASI_medLat":100,
                 "RASI_supInf":100,
                 "LPSI":0,
                 "LPSI_posAnt":100,
                 "LPSI_medLat":100,
                 "LPSI_supInf":100,
                 "RPSI":0,
                 "RPSI_posAnt":100,
                 "RPSI_medLat":100,
                 "RPSI_supInf":100,

                 "RTHI":0,
                 "RTHI_posAnt":100,
                 "RTHI_medLat":100,
                 "RTHI_proDis":100,
                 "RKNE":0,
                 "RKNE_posAnt":100,
                 "RKNE_medLat":100,
                 "RKNE_proDis":100,
                 "RTIB":0,
                 "RTIB_posAnt":100,
                 "RTIB_medLat":100,
                 "RTIB_proDis":100,
                 "RANK":0,
                 "RANK_posAnt":100,
                 "RANK_medLat":100,
                 "RANK_proDis":100,
                 "RHEE":0,
                 "RHEE_supInf":100,
                 "RHEE_medLat":100,
                 "RHEE_proDis":100,
                 "RTOE":0,
                 "RTOE_supInf":100,
                 "RTOE_medLat":100,
                 "RTOE_proDis":100,

                 "LTHI":0,
                 "LTHI_posAnt":100,
                 "LTHI_medLat":100,
                 "LTHI_proDis":100,
                 "LKNE":0,
                 "LKNE_posAnt":100,
                 "LKNE_medLat":100,
                 "LKNE_proDis":100,
                 "LTIB":0,
                 "LTIB_posAnt":100,
                 "LTIB_medLat":100,
                 "LTIB_proDis":100,
                 "LANK":0,
                 "LANK_posAnt":100,
                 "LANK_medLat":100,
                 "LANK_proDis":100,
                 "LHEE":0,
                 "LHEE_supInf":100,
                 "LHEE_medLat":100,
                 "LHEE_proDis":100,
                 "LTOE":0,
                 "LTOE_supInf":100,
                 "LTOE_medLat":100,
                 "LTOE_proDis":100,
                 }

        else:
            out={"LASI":100,
                 "RASI":100,
                 "LPSI":100,
                 "RPSI":100,
                 "RTHI":100,
                 "RKNE":100,
                 "RTIB":100,
                 "RANK":100,
                 "RHEE":100,
                 "RTOE":100,
                 "LTHI":100,
                 "LKNE":100,
                 "LTIB":100,
                 "LANK":100,
                 "LHEE":100,
                 "LTOE":100,
                 }

        return out



    # ----- vicon API -------
    def viconExport(self,NEXUS,acq,vskName,pointSuffix,staticProcessingFlag):
        """
            method exporting model outputs to Nexus UI

            This method exports :

                - joint centres as modelled-marker
                - angles
                - moment
                - force
                - power
                - bones


            :Parameters:
                - `NEXUS` () - Nexus environment
                - `vskName` (str) - name of the subject created in Nexus
                - `staticProcessingFlag` (bool`) : flag indicating only static model ouput will be export

        """


        if staticProcessingFlag:
            if self.checkCalibrationProperty("LeftKAD",True):
                nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"LKNE", acq)
            if self.checkCalibrationProperty("RightKAD",True):
                nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"RKNE", acq)

        # export JC
        nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"LHJC", acq)
        nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"RHJC", acq)
        nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"LKJC", acq)
        nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"RKJC", acq)
        nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"LAJC", acq)
        nexusTools.appendModelledMarkerFromAcq(NEXUS,vskName,"RAJC", acq)
        logging.debug("jc over")

        # export angles
        for it in btk.Iterate(acq.GetPoints()):
            if it.GetType() == btk.btkPoint.Angle:
                if pointSuffix!="":
                    if pointSuffix in it.GetLabel():
                        nexusTools.appendAngleFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
                else:
                    nexusTools.appendAngleFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)

        logging.debug("angles over")

        # bones
        # -------------
        nexusTools.appendBones(NEXUS,vskName,acq,"PEL", self.getSegment("Pelvis"),OriginValues = acq.GetPoint("midHJC").GetValues() )

        nexusTools.appendBones(NEXUS,vskName,acq,"LFE", self.getSegment("Left Thigh"),OriginValues = acq.GetPoint("LKJC").GetValues() )
        #nexusTools.appendBones(NEXUS,vskName,"LFEP", self.getSegment("Left Shank Proximal"),OriginValues = acq.GetPoint("LKJC").GetValues(),manualScale = 100 )
        nexusTools.appendBones(NEXUS,vskName,acq,"LTI", self.getSegment("Left Shank"),OriginValues = acq.GetPoint("LAJC").GetValues() )
        nexusTools.appendBones(NEXUS,vskName,acq,"LFO", self.getSegment("Left Foot"), OriginValues = self.getSegment("Left Foot").anatomicalFrame.getNodeTrajectory("FootOriginOffset") )
        nexusTools.appendBones(NEXUS,vskName,acq,"LTO", self.getSegment("Left Foot"), OriginValues = self.getSegment("Left Foot").anatomicalFrame.getNodeTrajectory("ToeOrigin"),  manualScale = self.getSegment("Left Foot").m_bsp["length"]/3.0 )

        nexusTools.appendBones(NEXUS,vskName,acq,"RFE", self.getSegment("Right Thigh"),OriginValues = acq.GetPoint("RKJC").GetValues() )
        #nexusTools.appendBones(NEXUS,vskName,"RFEP", self.getSegment("Right Shank Proximal"),OriginValues = acq.GetPoint("RKJC").GetValues(),manualScale = 100 )
        nexusTools.appendBones(NEXUS,vskName,acq,"RTI", self.getSegment("Right Shank"),OriginValues = acq.GetPoint("RAJC").GetValues() )
        nexusTools.appendBones(NEXUS,vskName,acq,"RFO", self.getSegment("Right Foot") , OriginValues = self.getSegment("Right Foot").anatomicalFrame.getNodeTrajectory("FootOriginOffset") )
        nexusTools.appendBones(NEXUS,vskName,acq,"RTO", self.getSegment("Right Foot") ,  OriginValues = self.getSegment("Right Foot").anatomicalFrame.getNodeTrajectory("ToeOrigin"), manualScale = self.getSegment("Right Foot").m_bsp["length"]/3.0)

        logging.debug("bones over")

        if not staticProcessingFlag:
            # export Force
            for it in btk.Iterate(acq.GetPoints()):
                if it.GetType() == btk.btkPoint.Force:
                    if pointSuffix!="":
                        if pointSuffix in it.GetLabel():
                            nexusTools.appendForceFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
                    else:
                        nexusTools.appendForceFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
            logging.debug("force over")

            # export Moment
            for it in btk.Iterate(acq.GetPoints()):
                if it.GetType() == btk.btkPoint.Moment:
                    if pointSuffix!="":
                        if pointSuffix in it.GetLabel():
                            nexusTools.appendMomentFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
                    else:
                        nexusTools.appendMomentFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
            logging.debug("Moment over")

            # export Moment
            for it in btk.Iterate(acq.GetPoints()):
                if it.GetType() == btk.btkPoint.Power:
                    if pointSuffix!="":
                        if pointSuffix in it.GetLabel():
                            nexusTools.appendPowerFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
                    else:
                        nexusTools.appendPowerFromAcq(NEXUS,vskName,str(it.GetLabel()), acq)
            logging.debug("power over")
