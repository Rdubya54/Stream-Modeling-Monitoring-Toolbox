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

userdistance=2.5

####Phase 1#############################################################################
#Phase 1 involves taking all input streamlines and placing a point every userdistance apart on the lines
##arcpy.SelectLayerByAttribute_management(polyline, "NEW_SELECTION","Stream_Order > 1")

#copy input streamlines into memory to imporve processing time
mem_lines=copy_features(polyline,r"in_memory/lines","")

#create point featureclass. save into memory to improve processing time
mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

#add necessary fields to the point feature class
arcpy.AddField_management(mem_point, "LineOID", "LONG")
arcpy.AddField_management(mem_point, "Segment_Distance", "FLOAT")
arcpy.AddField_management(mem_point, "Type", "STRING")

search_fields = ["SHAPE@", "OID@","Stream_Order"]
insert_fields = ["SHAPE@", "LineOID", "Type", "Segment_Distance"]

arcpy.AddMessage("Setting up the data for processing....")
arcpy.AddMessage("\t\tDrawing points...")

userdistance=20
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

                while distance <= length:
                    point = line_geom.positionAlongLine(distance, False)
                    insert.insertRow((point, oid, "mid", float(distance)))
                    distance += float(userdistance)
                
                insert.insertRow((start_of_line, oid, "start", float(distance)))
                insert.insertRow((end_of_line, oid, "end", float(distance)))
del search
del insert

#copy output points drawn on line into output gdb
perm_pointz=copy_features(mem_point,env.workspace,naming+"_"+"start_and_end_points")

#buffer the endpoints
end_point_buffers=os.path.join(env.workspace,naming+"_endpoint_buffers")
arcpy.Buffer_analysis(mem_point,end_point_buffers, "25 meters")

result = arcpy.GetCount_management(end_point_buffers)

#making result into an integer?
buffer_count = int(result.getOutput(0))
arcpy.AddMessage("buffer_count is"+str(buffer_count))

search_fields=["OID@"]
#iterate through buffers and clip them
with arcpy.da.SearchCursor(end_point_buffers, (search_fields)) as search:
        for row in search:
                arcpy.AddMessage("iterating "+str(row[0]))
                #make feature layer out of each buffer
                current_buffer=arcpy.MakeFeatureLayer_management(end_point_buffers,"temp.lyr","OBJECTID="+str(row[0]))
                arcpy.CopyFeatures_management(current_buffer,os.path.join(env.workspace,naming+"current_buffer"))
                current_buffer=os.path.join(env.workspace,naming+"current_buffer")
                
                #create fishent out of isolated buffer
                arcpy.AddMessage("describing")
                desc = arcpy.Describe(current_buffer)
                current_fishnet=os.path.join(env.workspace,naming+"current_fishnet")
                arcpy.AddMessage("fishnetting")
                arcpy.CreateFishnet_management(current_fishnet,str(desc.extent.lowerLeft),str(desc.extent.XMin) + " " + str(desc.extent.YMax + 10),"","","2", "1","","NO_LABELS", current_buffer,'POLYGON')

                #clip current end point buffer by top half of fishnet
                #select top half of fishnet
                top_net=arcpy.MakeFeatureLayer_management(current_fishnet,"top_net.lyr","OID=2")
                clip_buffer=os.path.join(env.workspace,naming+"clipped_buffer")
                arcpy.AddMessage("clipping")
                arcpy.Clip_analysis(current_buffer, top_net, clip_buffer)

                #if this is first buffer
                if row[0]==1:
                        #create the clipped buffer feature class
                        clipped_buffer_fc=arcpy.CreateFeatureclass_management(env.workspace, naming+"_clipped_buffer_fc", "POLYGON",clip_buffer,"DISABLED", "DISABLED", clip_buffer)
                #append clipped buffer to clipped buffer fc
                arcpy.AddMessage("appending")
                arcpy.Append_management(clip_buffer,clipped_buffer_fc)

del search

#mask the DEM by the clipped buffers
arcpy.AddMessage("\t\tMasking DEM...")
masked_dem = ExtractByMask(dem, clipped_buffer_fc)
masked_dem.save(os.path.join(env.workspace,naming+"_maskedraster"))

