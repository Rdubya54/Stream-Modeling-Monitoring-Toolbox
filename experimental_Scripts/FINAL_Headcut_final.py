import arcpy
import os
import string
from arcpy import env
from arcpy.sa import *

env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#get parameters
polyline=arcpy.GetParameterAsText(0)
dem=arcpy.GetParameterAsText(1)
env.workspace=arcpy.GetParameterAsText(2)
naming=arcpy.GetParameterAsText(3)

#this function is for copying features either into a gdb or into memory to spend up the processing time
def copy_features(features,workspace,copy_name):

        #if copying into memory
        if copy_name=="":
                copy_address=workspace

        #if copying into a geodatabase
        else:
                copy_address=os.path.join(workspace,copy_name)

        #arcpy copy features can be very picky and fail for weird reasons
        #if it throws an error, let the user know so that they can try solving it without having
        #to contact developer. Sometimes the copy is also unnesccary, so the code will attempt to
        #finish without having successfully copied
        try:
                arcpy.CopyFeatures_management(features,copy_address)

        except:
                arcpy.AddMessage("Failed to copy "+str(copy_address)+".")
                arcpy.AddMessage("This error usually occurs due to the Output gdb being open in ArcCatalog or another user having the gdb open.")
                arcpy.AddMessage("Be sure the output GDB is not open and no one else is using it.")
                arcpy.AddMessage("You can also try closing and reopening ArcMap.")
                arcpy.AddMessage("Tool may still be able to finish running, if not it will crash soon due to this error")

        return copy_address


####Phase 1#############################################################################
#Phase 1 involves taking all input streamlines and placing a point every userdistance apart on the lines
##arcpy.SelectLayerByAttribute_management(polyline, "NEW_SELECTION","Stream_Order > 1")

userdistance=0.5

#copy input streamlines into memory to imporve processing time
mem_lines=copy_features(polyline,r"in_memory/lines","")

