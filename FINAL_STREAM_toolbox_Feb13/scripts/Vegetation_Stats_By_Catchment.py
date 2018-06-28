import arcpy
import os
from arcpy import env
from arcpy.sa import *
from arcpy import da

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("spatial")

oldstreams = arcpy.GetParameterAsText(0)
catchments=arcpy.GetParameterAsText(1)
AC=arcpy.GetParameterAsText(2)
VEG_HEIGHT=arcpy.GetParameterAsText(3)
env.workspace=arcpy.GetParameterAsText(4)
naming=arcpy.GetParameterAsText(5)
in_mem=r"in_memory/"

streambuffer=os.path.join(env.workspace,naming+"_streambuffer")
catch_AC=os.path.join(env.workspace,naming+"_catch_AC")

final_segmented_AC=os.path.join(env.workspace,naming+"_polys_with_Veg_Stat")

#CLIP STREAM BUFFER TO CATCHMENTS
arcpy.Clip_analysis(catchments,AC, catch_AC)

#Make a vegetation raster for each of the three vegetation classes

#ground cover
groundraster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,0.49,1],[0.5,1000,0]]), "NODATA")
groundraster.save(os.path.join(env.workspace,naming+"_bareground"))

#understory
understoryraster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,0.49,0],[0.5,5,1],[5.1,1000,0]]), "NODATA")
understoryraster.save(os.path.join(env.workspace, naming+"_understory"))

#overstory
overstoryraster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,5,0],[5.1,1000,1]]), "NODATA")
overstoryraster.save(os.path.join(env.workspace, naming+"_overstory"))

#convert segmented polygons to rasters so that zonal statistics works correctly

##############################################################################
#uncomment this when testing scipt for bugs
##groundraster=os.path.join(env.workspace,naming+"groundraster")
##understoryraster=os.path.join(env.workspace, naming+"understoryraster")
##overstoryraster=os.path.join(env.workspace, naming+"overstoryraster")
###############################################################################

seg=arcpy.MakeFeatureLayer_management(catch_AC,"seg.lyr")

cell_size =float(arcpy.GetRasterProperties_management(VEG_HEIGHT, 'CELLSIZEX').getOutput(0))

#Get SUM FOR EACH CLASS BY CALCULATING THE SUM OF EACH 
groundzonal=ZonalStatistics(seg, "OBJECTID", groundraster, "SUM", "DATA")
underzonal=ZonalStatistics(seg, "OBJECTID", understoryraster,"SUM", "DATA")   
overzonal=ZonalStatistics(seg, "OBJECTID", overstoryraster, "SUM", "DATA")

#delete these fields later
arcpy.AddField_management(seg, "GROUND_COUNT", "FLOAT")
arcpy.AddField_management(seg, "UNDER_COUNT", "FLOAT")
arcpy.AddField_management(seg, "OVER_COUNT", "FLOAT")

#add field for each class
arcpy.AddField_management(seg, "Percent_Ground", "FLOAT")
arcpy.AddField_management(seg, "Percent_Understory", "FLOAT")
arcpy.AddField_management(seg, "Percent_Overstory", "FLOAT")

#create random points for each polygon
randos=arcpy.CreateRandomPoints_management(env.workspace, "centroids", seg,"#", 5)

#extract zonal values for each class to rando points

inRasterList=[[groundzonal,"Ground_Sum"],[underzonal,"Understory_Sum"],[overzonal,"Overstory_Sum"]]

ExtractMultiValuesToPoints(randos, inRasterList, "NONE")

search_fields = ["OID@","CID","Ground_Sum","Understory_Sum","Overstory_Sum"]
update_fields = ["OID@","SHAPE@AREA","GROUND_COUNT","UNDER_COUNT","OVER_COUNT",
                 "Percent_Ground","Percent_Understory","Percent_Overstory"]

modelist_ground=[]
modelist_under=[]
modelist_over=[]

#sort random points by cid so that cursor works
sorttable=os.path.join(env.workspace,naming+"_sorttable_")
arcpy.Sort_management(randos, sorttable, [["CID", "ASCENDING"]])

# makes search cursor and insert cursor into search/insert
with arcpy.da.SearchCursor(sorttable, (search_fields)) as search:

        for row in search:

            modelist_ground.append(row[2])
            modelist_under.append(row[3])
            modelist_over.append(row[4])

##            arcpy.AddMessage("length is "+str(len(modelist_ground)))

            #once it changes all of ones polygons points
            #are in list, get mode for each list
            if len(modelist_over or modelist_ground or modelist_under)==5:
                #remove nones from lists
                modelist_ground=[x for x in modelist_ground if x is not None]
                modelist_under=[x for x in modelist_under if x is not None]
                modelist_over=[x for x in modelist_over if x is not None]
                modelist_ground=[x for x in modelist_ground if x != -9999.0]
                modelist_under=[x for x in modelist_under if x != -9999.0]
                modelist_over=[x for x in modelist_over if x != -9999.0]

##                arcpy.AddMessage("gROUND list is "+str(modelist_ground))
##                arcpy.AddMessage("Understory list is "+str(modelist_under))
##                arcpy.AddMessage("Overstory list is "+str(modelist_over))

                #calculate modes
                mode_ground=max(set(modelist_ground), key=modelist_ground.count)
                mode_under=max(set(modelist_under), key=modelist_under.count)
                mode_over=max(set(modelist_over), key=modelist_over.count)
                
                #the mode is sumshaded for the polygon with the corresponding CID
                sum_ground=mode_ground
                sum_under=mode_under
                sum_over=mode_over

##                arcpy.AddMessage("POINTOID is "+str(str(row[1])))
##
##                arcpy.AddMessage("Mode ground is "+str(mode_ground))
##                arcpy.AddMessage("Mode understory is "+str(mode_under))
##                arcpy.AddMessage("Mode overstory is "+str(mode_over))
                
                pointOID=row[1]

                with arcpy.da.UpdateCursor(seg, (update_fields)) as update:

                    for roww in update:
                    
                        polyOID=roww[0]

                        #if pointOID IS polyOID

                        if (pointOID==polyOID):

                            areaofpoly=roww[1]
                            roww[2]=sum_ground
                            roww[3]=sum_under
                            roww[4]=sum_over

                            #calculate percent for each class
                            roww[5]=int(round(((sum_ground*(cell_size*cell_size))/areaofpoly)*100))
                            roww[6]=int(round(((sum_under*(cell_size*cell_size))/areaofpoly)*100))
                            roww[7]=int(round(((sum_over*(cell_size*cell_size))/areaofpoly)*100))
                            
                            update.updateRow(roww)

                            break

                #RESET MODELIST
                modelist_ground=[]
                modelist_under=[]
                modelist_over=[]

del search
del update

#COPY FEATURES BACK INTO PERM MEMORY
arcpy.CopyFeatures_management(seg,final_segmented_AC)

arcpy.Delete_management(sorttable)
arcpy.Delete_management(seg)
arcpy.Delete_management(streambuffer)
arcpy.Delete_management(catch_AC)
