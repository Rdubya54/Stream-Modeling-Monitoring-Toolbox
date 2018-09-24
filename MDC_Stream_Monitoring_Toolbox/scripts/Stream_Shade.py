import arcpy
import os
from arcpy import env
from arcpy.sa import *
from arcpy import da
from random import randint

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("spatial")

oldstreams = arcpy.GetParameterAsText(0)
AC=arcpy.GetParameterAsText(1)
VEG_HEIGHT=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)
in_mem=r"in_memory/"

streambuffer=os.path.join(env.workspace,naming+"_streambuffer")
segmented_AC=os.path.join(in_mem,naming+"_segmented_AC"+str(randint(0,99)))
centroidswithvalues=os.path.join(in_mem,naming+"centroidswithvalues"+str(randint(0,99)))
final_segmented_AC=os.path.join(env.workspace,naming+"_polys_with_StreamShade")

#only select treams that are second order and up
##arcpy.SelectLayerByAttribute_management(oldstreams, "NEW_SELECTION","Stream_Order > 1")

#CREATE THE STREAM BUFFER. THE ADVANCED LISCNESE WILL HAVE TO BE CHECKED OUT
#SO FLAT OUTPUTS CAN BE OBTAINED
arcpy.Buffer_analysis(oldstreams, streambuffer, "25 Feet", "FULL", "FLAT", "NONE")

#CLIP STREAM BUFFER TO THE ACTIVE CHANNEL POLYGONS
arcpy.Clip_analysis(streambuffer, AC, segmented_AC)

#RECLASS VEGETATION RASTER by vegetation of no vegetation

ONESANDZEROS = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,0.49,0],[0.5,1000,1]]), "NODATA")
ONESANDZEROS.save(os.path.join(env.workspace,naming+"Shaded_vs_Unshaded"))

#convert segmented polygons to layer
seg=arcpy.MakeFeatureLayer_management(segmented_AC,"seg.lyr")

cell_size =float(arcpy.GetRasterProperties_management(VEG_HEIGHT, 'CELLSIZEX').getOutput(0))

#Get Statistics for each segement USING ONES AND ZEROS TO GET TOTAL CELLS SHADED
zonalraster=ZonalStatistics(seg, "OBJECTID", ONESANDZEROS,"SUM","DATA")
zonalraster.save(os.path.join(env.workspace,naming+"_zonalraster"))

###put centroids in segmented polys 
centroids=arcpy.CreateRandomPoints_management(in_mem, naming+"centroids"+str(randint(0,99)), seg,"#", 15)

#extract value to centroids
ExtractValuesToPoints(centroids, zonalraster, centroidswithvalues,"NONE", "VALUE_ONLY")

#add necessary feilds
arcpy.AddField_management(seg, "PERCENT_SHADED", "FLOAT")
arcpy.AddField_management(seg, "SHADED_CELL_COUNT", "FLOAT")

#put point values into corresponding polygons
search_fields = ["OID@","RASTERVALU","CID"]
update_fields = ["OID@","SHAPE@AREA","PERCENT_SHADED","SHADED_CELL_COUNT"]

modelist=[]

# makes search cursor and insert cursor into search/insert
with arcpy.da.SearchCursor(centroidswithvalues, (search_fields)) as search:
        for row in search:

            modelist.append(row[1])

            #once it changes all of ones polygons points
            #are in list. now get mode
            if len(modelist)==5:
                #remove nones from list
                modelist=[x for x in modelist if x is not None]
                modelist=[x for x in modelist if x != -9999.0]
##                arcpy.AddMessage("Mode list "+str(modelist))

                #calculate mode
                mode=max(set(modelist), key=modelist.count)
##                arcpy.AddMessage("Mode is "+str(mode))
                
                #the mode is sumshaded for the polygon with the corresponding CID
                sumshaded=mode
                
                pointOID=row[2]
                with arcpy.da.UpdateCursor(seg, (update_fields)) as update:
                    for roww in update:
                        
                        polyOID=roww[0]

                        #if pointOID IS polyOID
##                        arcpy.AddMessage("point oid is "+str(pointOID)+" and polyOID is "+str(polyOID))
                        if (pointOID==polyOID):
                            areaofpoly=roww[1]
                            roww[3]=sumshaded
                            percentshaded=((sumshaded*(cell_size*cell_size))/areaofpoly)*100
##                            arcpy.AddMessage("Percent shaded is:"+str(percentshaded))

                            if percentshaded>200:
                                percentshaded=None
                                roww[2]=percentshaded

                            elif percentshaded>100 and percentshaded<200:
                                percentshaded=100
                                roww[2]=percentshaded

                            else:
                                roww[2]=int(round(percentshaded))

                            update.updateRow(roww)

                            break

                    #RESET MODELIST
                    modelist=[]

del search
del update

#DELETE POLYGONS WITH A NULL VALUE BECAUSE THEN THEY ARE OVERLAPING AND AREN'T NEEDED
##arcpy.SelectLayerByAttribute_management(seg, "NEW_SELECTION", "PERCENT_SHADED IS NOT NULL")

#COPY SEGEMENTED BANKFULL POLIES WITH STREAM SHADE FIELD BACK INTO
#PERM MEM
arcpy.CopyFeatures_management(seg,final_segmented_AC)

arcpy.SelectLayerByAttribute_management(seg, "CLEAR_SELECTION")

#DELETE EXTRANEOUS FEATURE CLASSES
arcpy.Delete_management(streambuffer)
arcpy.DeleteFeatures_management(segmented_AC)
arcpy.Delete_management(zonalraster)
arcpy.Delete_management(seg)
arcpy.Delete_management(centroids)
arcpy.Delete_management(centroidswithvalues)
##arcpy.Delete_management(ONESANDZEROS)



