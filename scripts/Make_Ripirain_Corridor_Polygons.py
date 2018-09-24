import arcpy
import os
from arcpy import env

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)

bankfull_polies= arcpy.GetParameterAsText(0)
buffer_value= arcpy.GetParameterAsText(1)
env.workspace=arcpy.GetParameterAsText(2)
naming=arcpy.GetParameterAsText(3)

rip_corridor=os.path.join(env.workspace,naming+"_riparian_corridors")

#buffer bankfull
arcpy.Buffer_analysis(bankfull_polies, rip_corridor, buffer_value,"FULL","","ALL")

