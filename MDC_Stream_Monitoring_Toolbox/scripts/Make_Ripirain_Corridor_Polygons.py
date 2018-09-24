import arcpy
import os
from arcpy import env

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)

bankfull_polies= arcpy.GetParameterAsText(0)
env.workspace=arcpy.GetParameterAsText(1)
naming=arcpy.GetParameterAsText(2)

rip_corridor=os.path.join(env.workspace,naming+"_riparian_corridors")

#buffer bankfull
arcpy.Buffer_analysis(bankfull_polies, rip_corridor, "30 Meters","FULL","","ALL")

