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
masked_AC=arcpy.GetParameterAsText(1)
tolerance=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)

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

spatial_ref = arcpy.Describe(polyline).spatialReference
output_points=os.path.join(env.workspace,naming+"_"+"output_points")
##headcuts=os.path.join(env.workspace,naming+"_"+"suspected_headcuts")

mem_lines=arcpy.CopyFeatures_management(polyline,r"in_memory/lines")
mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

##arcpy.CalculateField_management(polyline,"Direction_of_Flow",

#add line object id and value to the point feature class
arcpy.AddField_management(mem_point, "LineOID", "LONG")
arcpy.AddField_management(mem_point, "Value", "FLOAT")

#get count of polylines
result = arcpy.GetCount_management(mem_lines)

#making result into an integer?
features = int(result.getOutput(0))

search_fields = ["SHAPE@", "OID@"]
insert_fields = ["SHAPE@", "LineOID", "Value"]

#####put points on lines########################################################################

userdistance=0.5
# makes search cursor and insert cursor into search/insert
with arcpy.da.SearchCursor(mem_lines, (search_fields)) as search:
    with arcpy.da.InsertCursor(mem_point, (insert_fields)) as insert:
        for row in search:
            
        #line geom is shape in search fields
                line_geom = row[0]
                length = float(line_geom.length)
                distance = 0
                
        #oid is OID@ in search fields            
                oid = str(row[1])

                #creates a point at the start and end of line for final point that is less then the userdistance away
                start_of_line = arcpy.PointGeometry(line_geom.firstPoint)
                end_of_line = arcpy.PointGeometry(line_geom.lastPoint)

                #returns a point on the line at a specific distance from the beginning
                point = line_geom.positionAlongLine(distance, False)

                #insert point at every userdistance
                while distance <= length:
                    point = line_geom.positionAlongLine(distance, False)
                    insert.insertRow((point, oid, float(distance)))
                    distance += float(userdistance)
                    
                insert.insertRow((end_of_line, oid, length))

del search
del insert

arcpy.Delete_management(mem_lines)

##inputDEM=arcpy.CopyRaster_management(DEM,r"in_memory/a")

# transfer elevation to points

ExtractMultiValuesToPoints(mem_point, [[masked_AC, "Min_Elevation"]])

##arcpy.Delete_management(inputDEM)

# calculate elevation change

arcpy.AddField_management(mem_point,"Ev_Change","FLOAT")

feilds=["Min_Elevation","LINEOID","Ev_Change","OID@"]

elev1=0
line_OID=1

with arcpy.da.UpdateCursor(mem_point,feilds) as update:
        
        for row in update:

                arcpy.AddMessage("doing line "+str(line_OID))
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

##                        arcpy.AddMessage(str(row[2]))
##                        arcpy.AddMessage(str(elev2))
##                        import sys
##                        sys.exit
        
arcpy.CopyFeatures_management(mem_point,output_points)

#make mem_points a layer so select by attibutes can be done

layer=arcpy.MakeFeatureLayer_management(mem_point,"output_points.lyr")

arcpy.SelectLayerByAttribute_management(layer, "NEW_SELECTION", "Ev_Change >"+str(tolerance)+"OR Ev_Change <-"+str(tolerance))

arcpy.FeatureClassToFeatureClass_conversion(layer,env.workspace,naming+"_"+"suspected_headcuts")

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
