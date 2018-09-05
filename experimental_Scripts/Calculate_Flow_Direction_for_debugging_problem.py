import arcpy
import os
from arcpy import env
from arcpy.sa import *

env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#get parameters
originalDEM=arcpy.GetParameterAsText(0)
env.workspace=arcpy.GetParameterAsText(1)
naming=arcpy.GetParameterAsText(2)

Fill_with_Z=os.path.join(env.workspace,naming+"_"+"Depressionless_DEM")
Filled_Flow=os.path.join(env.workspace,naming+"_"+"_Flow_Direction")
drop_raster = os.path.join(env.workspace,naming+"_"+"Drop_Raster_from_Filled_Flow_Direction")
##DEM5m=os.path.join(env.workspace,naming+"_"+"DEM_Resampled")

#Check resolution of dem
arcpy.AddMessage("Checking resolution of raster (Step 1 of 10)")
demrez = arcpy.GetRasterProperties_management(originalDEM, "CELLSIZEX")
demres = demrez.getOutput(0)

error=Exception("ERROR:Input DEM resolution is greater than 5 5")
#if resolution is less than 1 meter, resample it to 1 meter

if float(demres)<5:
        DEM5m=os.path.join(env.workspace,naming+"_fivem_DEM")
        arcpy.Resample_management(originalDEM, DEM5m, "5 5", "BILINEAR")
        resampledflag=1
        
else:
        DEM5m=originalDEM
        resampledflag=0

#calculate Flow Direction 
arcpy.AddMessage("Calculating Flow Direction (Step 2 of 10)")
Flowdir=FlowDirection(DEM5m,"NORMAL")
Flowdir.save(os.path.join(env.workspace,naming+"_"+"Flow_Direction"))

#calculate Sink
arcpy.AddMessage("Calculating Sink (Step 3 of 10)")
outsink=Sink(Flowdir)
outsink.save(os.path.join(env.workspace,naming+"_"+"Sink"))

#calculate Watershed
arcpy.AddMessage("Calculating Watershed (Step 4 of 10)")
outwatershed=Watershed(Flowdir, outsink,"Value")
outwatershed.save(os.path.join(env.workspace,naming+"_"+"Watershed"))

arcpy.AddMessage("Building Attribute Table (Step 5 of 10)")
arcpy.BuildRasterAttributeTable_management(outwatershed, "Overwrite")

#calculate sink min
arcpy.AddMessage("Calculating Sink Min (Step 6 of 10)")
sink_min=ZonalStatistics(outwatershed,"Value",DEM5m,"MINIMUM", "DATA")
sink_min.save(os.path.join(env.workspace,naming+"_"+"Sink_Min"))

#calculate sink max
arcpy.AddMessage("Calculating Zonal Fill (Step 7 of 10)")
sink_max=ZonalFill(outwatershed, DEM5m)
sink_max.save(os.path.join(env.workspace,naming+"_"+"Sink_Max"))

#subtract sink min from sink max to get sink depth
arcpy.AddMessage("Calculating Sink Depth (Step 8 of 10)")
sinkDepth=Minus(sink_max,sink_min)
sinkDepth.save(os.path.join(env.workspace,naming+"_"+"Sink_Depth"))

z_limit=arcpy.GetRasterProperties_management(sinkDepth,"MAXIMUM")
##arcpy.AddMessage("The z_limit is {0}".format(z_limit))

#Fill
arcpy.AddMessage("Calculating Fill (Step 9 of 10)")
arcpy.gp.Fill_sa(DEM5m,Fill_with_Z, z_limit)

#Flow Direction
arcpy.AddMessage("Calculating Flow Direction (Step 10 of 10)")
arcpy.gp.FlowDirection_sa(Fill_with_Z,Filled_Flow,"NORMAL",drop_raster)

#delete the resampled DEM if it was created
if (resampledflag==1):
        arcpy.Delete_management(DEM5m)

arcpy.Delete_management(Flowdir)
arcpy.Delete_management(sink_max)
arcpy.Delete_management(sink_min)
arcpy.Delete_management(outwatershed)
arcpy.Delete_management(outsink)
arcpy.Delete_management(sinkDepth)
arcpy.Delete_management(drop_raster)