#create point featureclass. save into memory to improve processing time
mem_point = arcpy.CreateFeatureclass_management(env.workspace, "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

#add necessary fields to the point feature class
arcpy.AddField_management(mem_point, "LineOID", "LONG")
arcpy.AddField_management(mem_point, "Value", "FLOAT")
arcpy.AddField_management(mem_point, "Stream_Order", "FLOAT")

search_fields = ["SHAPE@", "OID@","Stream_Order"]
insert_fields = ["SHAPE@", "LineOID", "Value","Stream_Order"]

arcpy.AddMessage("Setting up the data for processing....")
arcpy.AddMessage("\t\tDrawing points...")

#using cursor combo below/draw points on each streamline
with arcpy.da.SearchCursor(mem_lines, (search_fields)) as search:
    with arcpy.da.InsertCursor(mem_point, (insert_fields)) as insert:
        for row in search:
            
                #line geom is shape in search fields
                #use it to get length of line
                line_geom = row[0]
                length = float(line_geom.length)
                distance = 0
                
                #oid is OID@ in search fields
                #insert value into point field
                oid = str(row[1])

                #stream order is stream order in search fields
                #insert value into point field
                streamorder=row[2]

                #creates a point at the start and end of line for final point that is less then the userdistance away
                start_of_line = arcpy.PointGeometry(line_geom.firstPoint)
                end_of_line = arcpy.PointGeometry(line_geom.lastPoint)

                #returns a point on the line at a specific distance from the beginning
                point = line_geom.positionAlongLine(distance, False)
                
                #insert point at every userdistance
                while distance <= length:
                    point = line_geom.positionAlongLine(distance, False)

                    #insert rows for each point
                    insert.insertRow((point, oid, float(distance),streamorder))
                    distance += float(userdistance)
                   
                insert.insertRow((end_of_line, oid, length,streamorder))
del search
del insert

#copy output points drawn on line into output gdb
perm_pointz=copy_features(mem_point,env.workspace,naming+"_"+"points")

#delete points/lines in memory. They are now saved permenatently
arcpy.DeleteFeatures_management(mem_point)
arcpy.DeleteFeatures_management(mem_lines)

#now that there you have stream points
#place buffer around each one
arcpy.AddMessage("\t\tBuffering points...")

smallbuffers=os.path.join(env.workspace,naming+"_smallbuffers")
small_streams=arcpy.MakeFeatureLayer_management(perm_pointz,"small_points","Stream_Order <=2")
arcpy.Buffer_analysis(small_streams, smallbuffers, "25 Meters")

largebuffers=os.path.join(env.workspace,naming+"_largebuffers")
large_streams=arcpy.MakeFeatureLayer_management(perm_pointz,"large_points","Stream_Order >2")
arcpy.Buffer_analysis(large_streams, largebuffers, "25 Meters")

buffers=os.path.join(env.workspace,naming+"buffer")
arcpy.Merge_management([smallbuffers, largebuffers], buffers)

#mask the dem to point buffers so there are way less points to deal with
arcpy.AddMessage("\t\tMasking DEM...")
masked = ExtractByMask(dem, buffers)
masked.save(os.path.join(env.workspace,naming+"_maskedraster"))

#now find the minimum elevation value in each buffer zone
arcpy.AddMessage("\t\tCalculating Zonal Statistics for Mask...")
outZonalStats = ZonalStatistics(buffers, "OBJECTID", masked,"MINIMUM","DATA")
outZonalStats.save(os.path.join(env.workspace,naming+"_min_by_zones"))

###################################################PHASE 2#############################################333

spatial_ref = arcpy.Describe(polyline).spatialReference
output_points=os.path.join(env.workspace,naming+"_"+"output_points")

arcpy.AddMessage("\t\tExtracting elevation to points..")
ExtractMultiValuesToPoints(mem_point, [[outZonalStats, "Min_Elevation"]])

##arcpy.Delete_management(inputDEM)

# calculate elevation change

arcpy.AddField_management(mem_point,"Ev_Change","FLOAT")

feilds=["Min_Elevation","LINEOID","Ev_Change","OID@"]

elev1=0
line_OID=1

arcpy.AddMessage("\t\tCalculating Elevation Change...")
with arcpy.da.UpdateCursor(mem_point,feilds) as update:
        
        for row in update:

##                arcpy.AddMessage("doing line "+str(line_OID))
                #if its the first point in ever
                if(row[3]==1):

                        if row[0]==None:
                                elev1=None
                                

                        else:
                                elev1=float(row[0])
                                row[2]=float(0)
                                
                        
                elif(line_OID==row[1]):

                        if row[0]==None:
                                row[2]=None
                                
                                
                        else:
                                try:
                                        elev2 = float(row[0])

                                except:
                                        elev2=None

                                try:       
                                        row[2]=(elev1-elev2)

                                except:
                                        row[2]=None

                        try:
                                elev1=elev2

                        except:
                                elev1=None
                        
                        OID=row[1]
                        
                        update.updateRow(row)

                else:
                        row[2]=0
                        line_OID=row[1]

                        if row[0]==None:
                                elev1=None

                        else:
                                elev1=float(row[0])
        
arcpy.CopyFeatures_management(mem_point,output_points)

#make mem_points a layer so select by attibutes can be done

layer=arcpy.MakeFeatureLayer_management(mem_point,"output_points.lyr")

##arcpy.Delete_management(bufferraster)
##arcpy.Delete_management(streamorderraster)
##arcpy.Delete_management(masked)
####arcpy.Delete_management(dem_pointz)
##arcpy.Delete_management(dem_points)
##arcpy.Delete_management(outZonalStats)
##arcpy.Delete_management(mem_lines)
##arcpy.Delete_management(perm_pointz)
##arcpy.Delete_management(smallbuffers)
##arcpy.Delete_management(largebuffers)
##arcpy.Delete_management(buffers)
