import arcpy
import os
from arcpy import env
from arcpy.sa import *

#this funtion finds the necessary aggregate point dist for the aggregate points
#tool to produce polygons that resemble the shape of channels. Getting this value wrong
#results in segement streams or blocky shaped polygons
def calculate_aggregate_point_dist():

        #get cell size
        originalDEM=arcpy.GetParameterAsText(0)
        arcpy.AddMessage("Checking cell size of raster... ")
        demrez = arcpy.GetRasterProperties_management(originalDEM, "CELLSIZEX")
        demres = demrez.getOutput(0)

        #forumula for determining aggregate point dist
        agg_dist=(float(demres)*0.5)+float(demres)
                
        sr = arcpy.Describe(originalDEM).spatialReference
        unit = sr.linearUnitName

        #get units of projection
        if unit!="Feet":
                unit=unit+"s"

##        arcpy.AddMessage("unit is "+str(unit))

        agg_dist=str(agg_dist)+" "+unit

        return str(agg_dist)

env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#get parameters
DEM=arcpy.GetParameterAsText(0)
dem_points=arcpy.GetParameterAsText(1)
minfield=arcpy.GetParameterAsText(2)
SO_field=arcpy.GetParameterAsText(3)
tol_1=arcpy.GetParameterAsText(4)
tol_2=arcpy.GetParameterAsText(5)
tol_3=arcpy.GetParameterAsText(6)
tol_4=arcpy.GetParameterAsText(7)
tol_5=arcpy.GetParameterAsText(8)
tol_6=arcpy.GetParameterAsText(9)
tol_7=arcpy.GetParameterAsText(10)
tol_8=arcpy.GetParameterAsText(11)
env.workspace=arcpy.GetParameterAsText(12)
naming=arcpy.GetParameterAsText(13)

arcpy.AddMessage("Identifying points that are Active Channel...(Step 1 of 3)")

sql_query=("("+str(SO_field)+"=1 AND grid_code <= ("+str(minfield)+"+"+str(tol_1)+")) OR ("+ str(SO_field)+"=2 AND grid_code <= ("+str(minfield)+"+"+str(tol_2)+")) OR "
"("+str(SO_field)+"=3 AND grid_code <= ("+str(minfield)+"+"+str(tol_3)+")) OR ("+ str(SO_field)+"=4 AND grid_code <= ("+str(minfield)+"+"+str(tol_4)+")) OR "
"("+str(SO_field)+"=5 AND grid_code <= ("+str(minfield)+"+"+str(tol_5)+")) OR ("+ str(SO_field)+"=6 AND grid_code <= ("+str(minfield)+"+"+str(tol_6)+")) OR "
"("+str(SO_field)+"=7 AND grid_code <= ("+str(minfield)+"+"+str(tol_7)+")) OR ("+ str(SO_field)+">=8 AND grid_code <= ("+str(minfield)+"+"+str(tol_8)+"))")

arcpy.AddMessage(sql_query)
 
lyr=arcpy.MakeFeatureLayer_management(dem_points,"slayer",sql_query)

#use a while loop to itrate until counter exceeds buffer number
#to iterate through every buffer
arcpy.AddMessage("Copying identified points into workspace...(Step 2 of 3)")
final_points=arcpy.CopyFeatures_management(lyr,os.path.join(env.workspace,naming+"_"+"AC_Points"))

polys_draft=os.path.join(env.workspace, naming+"_Active_Channel_Polys_draft")

#get necessary point dist for aggregate points. 
agg_dist=calculate_aggregate_point_dist()
###create polygons from points
arcpy.AddMessage("Building Active Channel Polygons from points...(Step 3 of 3)")
try:
        arcpy.AggregatePoints_cartography(lyr,polys_draft, agg_dist)

except:
        arcpy.AddMessage("Polygons could not be created because an Advanced License has not been checked out.")

arcpy.Delete_management(os.path.join(env.workspace,naming+"Active_Channel_Polys_draft_tbl"))

