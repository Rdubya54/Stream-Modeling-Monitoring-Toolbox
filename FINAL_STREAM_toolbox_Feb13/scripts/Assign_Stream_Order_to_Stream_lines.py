import arcpy
import os
from arcpy import env
from arcpy.sa import *
from arcpy import da

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("spatial")

polyline = arcpy.GetParameterAsText(0)
og_stream_raster=arcpy.GetParameterAsText(1)
filledflow=arcpy.GetParameterAsText(2)

#copy features to in memory to increase performance

##polyline =arcpy.CopyFeatures_management(og_polyline,r"in_memory/lines")
stream_raster=arcpy.CopyRaster_management(og_stream_raster,r"in_memory/b")
##filledflow=arcpy.CopyRaster_management(og_filled_flowdir,r"in_memory/c")
points="in_memory/Strahler_points"
points2="in_memory/Shreve_points"
#calculate Stream order from raster 

outStreamOrder=StreamOrder(stream_raster,filledflow,"STRAHLER")

#assign stream order values to polylines using points
#first create points
mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

arcpy.AddField_management(polyline,"Strahler_Stream_Order", "INTEGER")
arcpy.AddField_management(mem_point, "LINE_OID", "INTEGER")

ayylmao_fields=["SHAPE@","Strahler_Stream_Order","OID@"]
nug_fields=["SHAPE@","LINE_OID"]

with arcpy.da.SearchCursor(polyline,(ayylmao_fields)) as cursor3:
    with arcpy.da.InsertCursor(mem_point, (nug_fields)) as insertz:

        for i in cursor3:
            oid=str(i[2])
            line_geom = i[0]
            length=float(line_geom.length)
            midpoint=length/2
            midhalf=midpoint/2
            midmidhalf=midhalf/2
            
            start_of_line = arcpy.PointGeometry(line_geom.firstPoint)

            insertz.insertRow((start_of_line,oid))
            
            end_of_line = arcpy.PointGeometry(line_geom.lastPoint)

            insertz.insertRow((end_of_line,oid))

            xextra1=line_geom.positionAlongLine(midmidhalf,False)

            insertz.insertRow((xextra1,oid))

            extra1=line_geom.positionAlongLine(midhalf,False)

            insertz.insertRow((extra1,oid))

            mid_point=line_geom.positionAlongLine(midpoint,False)

            insertz.insertRow((mid_point,oid))

            extra2=line_geom.positionAlongLine(midpoint+midhalf,False)

            insertz.insertRow((extra2,oid))

            xextra2=line_geom.positionAlongLine(midpoint+midhalf+midmidhalf,False)

            insertz.insertRow((xextra2,oid))

del cursor3
del insertz

#extract stream order values to points

ExtractMultiValuesToPoints(mem_point, [[outStreamOrder,"Strahler_Stream_Order"]])

arcpy.CopyFeatures_management(mem_point,points)

#make new stream order field
arcpy.AddField_management(polyline,"Strahler_Stream_Order_", "INTEGER")

count3=1
numberomodes=0
modelist=[]
listt=[]

fug_fields=["Strahler_Stream_Order","LINE_OID"]

with arcpy.da.SearchCursor(mem_point,(fug_fields)) as djcursor:
    
    for point in djcursor:

##        arcpy.AddMessage("top count is {0}".format(count3))
        if count3==8:
##            arcpy.AddMessage("list is {0}".format(listt))
            #remove nones from list
            listt=[x for x in listt if x is not None]
##            arcpy.AddMessage("list after removing nones {0}".format(listt))
            mode=max(set(listt), key=listt.count)
            numberomodes+=1
##            arcpy.AddMessage("mode is {0}".format(mode))
##            arcpy.AddMessage("numberomodes is {0}".format(numberomodes))
            modelist.append(mode)
            count3=1
            listt=[]
            listt.append(point[0])
            count3+=1

        else:
            listt.append(point[0])
            count3+=1

##        arcpy.AddMessage("count bottom is {0}".format(count3))
##    arcpy.AddMessage("list is {0}".format(listt))
    listt=[x for x in listt if x!=None]
##    arcpy.AddMessage("list after removing nones {0}".format(listt))
    mode=max(set(listt), key=listt.count)
    numberomodes+=1
##    arcpy.AddMessage("mode is {0}".format(mode))
##    arcpy.AddMessage("numberomodes is {0}".format(numberomodes))
    modelist.append(mode)  

del listt
del point
del djcursor

fox=0

suh_fields=["Strahler_Stream_Order_","Strahler_Stream_Order"]

with arcpy.da.UpdateCursor(polyline,(suh_fields)) as lil_cursor:
    for rowww in lil_cursor:
##        arcpy.AddMessage("MODE BEING ADDED IS {0}".format(modelist[fox]))
##        arcpy.AddMessage("fox IS {0}".format(fox))
        if modelist[fox] is not None:
            rowww[0]=modelist[fox]
            
        else:
##            arcpy.AddMessage("no wait MODE BEING ADDED IS {0}".format(rowww[1]))
            rowww[0]=rowww[1]
            
        lil_cursor.updateRow(rowww)
        fox+=1
del rowww
del lil_cursor

#for trouble 
##field_names = [f.name for f in arcpy.ListFields(polyline)]
##
##for f in field_names:
##    arcpy.AddMessage(str(f))

arcpy.DeleteField_management(polyline,["Strahler_Stream_Order"])
arcpy.Delete_management(mem_point)

