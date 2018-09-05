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
dem=arcpy.GetParameterAsText(0)
polyline=arcpy.GetParameterAsText(1)
AC_polys=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)

def convert_list(listt):
        #remove blanks from export list
        listt=[x for x in listt if x != [[]]]
        string=str(listt)
        almost=string.replace("[","")
        there=almost.replace("]","")
        fixed="("+there+")"

        return fixed

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

userdistance=0.5

####Phase 1#############################################################################
#Phase 1 involves taking all input streamlines and placing a point every userdistance apart on the lines
##arcpy.SelectLayerByAttribute_management(polyline, "NEW_SELECTION","Stream_Order > 1")

#copy input streamlines into memory to imporve processing time
mem_lines=copy_features(polyline,r"in_memory/lines","")

#create point featureclass. save into memory to improve processing time
mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

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
arcpy.Buffer_analysis(large_streams, largebuffers, "50 Meters")

buffers=os.path.join(env.workspace,naming+"buffer")
arcpy.Merge_management([smallbuffers, largebuffers], buffers)

#mask the dem to point buffers so there are way less points to deal with
arcpy.AddMessage("\t\tMasking DEM...")
masked = ExtractByMask(dem, buffers)
masked.save(os.path.join(env.workspace,naming+"_maskedraster"))

arcpy.AddMessage("\t\tConverting mask to points...")
dem_points=os.path.join(env.workspace,naming+"_dempoints")
arcpy.RasterToPoint_conversion(masked, dem_points, "Value")

#now find the minimum elevation value in each buffer zone
arcpy.AddMessage("\t\tCalculating Zonal Statistics for Mask...")
outZonalStats = ZonalStatistics(buffers, "OBJECTID", masked,"MINIMUM","DATA")
outZonalStats.save(os.path.join(env.workspace,naming+"_min_by_zones"))

#now convert the buffers to rasters by object id so we can load them into points
arcpy.AddMessage("\t\tConverting buffers into raster...")
bufferraster=os.path.join(env.workspace,naming+"_bufferraster")
arcpy.PolygonToRaster_conversion(buffers, "OBJECTID", bufferraster, "#", "#", 1)

#now convert the buffers to rasters by Line_OID so we can load them into points
arcpy.AddMessage("\t\tConverting buffers into raster...")
line_raster=os.path.join(env.workspace,naming+"_line_raster")
arcpy.PolygonToRaster_conversion(buffers, "LineOID", line_raster, "#", "#", 1)

#extract necessary data from raster to buffer points
inRasterlist=[[bufferraster],[line_raster],[outZonalStats]]
arcpy.AddMessage("\t\tExtracting values to points...")
ExtractMultiValuesToPoints(dem_points,inRasterlist,"NONE")

#build thwag network through sql query
thwag_network_lyr=arcpy.MakeFeatureLayer_management(dem_points,"thwag_net_lyr","grid_code= "+naming+"_min_by_zones")
thwag_network=os.path.join(env.workspace,naming+"thwag_network")
arcpy.CopyFeatures_management(thwag_network_lyr,thwag_network)


#######################################################################################################################

#make pgdb version for easy distinct query (this cannot be done in gdb)
pgdb=arcpy.CreatePersonalGDB_management("Q:/", "dummy.mdb")
##env.workspace=pgdb
##thwag_network_pgdb=os.path.join(pgdb,naming+"thwag_network")
arcpy.CopyFeatures_management(thwag_network_lyr,"Q:/dummy.mdb/thwag_network")
pgdb_points="Q:/dummy.mdb/thwag_network"

#select points that are from buffers where more then 1 point was selected due to
#more than one point possessing the minimum elevation
distinct_query="[oneline_halfm_test2_bufferraster] IN \
(SELECT [oneline_halfm_test2_bufferraster] \
FROM thwag_network \
GROUP BY [oneline_halfm_test2_bufferraster] HAVING \
Count( [oneline_halfm_test2_bufferraster] )>1)"
duplicates_lyr=arcpy.MakeFeatureLayer_management(pgdb_points,"duplicates.lyr", distinct_query)
duplicates=os.path.join(env.workspace,naming+"_duplicates")
arcpy.CopyFeatures_management(duplicates_lyr,duplicates)

duplicates_sorted=os.path.join(env.workspace,naming+"_duplicates_sorted")
arcpy.Sort_management(duplicates, duplicates_sorted, [["oneline_halfm_test2_bufferraster"]])

points_to_delete=[]
value=0
value2=-99
search_fields=["OID@","oneline_halfm_test2_bufferraster","pointid"]

with arcpy.da.SearchCursor(duplicates_sorted, (search_fields)) as search:
        for row in search:
                
##                arcpy.AddMessage("value is "+str(value))
##                arcpy.AddMessage("value2 is "+str(value2))

                arcpy.AddMessage("row is "+str(row[1]))
                #this makes it so that each buffer raster value is only done once
                if value!=row[1]:
                        arcpy.AddMessage("value is "+str(value))
                        arcpy.AddMessage("value2 is "+str(value2))


##                        if value2==value:
##                                arcpy.AddMessage("deleted a "+str(value2))
##                                points_to_delete.append(value2_pointid)

                        
                                
                        value=row[1]


                else:
                        arcpy.AddMessage("deleted a "+str(row[1]))
                        points_to_delete.append(row[2])
                        

##                        if value2==value:
##                                arcpy.AddMessage("deleted a "+str(value2))
##                                points_to_delete.append(value2_pointid)



points_to_delete=convert_list(points_to_delete)

points_wo_dups_lyr=arcpy.MakeFeatureLayer_management(thwag_network_lyr,"remove_nondups.lyr","pointid NOT IN "+points_to_delete)

points_wo_dups=os.path.join(env.workspace,naming+"points_wo_dups")
#run near analysis for sort order of thwag network
arcpy.Near_analysis(points_wo_dups_lyr,polyline)
arcpy.CopyFeatures_management(points_wo_dups_lyr,points_wo_dups)

############################################################################################################################################

#convert to thwag lines
thwag_lines=os.path.join(env.workspace,naming+"thwag_lines")
arcpy.PointsToLine_management(points_wo_dups_lyr, thwag_lines, "NEAR_FID", naming+"_bufferraster")

#maske buffer mask to the AC_polys
##arcpy.AddMessage("\t\tMasking DEM to AC_Polys...")
##masked_AC = ExtractByMask(outZonalStats, AC_polys)
##masked_AC.save(os.path.join(env.workspace,naming+"_masked_to_AC"))

##arcpy.Delete_management(mem_point)
##
##arcpy.Delete_management(layer)

###now add all the raster data created to the points for analysis
##inRasterlist=[[bufferraster],[outZonalStats],[streamorderraster]]
##arcpy.AddMessage("\t\tExtracting values to points...")
##
##ExtractMultiValuesToPoints(dem_points,inRasterlist,"NONE")
##
##copy_features(dem_points,env.workspace,naming+"_dempoints_wattr")
##
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
