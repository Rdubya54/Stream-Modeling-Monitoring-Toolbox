import arcpy
import os
from arcpy import env
from arcpy.sa import *
from arcpy import da

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("spatial")

catchments=arcpy.GetParameterAsText(0)
AC=arcpy.GetParameterAsText(1)
VEG_HEIGHT=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)
in_mem=r"in_memory/"

streambuffer=os.path.join(env.workspace,naming+"_streambuffer")
catch_AC=os.path.join(env.workspace,naming+"_catch_AC")

final_segmented_AC=os.path.join(env.workspace,naming+"_polys_with_Veg_Stat")

arcpy.AddMessage("Setting up overhead data...")

#CLIP STREAM BUFFER TO CATCHMENTS
arcpy.Clip_analysis(catchments, AC, catch_AC)

##Make a vegetation raster for each of the three vegetation classes

#ground cover
groundraster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,0.49,1],[0.5,1000,0]]), "NODATA")
groundraster.save(os.path.join(env.workspace,naming+"_bareground"))

#understory
understoryraster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,0.49,0],[0.5,5,1],[5.1,1000,0]]), "NODATA")
understoryraster.save(os.path.join(env.workspace, naming+"_understory"))

#overstory
overstoryraster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,5,0],[5.1,1000,1]]), "NODATA")
overstoryraster.save(os.path.join(env.workspace, naming+"_overstory"))

#all landcover. this one is just for visual purposes for end user. the other three rasters are needed to calculate
#veg stats effectively
all_raster = Reclassify(VEG_HEIGHT, "Value", RemapRange([[-1000,0.49,1],[0.5,5,2],[5.1,1000,3]]), "NODATA")
all_raster.save(os.path.join(env.workspace, naming+"_classified_veg"))

####convert segmented polygons to rasters so that zonal statistics works correctly
##
################################################################################
###uncomment this when testing scipt for bugs
####groundraster=os.path.join(env.workspace,naming+"groundraster")
####understoryraster=os.path.join(env.workspace, naming+"understoryraster")
####overstoryraster=os.path.join(env.workspace, naming+"overstoryraster")
#################################################################################
##
seg=arcpy.MakeFeatureLayer_management(catch_AC,"seg.lyr")
##
##
##    
cell_size =float(arcpy.GetRasterProperties_management(VEG_HEIGHT, 'CELLSIZEX').getOutput(0))
##
###Get SUM FOR EACH CLASS BY CALCULATING THE SUM OF EACH 
groundzonal=ZonalStatistics(seg, "OBJECTID", groundraster, "SUM", "DATA")
groundzonal.save(os.path.join(env.workspace,naming+"_ground_zonal"))
underzonal=ZonalStatistics(seg, "OBJECTID", understoryraster,"SUM", "DATA")
underzonal.save(os.path.join(env.workspace,naming+"_under_zonal"))
overzonal=ZonalStatistics(seg, "OBJECTID", overstoryraster, "SUM", "DATA")
overzonal.save(os.path.join(env.workspace,naming+"_over_zonal"))
##
##
##arcpy.AddMessage("Completed")
##
##
##
###delete these fields later
arcpy.AddField_management(seg, "GROUND_COUNT", "FLOAT")
arcpy.AddField_management(seg, "UNDER_COUNT", "FLOAT")
arcpy.AddField_management(seg, "OVER_COUNT", "FLOAT")

#add field for each class
arcpy.AddField_management(seg, "Percent_Ground", "FLOAT")
arcpy.AddField_management(seg, "Percent_Understory", "FLOAT")
arcpy.AddField_management(seg, "Percent_Overstory", "FLOAT")
##
##arcpy.CopyFeatures_management(seg,os.path.join(env.workspace,naming+"_seggg"))
#create random points for each polygon
points=os.path.join(env.workspace,naming+"_raster_points")

ground_zonal_resampled=os.path.join(env.workspace,naming+"_ground_zonal_resampled")
arcpy.Resample_management(groundzonal, ground_zonal_resampled, "30 30", "BILINEAR")
randos=arcpy.RasterToPoint_conversion(ground_zonal_resampled,points)
##
##
##arcpy.AddMessage("\t\tConverting buffers into raster...")
catchment_raster=os.path.join(env.workspace,naming+"_bufferrasterr")
arcpy.PolygonToRaster_conversion(catch_AC, "OBJECTID", catchment_raster, "#", "#", 1)

##randos=arcpy.CreateRandomPoints_management(env.workspace, "centroids", seg,"#", 25)
#extract zonal values for each class to rando points

projection = arcpy.Describe(AC).spatialReference
catchment_project=os.path.join(env.workspace,naming+"points_reproject")
arcpy.ProjectRaster_management(catchment_raster, catchment_project, projection)

desc = arcpy.Describe(AC)
ref = desc.spatialReference
##arcpy.AddMessage("input catchments are "+str(ref.Name))

desc = arcpy.Describe(underzonal)
ref = desc.spatialReference
##arcpy.AddMessage("Zonals are "+str(ref.Name))

desc = arcpy.Describe(overzonal)
ref = desc.spatialReference
##arcpy.AddMessage("Zonals are "+str(ref.Name))

desc = arcpy.Describe(groundzonal)
ref = desc.spatialReference
##arcpy.AddMessage("Zonals are "+str(ref.Name))

desc = arcpy.Describe(catchment_project)
ref = desc.spatialReference
##arcpy.AddMessage("catchemnt raster reprojected are "+str(ref.Name))

desc = arcpy.Describe(randos)
ref = desc.spatialReference
##arcpy.AddMessage("points are "+str(ref.Name))