#for trouble 
##field_names = [f.name for f in arcpy.ListFields(polyline)]
##
##for f in field_names:
##    arcpy.AddMessage("after: "+str(f))

#REPEAT PROCESS FOR SHREVE

outStreamOrder2=StreamOrder(stream_raster,filledflow,"SHREVE")

mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", polyline)

arcpy.AddField_management(polyline, "Shreve_Stream_Order", "INTEGER")
arcpy.AddField_management(mem_point, "LINE_OID", "INTEGER")

ayylmao_fields=["SHAPE@","Shreve_Stream_Order","OID@"]
nug_fields=["SHAPE@","LINE_OID"]

with arcpy.da.SearchCursor(polyline,(ayylmao_fields)) as cursor3:
    with arcpy.da.InsertCursor(mem_point, (nug_fields)) as insertz:

        for i in cursor3:
            oid=str(i[2])
            line_geom = i[0]
            length=float(line_geom.length)
            midpoint=length/2
            midhalf=midpoint/2
            midmidhalf=midhalf/2
            
            start_of_line = arcpy.PointGeometry(line_geom.firstPoint)

            insertz.insertRow((start_of_line,oid))
            
            end_of_line = arcpy.PointGeometry(line_geom.lastPoint)

            insertz.insertRow((end_of_line,oid))

            xextra1=line_geom.positionAlongLine(midmidhalf,False)

            insertz.insertRow((xextra1,oid))

            extra1=line_geom.positionAlongLine(midhalf,False)

            insertz.insertRow((extra1,oid))

            mid_point=line_geom.positionAlongLine(midpoint,False)

            insertz.insertRow((mid_point,oid))

            extra2=line_geom.positionAlongLine(midpoint+midhalf,False)

            insertz.insertRow((extra2,oid))

            xextra2=line_geom.positionAlongLine(midpoint+midhalf+midmidhalf,False)

            insertz.insertRow((xextra2,oid))

del cursor3
del insertz

#extract stream order values to points

ExtractMultiValuesToPoints(mem_point, [[outStreamOrder2,"Shreve_Stream_Order"]])

arcpy.CopyFeatures_management(mem_point,points2)

#make new stream order field
arcpy.AddField_management(polyline, "Shreve_Stream_Order_", "INTEGER")

count3=1
numberomodes=0
modelist=[]

fug_fields=["Shreve_Stream_Order","LINE_OID"]

#put 8 points on every line an equal distance apart

with arcpy.da.SearchCursor(mem_point,(fug_fields)) as djcursorr:


    listt=[]
    
    for point in djcursorr:

##        arcpy.AddMessage("top count is {0}".format(count3))
        if count3==8:
##            arcpy.AddMessage("list is {0}".format(listt))
            #remove nones from list
            listt=[x for x in listt if x !=None]
##            arcpy.AddMessage("list after removing nones {0}".format(listt))
            mode=max(set(listt), key=listt.count)
            numberomodes+=1
##            arcpy.AddMessage("mode is {0}".format(mode))
##            arcpy.AddMessage("numberomodes is {0}".format(numberomodes))
            modelist.append(mode)
            count3=1
            listt=[]
            listt.append(point[0])
            count3+=1

        else:
            listt.append(point[0])
            count3+=1

##        arcpy.AddMessage("count bottom is {0}".format(count3))
##    arcpy.AddMessage("list is {0}".format(listt))
    listt=[x for x in listt if x!=None]
##    arcpy.AddMessage("list after removing nones {0}".format(listt))
    mode=max(set(listt), key=listt.count)
    numberomodes+=1
##    arcpy.AddMessage("mode is {0}".format(mode))
##    arcpy.AddMessage("numberomodes is {0}".format(numberomodes))
    modelist.append(mode)  

del listt
del point
del djcursorr

fox=0

suh_fields=["Shreve_Stream_Order_","Shreve_Stream_Order"]

with arcpy.da.UpdateCursor(polyline,(suh_fields)) as lil_cursor:
    for rowww in lil_cursor:
##        arcpy.AddMessage("MODE BEING ADDED IS {0}".format(modelist[fox]))
##        arcpy.AddMessage("fox IS {0}".format(fox))
        if modelist[fox] is not None:
            rowww[0]=modelist[fox]
            
        else:
##            arcpy.AddMessage("no wait MODE BEING ADDED IS {0}".format(rowww[1]))
            rowww[0]=rowww[1]
            
        lil_cursor.updateRow(rowww)
        fox+=1
del rowww
del lil_cursor
del modelist

#for trouble 
##field_names = [f.name for f in arcpy.ListFields(polyline)]
##
##for f in field_names:
##    arcpy.AddMessage(str(f))

arcpy.DeleteField_management(polyline,["Shreve_Stream_Order"])
arcpy.Delete_management(mem_point)

#for trouble 
field_names = [f.name for f in arcpy.ListFields(polyline)]

##for f in field_names:
##    arcpy.AddMessage("after: "+str(f))

##desc=arcpy.Describe(og_polyline)
##
##arcpy.CopyFeatures_management(polyline,og_polyline)
##
##field_names = [f.name for f in arcpy.ListFields(og_polyline)]
##
##for f in field_names:
##    arcpy.AddMessage("polyline: "+str(f))


##arcpy.Delete_management(polyline)
arcpy.Delete_management(outStreamOrder)
arcpy.Delete_management(outStreamOrder2)
arcpy.Delete_management(stream_raster)
arcpy.Delete_management(points)
arcpy.Delete_management(points2)
