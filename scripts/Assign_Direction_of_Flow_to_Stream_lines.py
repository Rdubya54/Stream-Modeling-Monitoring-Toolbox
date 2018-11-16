import arcpy
import os
from arcpy import env
from arcpy.sa import *
from arcpy import da
from math import atan2, pi 


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
  
def calcGeomCardinality(polyline):  
    pnt1 = polyline.firstPoint  
    pnt2 = polyline.lastPoint
    angle_deg = (atan2(pnt2.Y - pnt1.Y, pnt2.X - pnt1.X)) * 180.0 / pi  
    if angle_deg < 0:  
        angle_deg = 360 + angle_deg  
    return getCardinal(angle_deg)


#code starts here
arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("spatial")

#get input parameters
polyline = arcpy.GetParameterAsText(0)

#add field for direction of flow to streamlines
arcpy.AddField_management(polyline, "Direction_of_Flow", "TEXT")

calc_fields=["Direction_of_Flow","SHAPE@"]

arcpy.AddMessage("Writing Flow Direction of Stream Segement....")

#iterate through streamlines and calculate direction of flow
with arcpy.da.UpdateCursor(polyline,(calc_fields)) as cursor:

    for i in cursor:

        i[0]=calcGeomCardinality(i[1])
        cursor.updateRow(i)

del cursor