inRasterList=[[groundzonal,"Ground_Sum"],[underzonal,"Understory_Sum"],[overzonal,"Overstory_Sum"],[catchment_project,"CATCHMENT_ID"]]
ExtractMultiValuesToPoints(randos, inRasterList, "NONE")

##field_names = [f.name for f in arcpy.ListFields(randos)]
##
##for f in field_names:
##    arcpy.AddMessage(str(f))

####search_fields = ["OID@","CID","Ground_Sum","Understory_Sum","Overstory_Sum"]
##arcpy.AddMessage("ZonalSt_"+naming[:4]+"1")
search_fields = ["OID@","CATCHMENT_ID","Ground_Sum","Understory_Sum","Overstory_Sum"]
##search_fields = ["OID@","CATCHMENT_ID","ZonalSt_"+naming[:4]+"1","ZonalSt_"+naming[:4]+"2","ZonalSt_"+naming[:4]+"3"]

update_fields = ["OID@","SHAPE@AREA","GROUND_COUNT","UNDER_COUNT","OVER_COUNT",
                 "Percent_Ground","Percent_Understory","Percent_Overstory"]

modelist_ground=[]
modelist_under=[]
modelist_over=[]

#sort random points by cid so that cursor works
sorttable=os.path.join(env.workspace,naming+"_sorttable_")
arcpy.Sort_management(randos, sorttable, [["CATCHMENT_ID", "ASCENDING"]])

CID_counter=0
previous_CID=None

arcpy.AddMessage("Calculating Veg Stats...")
# iterate through points sorted by catchment id
with arcpy.da.SearchCursor(sorttable, (search_fields)) as search:

        for row in search:

##            arcpy.AddMessage("CID is "+str(row[1]))

            if row[1]!=previous_CID or CID_counter>0:
                #append points to li st for mode calculation
                modelist_ground.append(row[2])
                modelist_under.append(row[3])
                modelist_over.append(row[4])

                CID_counter+=1
                                 
##                arcpy.AddMessage("gROUND list is "+str(row[2]))
##                arcpy.AddMessage("Understory list is "+str(row[3]))
##                arcpy.AddMessage("Overstory list is "+str(row[4]))
            
    ##            arcpy.AddMessage("length is "+str(len(modelist_ground)))

                #once it changes all of ones polygons points
                #are in list, get mode for each list
                if CID_counter==3:
                    #remove nones from lists
                    modelist_ground=[x for x in modelist_ground if x is not None]
                    modelist_under=[x for x in modelist_under if x is not None]
                    modelist_over=[x for x in modelist_over if x is not None]
                    modelist_ground=[x for x in modelist_ground if x != -9999.0]
                    modelist_under=[x for x in modelist_under if x != -9999.0]
                    modelist_over=[x for x in modelist_over if x != -9999.0]

##                    arcpy.AddMessage("CID is "+str(row[1]))
##                    arcpy.AddMessage("gROUND list is "+str(modelist_ground))
##                    arcpy.AddMessage("Understory list is "+str(modelist_under))
##                    arcpy.AddMessage("Overstory list is "+str(modelist_over))

                    #calculate modes
                    try:
                        mode_ground=max(set(modelist_ground), key=modelist_ground.count)

                    except:
                        mode_ground=None

                    try:
                        mode_under=max(set(modelist_under), key=modelist_under.count)

                    except:
                        mode_under=None

                    try:
                        mode_over=max(set(modelist_over), key=modelist_over.count)

                    except:
                        mode_over=None
                    
                    #the mode is sumshaded for the polygon with the corresponding CID
                    sum_ground=mode_ground
                    sum_under=mode_under
                    sum_over=mode_over

##                    arcpy.AddMessage("POINTOID is "+str(str(row[1])))
##
##                    arcpy.AddMessage("Mode ground is "+str(mode_ground))
##                    arcpy.AddMessage("Mode understory is "+str(mode_under))
##                    arcpy.AddMessage("Mode overstory is "+str(mode_over))
                    
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

##                                arcpy.AddMessage("sum ground is "+str(sum_ground))
##                                arcpy.AddMessage("sum under is "+str(sum_under))
##                                arcpy.AddMessage("sum over is "+str(sum_over))

                                #calculate percent for each class

                                try:
                                    roww[5]=int(round(((sum_ground*(cell_size*cell_size))/areaofpoly)*100))

                                except Exception as e:
                                    arcpy.AddMessage(str(e))
                                    roww[5]=None

                                try:
                                    roww[6]=int(round(((sum_under*(cell_size*cell_size))/areaofpoly)*100))

                                except:
                                    roww[6]=None

                                try:
                                    roww[7]=int(round(((sum_over*(cell_size*cell_size))/areaofpoly)*100))

                                except:
                                    roww[7]=None
                                
                                update.updateRow(roww)

                                break

                    #RESET MODELIST
                    modelist_ground=[]
                    modelist_under=[]
                    modelist_over=[]
                    CID_counter=0

del search
del update
##
###COPY FEATURES BACK INTO PERM MEMORY
arcpy.CopyFeatures_management(seg,final_segmented_AC)
##
arcpy.Delete_management(understoryraster)
arcpy.Delete_management(overstoryraster)
arcpy.Delete_management(groundraster)
arcpy.Delete_management(sorttable)
arcpy.Delete_management(seg)
arcpy.Delete_management(streambuffer)
arcpy.Delete_management(catch_AC)

arcpy.Delete_management(groundzonal)
arcpy.Delete_management(underzonal)
arcpy.Delete_management(overzonal)
arcpy.Delete_management(catchment_project)
arcpy.Delete_management(catchment_raster)
arcpy.Delete_management(ground_zonal_resampled)
arcpy.Delete_management(points)
