import arcpy
import os
from arcpy import env
from arcpy.sa import *

env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

filled_flow=arcpy.GetParameterAsText(0)
FlowAccum=arcpy.GetParameterAsText(1)
flow_x=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)

##FlowAccum=os.path.join(env.workspace,naming+"_"+flow_x+"_"+"Flow_Accumulation")
con=os.path.join(env.workspace,naming+"_"+flow_x+"_"+"Reclassed_FlowAccum")
Reclass=os.path.join(env.workspace,naming+"_"+flow_x+"_"+"streams_as_raster")
Streams=os.path.join(env.workspace,naming+"_"+flow_x+"_"+"Streams_Lines_NoSmooth")
Streams_final=os.path.join(env.workspace,naming+"_"+flow_x+"_"+"stream_lines")

#Raster Calculator
arcpy.AddMessage("Using Raster Calculator (Step 1 of 3)")
ConRaster=Con(FlowAccum,1,0,"value>"+str(flow_x))
ConRaster.save(os.path.join(env.workspace,naming+"_"+flow_x+"_"+"Con"))

#Reclassify
arcpy.AddMessage("Reclassifying Raster (Step 2 of 3)")         
arcpy.gp.Reclassify_sa(ConRaster, "VALUE", "0 NODATA;1 1", Reclass, "DATA")

#Raster to Polyline to create streams
arcpy.AddMessage("Converting Raster to Polyline (Step 3 of 3)")
StreamToFeature(Reclass, filled_flow, Streams,"NO_SIMPLIFY")

try:
    import arcpy.cartography as CA
    CA.SmoothLine(Streams, Streams_final, "PAEK", "15")

except:
    StreamToFeature(Reclass, filled_flow, Streams_final,"NO_SIMPLIFY")
    

##arcpy.Delete_management(FlowAccum)
arcpy.Delete_management(ConRaster)
arcpy.Delete_management(Streams)
arcpy.Delete_management(con)
