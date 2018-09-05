import arcpy
import os
import string
from arcpy import env
from arcpy.sa import *
from math import atan2, pi 

env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#get parameters
input_dem=arcpy.GetParameterAsText(0)
polyline=arcpy.GetParameterAsText(1)
env.workspace=arcpy.GetParameterAsText(2)
naming=arcpy.GetParameterAsText(3)

def getCardinal(angle):  
    lstCardinal = [[22.5,"E"], [67.5, "NE"], [112.5, "N"],  
                   [157.5, "NW"], [202.5, "W"], [247.5, "SW"],  
                   [292.5, "S"], [337.5, "SE"], [360, "E"]]  
  
    for item in lstCardinal:  
        value = item[0]  
        if angle < value:  
            cardinal = item[1]  
            break  
    return cardinal  
  
def calcGeomCardinality(pnt1,pnt2):  
##    arcpy.AddMessage("first point is "+str(pnt1))
    angle_deg = (atan2(pnt2.getPart().Y - pnt1.getPart().Y, pnt2.getPart().X - pnt1.getPart().X)) * 180.0 / pi  
    if angle_deg < 0:  
        angle_deg = 360 + angle_deg  
    return getCardinal(angle_deg)

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
arcpy.AddField_management(mem_point, "DIRECTION", "STRING")

#get count of polylines
result = arcpy.GetCount_management(mem_lines)

#making result into an integer?
features = int(result.getOutput(0))

search_fields = ["SHAPE@", "OID@"]
insert_fields = ["SHAPE@", "LineOID", "Value","DIRECTION"]

#####put points on lines########################################################################

userdistance=1
direction_list=[]
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
                last_point=start_of_line

                #insert point at every userdistance
                while distance <= length:
                    point = line_geom.positionAlongLine(distance, False)
                    direction=calcGeomCardinality(last_point,point)
                    insert.insertRow((point, oid, float(distance),direction))
                    direction_list.append(direction)
                    distance += float(userdistance)
                    last_point=point


                else:
                        direction="E"          
                    
                insert.insertRow((end_of_line, oid, length,direction))
                direction_list.append(direction)

del search
del insert


#assign coordinate to line points
arcpy.AddXY_management(mem_point)

#save to perm memory
saved_points=os.path.join(env.workspace,naming+"_saved_points")
arcpy.CopyFeatures_management(mem_point,saved_points)

#create new feature class for cross section points
cross_section_points = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)
cross_section_lines = arcpy.CreateFeatureclass_management(env.workspace, "LINES_in_memory", "POLYLINE", "", "DISABLED", "DISABLED", polyline)

arcpy.AddField_management(cross_section_points, "PointOID", "LONG")
arcpy.AddField_management(cross_section_points, "LineOID", "LONG")
arcpy.AddField_management(cross_section_points, "Type", "LONG")
arcpy.AddField_management(cross_section_points, "DIRECTION", "STRING")

arcpy.AddField_management(cross_section_lines, "PointOID", "LONG")
arcpy.AddField_management(cross_section_lines, "LineOID", "LONG")

#iterate through line points and determeine coordinates for cross section points
search_fields = ["POINT_X","POINT_Y","OID@","LineOID","SHAPE@","DIRECTION"]
insert_fields = ["SHAPE@","PointOID","LineOID","Type","DIRECTION"]
insert_fields_lines = ["SHAPE@","PointOID","LineOID"]
                
bufferdist=25
with arcpy.da.SearchCursor(saved_points, (search_fields)) as search:
    with arcpy.da.InsertCursor(cross_section_points, (insert_fields)) as insert_point:
            with arcpy.da.InsertCursor(cross_section_lines, (insert_fields_lines)) as insert_line:
                for row in search:

                        direction=row[5]

                        if direction=="N" or direction=="S":
                                point1_x=row[0]+bufferdist
                                point1_y=row[1]
                                                
                                point2_x=row[0]-bufferdist
                                point2_y=row[1]

                        elif direction=="SW" or direction=="NW" or direction=="NE" or direction=="SE":

                                #create list of directions that include every index after the og_points index
                                listt=direction_list[row[2]:]

                                for i in listt:
                                        reference=i

                                        if reference!="SW" or reference!="SE" or reference!="NW" or reference!="NE":
                                                break
                                        
                                if reference=="N" or reference=="S":
                                        point1_x=row[0]+bufferdist
                                        point1_y=row[1]
                                                        
                                        point2_x=row[0]-bufferdist
                                        point2_y=row[1]


                                else:
                                        point1_x=row[0]
                                        point1_y=row[1]+bufferdist
                                                        
                                        point2_x=row[0]
                                        point2_y=row[1]-bufferdist

                        
                                
                        else:
                                point1_x=row[0]
                                point1_y=row[1]+bufferdist
                                                
                                point2_x=row[0]
                                point2_y=row[1]-bufferdist


                        array=arcpy.Array()
                        
                        point1=arcpy.Point(point1_x,point1_y)
                        point2=arcpy.Point(point2_x,point2_y)
                        array.add(point1)
                        array.add(point2)
                        
                        insert_point.insertRow((point1, row[2],row[3],"0",direction))
                        insert_point.insertRow((point2, row[2],row[3],"1",direction))

                        polyline=arcpy.Polyline(array)
                        insert_line.insertRow(([polyline,row[2],row[3]]))

del search
del insert_point
del insert_line

perm=os.path.join(env.workspace,naming+"_cross_section_points")
arcpy.management.CopyFeatures(cross_section_points,perm)

perm=os.path.join(env.workspace,naming+"_cross_section_lines")
arcpy.management.CopyFeatures(cross_section_lines,perm)
###############################################################################################################################################################
###############################################################################################################################################################
mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", cross_section_lines, "DISABLED", "DISABLED", cross_section_lines)

#add line object id and value to the point feature class
arcpy.AddField_management(mem_point, "LineOID", "LONG")
arcpy.AddField_management(mem_point, "Value", "FLOAT")

search_fields = ["SHAPE@", "PointOID","LineOID"]
insert_fields = ["SHAPE@", "PointOID","LineOID", "Value"]

userdistance=1
# iterate through every cross section line and create points for extracting elevation values
with arcpy.da.SearchCursor(cross_section_lines, (search_fields)) as search:
    with arcpy.da.InsertCursor(mem_point, (insert_fields)) as insert:
        for row in search:
            
        #line geom is shape in search fields
                line_geom = row[0]
                length = float(line_geom.length)
                distance = 0
                
        #oid is OID@ in search fields            
                oid = str(row[1])

                #returns a point on the line at a specific distance from the beginning
                point = line_geom.positionAlongLine(distance, False)

                #insert point at every userdistance
                while distance <= length:
                    point = line_geom.positionAlongLine(distance, False)
                    insert.insertRow((point, row[1],row[2], float(distance)))
                    distance += float(userdistance)
                    

del search
del insert

cross_section_many_points=os.path.join(env.workspace,naming+"_line_pointd")
arcpy.CopyFeatures_management(mem_point,cross_section_many_points)
