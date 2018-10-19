import arcpy
import os
from arcpy import env

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)

bankfull_polies=arcpy.GetParameterAsText(0)
active_channel=arcpy.GetParameterAsText(1)
buffer_value= arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)

rip_corridor=os.path.join(env.workspace,naming+"_riparian_corridors")

#buffer bankfull
arcpy.Buffer_analysis(bankfull_polies, rip_corridor, buffer_value,"FULL","","ALL")

#create another verison of the ripirain cooridor that does not include area within active channel polygons
clipped_corridor=os.path.join(env.workspace,naming+"_rip_corridors_no_AC")
arcpy.Erase_analysis(rip_corridor, active_channel, clipped_corridor)