#calculate the zonal minimum elevation in each clipped buffer
outZonalStats = ZonalStatistics(clipped_buffer_fc, "OBJECTID", masked_dem,"MINIMUM","DATA")
outZonalStats.save(os.path.join(env.workspace,naming+"endpoint_min_by_zones"))

#now convert the buffers to rasters by object id so we can load them into points
arcpy.AddMessage("\t\tConverting buffers into raster...")
bufferraster=os.path.join(env.workspace,naming+"_bufferraster")
arcpy.PolygonToRaster_conversion(clipped_buffer_fc, "OBJECTID", bufferraster, "#", "#", 1)

#vectorize min zone rasters
min_points=os.path.join(env.workspace,naming+"min_points")
arcpy.RasterToPoint_conversion(outZonalStats, min_points, "Value")

inRasterlist=[[bufferraster]]
arcpy.AddMessage("\t\tExtracting values to points...")
ExtractMultiValuesToPoints(min_points,inRasterlist,"NONE")

arcpy.AddField_management(perm_pointz, "min_elevation", "FLOAT")
search_fields=["OID@", "min_elevation"]

#iterate through end points and write in min values
with arcpy.da.UpdateCursor(perm_pointz, (search_fields)) as update:
        for row in update:

                #grab min point that is nearest to end point
                nearest_min=arcpy.MakeFeatureLayer_management(min_points,"min_point.lyr",naming+"_bufferraster="+str(row[0]))

                #obtain value of point
                min_fields=["grid_code"]
                with arcpy.da.SearchCursor(nearest_min, (min_fields)) as search:
                        for roww in search:
                                min_value=roww[0]
                                break

                #populate field of end point with min value
                row[1]=min_value

                update.updateRow(row)

del update

#iterate through input lines to calculate stream gradeint
arcpy.AddField_management(polyline, "start_elev", "FLOAT")
arcpy.AddField_management(polyline, "end_elev", "FLOAT")
arcpy.AddField_management(polyline, "Stream_Gradient", "FLOAT")

search_fields=["OID@","start_elev","end_elev","SHAPE@LENGTH","Stream_Gradient"]
with arcpy.da.UpdateCursor(polyline, (search_fields)) as update:
        for row in update:

                #select end points of line
                end_points=arcpy.MakeFeatureLayer_management(perm_pointz,"min_point.lyr","LineOID="+str(row[0]))

                start_value=None
                end_value=None

                #obtain values of end points and put them into line
                min_fields=["min_elevation","type"]
                with arcpy.da.SearchCursor(end_points, (min_fields)) as search:
                        for roww in search:
                                if roww[1]=="start":
                                        start_value=roww[0]

                                elif roww[1]=="end":
                                        end_value=roww[0]
                                
                #populate field of end point with min value
                row[1]=start_value
                row[2]=end_value

                arcpy.AddMessage(str(row[3]))
                
                #calculate stream gradeint
                gradient=(start_value-end_value)/float(row[3])
                arcpy.AddMessage(gradient)
                row[4]=float(gradient)

                update.updateRow(row)

del update

#SORT POINTS BY LINEOID AND buffer raster
sub_perm_pointz=os.path.join(env.workspace,naming+"endpoints_sorted")
arcpy.Sort_management(perm_pointz, sub_perm_pointz, [["LineOID", "ASCENDING"],[naming+"_bufferraster", "ASCENDING"]])

arcpy.AddField_management(sub_perm_pointz, "Sub_Segment_Gradient", "FLOAT")
search_fields=["OID@","Type","min_elevation","Sub_Segment_Gradient"]
#iterate through points and calculate individual gradeints
with arcpy.da.UpdateCursor(sub_perm_pointz, (search_fields)) as update:
        for row in update:

                current_elev=row[2]
                
                #if its not the starting point
                if row[1]!="start":
                        sub_seg_gradient=float((prev_elev-current_elev)/userdistance)
                        
                prev_elev=row[2]
                row[3]=sub_seg_gradient

                update.updateRow(row)

del update

arcpy.CopyFeatures_management(sub_perm_pointz,perm_pointz)

