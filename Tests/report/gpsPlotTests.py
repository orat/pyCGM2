# -*- coding: utf-8 -*-
import logging

import matplotlib.pyplot as plt
import numpy as np

# pyCGM2 settings
import pyCGM2

from pyCGM2.Processing.highLevel import standardSmartFunctions,gaitSmartFunctions
from pyCGM2 import enums
from pyCGM2.Processing import c3dManager,scores
from pyCGM2.Model.CGM2 import  cgm,cgm2

from pyCGM2.Report import plot,plotFilters,plotViewers,normativeDatasets
from pyCGM2.Tools import trialTools
from pyCGM2.Report import plot


class gpsPlotTest():

    @classmethod
    def singleAnalysis(cls):

        # ----DATA-----
        DATA_PATH = pyCGM2.TEST_DATA_PATH+"operations\\plot\\gaitPlot\\"
        modelledFilenames = ["gait Trial 03 - viconName.c3d"]


        #---- c3d manager
        #--------------------------------------------------------------------------
        c3dmanagerProcedure = c3dManager.UniqueC3dSetProcedure(DATA_PATH,modelledFilenames)
        cmf = c3dManager.C3dManagerFilter(c3dmanagerProcedure)
        cmf.enableEmg(False)
        trialManager = cmf.generate()

        #---- Analysis
        #--------------------------------------------------------------------------

        modelInfo=None
        subjectInfo=None
        experimentalInfo=None

        analysis = gaitSmartFunctions.make_analysis(trialManager,
                                                cgm.CGM1LowerLimbs.ANALYSIS_KINEMATIC_LABELS_DICT,
                                                cgm.CGM1LowerLimbs.ANALYSIS_KINETIC_LABELS_DICT,
                                    modelInfo,subjectInfo,experimentalInfo)


        ndp = normativeDatasets.Schwartz2008("Free")
        gps =scores.CGM1_GPS()
        scf = scores.ScoreFilter(gps,analysis, ndp)
        scf.compute()

        # viewer
        kv = plotViewers.GpsMapPlotViewer(analysis)

        # filter
        pf = plotFilters.PlottingFilter()
        pf.setViewer(kv)
        pf.setPath(DATA_PATH)
        pf.setPdfName(str("map"))
        pf.plot()

        plt.show()

if __name__ == "__main__":

    plt.close("all")

    gpsPlotTest.singleAnalysis()
