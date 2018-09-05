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
env.workspace=arcpy.GetParameterAsText(1)
naming=arcpy.GetParameterAsText(2)

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

userdistance=20
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

#assign coordinate to line points
arcpy.AddXY_management(mem_point)

#save to perm memory
saved_points=os.path.join(env.workspace,naming+"_saved_points")
arcpy.CopyFeatures_management(mem_point,saved_points)

#create new feature class for cross section points
cross_section_points = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

arcpy.AddField_management(cross_section_points, "POINT_X", "DOUBLE")
arcpy.AddField_management(cross_section_points, "POINT_Y", "DOUBLE")
arcpy.AddField_management(cross_section_points, "PointOID", "LONG")
arcpy.AddField_management(cross_section_points, "LineOID", "LONG")
arcpy.AddField_management(cross_section_points, "Type", "LONG")

#iterate through line points and determeine coordinates for cross section points
search_fields = ["POINT_X","POINT_Y","OID@","LineOID"]
insert_fields = ["POINT_X","POINT_Y","PointOID","LineOID","Type"]
with arcpy.da.SearchCursor(saved_points, (search_fields)) as search:
    with arcpy.da.InsertCursor(cross_section_points, (insert_fields)) as insert:
        for row in search:

                arcpy.AddMessage("creating point")
                point1_x=row[0]
                point1_y=row[1]+0.5
                arcpy.AddMessage("POINT X IS "+str(point1_x))             
                point2_x=row[0]
                point2_y=row[1]-0.5

                insert.insertRow((point1_x,point1_y,row[2],row[3],"0"))
                insert.insertRow((point2_x,point2_y,row[2],row[3],"1"))

del search
del insert

out_fc=os.path.join(env.workspace,naming+"_woahhh")
arcpy.management.CopyFeatures(cross_section_points, out_fc)

lyr = str(arcpy.management.MakeXYEventLayer(cross_section_points, "POINT_X", "POINT_Y", 'temp', polyline).getOutput(0))
out_fc=os.path.join(env.workspace,naming+"_gahhh")
arcpy.management.CopyFeatures(lyr, out_fc)

##perm=os.path.join(env.workspace,naming+"_wtf")
##arcpy.management.CopyFeatures(cross_section_points,perm)


