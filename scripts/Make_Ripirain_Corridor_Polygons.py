import arcpy
import os
from arcpy import env

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)

bankfull_polies=arcpy.GetParameterAsText(0)
active_channel=arcpy.GetParameterAsText(1)
buffer_value=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)

#sometimes when running buffer tool depending on input we get error 99999 geometery error
#first we try buffering the easy way
try:
    #buffer bankfull
    rip_corridor=os.path.join(env.workspace,naming+"_riparian_corridors")
    arcpy.Buffer_analysis(bankfull_polies, rip_corridor, buffer_value+" Meters","FULL","","ALL")
    firstbuffer=True

#if we get the error, we have to buffer the harder way
except:
    #buffer bankfull
    rip_corridor=os.path.join(env.workspace,naming+"_part1")
    arcpy.Buffer_analysis(bankfull_polies, rip_corridor, buffer_value+" Meters", "FULL", "ROUND", "NONE", "", "PLANAR")
    firstbuffer=False

#if buffering was done easy way..
if firstbuffer==True:
    #create another verison of the ripirain cooridor that does not include area within active channel polygons
    clipped_corridor=os.path.join(env.workspace,naming+"_rip_corridors_no_AC")
    arcpy.Erase_analysis(rip_corridor, active_channel, clipped_corridor)

#if buffering was done hard way...
else:
    dissolved_rip=os.path.join(env.workspace,naming+"_riparian_corridors")
    arcpy.Dissolve_management(rip_corridor,dissolved_rip)

    #create another verison of the ripirain cooridor that does not include area within active channel polygons
    clipped_corridor=os.path.join(env.workspace,naming+"_rip_corridors_no_AC")
    arcpy.Erase_analysis(dissolved_rip, active_channel, clipped_corridor)

    arcpy.Delete_management(rip_corridor)
