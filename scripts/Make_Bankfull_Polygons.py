import arcpy
import os
import string
import math
from arcpy import env
from arcpy.sa import *

env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#get parameters
slope=arcpy.GetParameterAsText(0)
streamlines=arcpy.GetParameterAsText(1)
ac_polygons=arcpy.GetParameterAsText(2)
env.workspace=arcpy.GetParameterAsText(3)
naming=arcpy.GetParameterAsText(4)

try:
        dump=arcpy.CreateFileGDB_management("C:/", "bankfull_dump.gdb")

except Exception as e:
        arcpy.AddMessage(str(e))

env.workspace="C:/bankfull_dump.gdb"

def check_resolution(slope):
##        arcpy.AddMessage("Checking resolution of raster... ")
        demrez = arcpy.GetRasterProperties_management(slope,"CELLSIZEX")
        demresx = demrez.getOutput(0)
        demrez = arcpy.GetRasterProperties_management(slope,"CELLSIZEX")
        demresy = demrez.getOutput(0)

        if demresx!="5" or demresy!="5":
                arcpy.AddMessage("Resampling raster to 5 5...")
                sloperesample=os.path.join(env.workspace,naming+"_5m_slope")
                arcpy.Resample_management(slope, sloperesample, "5 5", "BILINEAR")
                slope=sloperesample
                
        return slope
                
#this function is for converting python list into SQL queryable list
def convert_list(listt):
        #remove blanks from export list
        listt=[x for x in listt if x != [[]]]
        string=str(listt)
        almost=string.replace("[","")
        there=almost.replace("]","")
        fixed="("+there+")"

        return fixed

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

        except Exception as e:
                arcpy.AddMessage("ERROR received is "+str(e))
                arcpy.AddMessage("Failed to copy "+str(copy_address)+".")
                arcpy.AddMessage("This error usually occurs due to the Output gdb being open in ArcCatalog or another user having the gdb open.")
                arcpy.AddMessage("Be sure the output GDB is not open and no one else is using it.")
                arcpy.AddMessage("You can also try closing and reopening ArcMap.")
                arcpy.AddMessage("Tool may still be able to finish running, if not it will crash soon due to this error")

        return copy_address

#this function converts the necessary areas from raster to point
def extract_selection(streamlines,section_counter,slope):
##        arcpy.AddMessage("Buffering...")
        streambuffers=os.path.join(env.workspace,naming+"_buffers"+str(section_counter))
        arcpy.Buffer_analysis(streamlines, streambuffers, "25 Meters")

##        arcpy.AddMessage("Masking...")
        masked = ExtractByMask(slope, streambuffers)
        masked.save(os.path.join(env.workspace,naming+"_maskedraster"+str(section_counter)))
        
##        arcpy.AddMessage("Converting to points...")
        slope_points=os.path.join(env.workspace,naming+"_slopepoints"+str(section_counter))
        arcpy.RasterToPoint_conversion(masked, slope_points, "Value")

        return slope_points

#this function does all of the actual calculating needed to determine bankfull
def calculate_bankfull(points,ac_polygons):

        arcpy.AddField_management(points, "OG_OID", "INTEGER")
        arcpy.CalculateField_management (points, "OG_OID", "!OBJECTID!", "PYTHON_9.3")

        arcpy.Near_analysis(points,ac_polygons)
        
        #make point feature class of all points with next to no slope
##        arcpy.AddMessage("making no slopes")
        query="grid_code<=5"
        lyr=arcpy.MakeFeatureLayer_management(points,"nayer",query)
        copy_features(lyr,env.workspace,"no_slope_points")
        no_slope_points=os.path.join(env.workspace,"no_slope_points")

        #make point feature class of all points with at least some slope
##        arcpy.AddMessage("making slopes")
        query="grid_code>5"
        lyr=arcpy.MakeFeatureLayer_management(points,"payer",query)
        copy_features(lyr,env.workspace,"slope_points")
        slope_points=os.path.join(env.workspace,"slope_points")

        #start with a barebones bankfull. select all points within 2 point rows
        #of AC polygons.
##        arcpy.AddMessage("making skeleton")
        #problem is not the lack of requirement
        query="NEAR_DIST<=12.5"
        lyr=arcpy.MakeFeatureLayer_management(points,"dayer",query)
        copy_features(lyr,env.workspace,"barebones")
        bf_group=os.path.join(env.workspace,"barebones")

##        #MAKE LIST OF ALL POINTS IN BANKFULL SKELETON
##        arcpy.AddMessage("Making skeleton list")
        skeletonlist=[]
        search_fields=["OBJECTID"]

        with arcpy.da.SearchCursor(bf_group, search_fields) as search:
                for row in search:
                        skeletonlist.append(row[0])
                        
        i=0

        skeletonlist=convert_list(skeletonlist)

        barrier_group=no_slope_points

##        arcpy.AddMessage("adding field")
        arcpy.AddField_management(slope_points, "NO_SLOPE_DIST", "FLOAT")

        #this while loop needs to run as many times as there are
        #rows of points (depends on cell size and buffer size)
        #so that extracted area is fully analyzed
        while i<10:
            
##                arcpy.AddMessage("iteration is "+str(i))

        #ANALYSIS
                #perform near analysis on slope points to non slope barrier points
##                arcpy.AddMessage("performing Near analysis on slope ")
                arcpy.Near_analysis(slope_points,barrier_group)

                #copy the near dist field to a different field because there can only be one
                #NEAR_FID so otherwise the data will be lost on next near calculation
##                arcpy.AddMessage("calculating field")
                arcpy.CalculateField_management (slope_points, "NO_SLOPE_DIST", "!NEAR_DIST!", "PYTHON_9.3")
                        
                #perform near analysis on slope points to current bankfull
##                arcpy.AddMessage("performing Near analysis")
                arcpy.Near_analysis(slope_points,bf_group)


        #SELECTING AND EXPORTING


                if i==0:
                        query="NEAR_DIST<=7.071"

                else:
                        query="NEAR_DIST<=7.071 and NO_SLOPE_DIST>12.5"
                        
##                arcpy.AddMessage("making feature layer")
                bf_group=arcpy.MakeFeatureLayer_management(slope_points,"aaayer",query)
                copy_features(bf_group,env.workspace,"bf_group_after"+str(i))
                bf_group=os.path.join(env.workspace,"bf_group_after"+str(i))

                #add to barrier group by selecting all slope points that are within n meter
                #of previous barrier and have a high slope
                query="NEAR_DIST<=7.071 and NO_SLOPE_DIST<=7.071 and OG_OID NOT IN " +(skeletonlist)
                barrier_group=arcpy.MakeFeatureLayer_management(slope_points,"aaaayer",query)
                copy_features(barrier_group,env.workspace,"barrier_group"+str(i))
                barrier_group=os.path.join(env.workspace,"barrier_group"+str(i))

                #if not first iteration
                if i!=0:
                        #append old barrier points to barrier point feature class
                        old_barrier=os.path.join(env.workspace,"barrier_group"+str(i-1))
                        arcpy.Append_management([old_barrier],barrier_group)

                        old_bf_group=os.path.join(env.workspace,"bf_group_after"+str(i-1))
                        arcpy.Append_management([old_bf_group],bf_group)
                i+=1

        copy_features(bf_group,env.workspace, "section_bankfull")
                
        return bf_group,streamlines

#this function makes polygons into the points determined to be bankfull
def export_bankfull(bf_group,counter,halfway_polys,ac_polys,complete_polys):
##        arcpy.AddMessage("Exporting final copy")

        copy_features(bf_group,env.workspace, naming+"bankfull"+str(counter))

        if counter!=1:
                polys=os.path.join(env.workspace,naming+"bankfull_polys"+str(counter))
                arcpy.AggregatePoints_cartography(bf_group,polys, "7.5 meters")
                arcpy.Append_management([polys],halfway_polys)
                
        else:
                halfway_polys=os.path.join(env.workspace,naming+"bankfull_polys"+str(counter))
                arcpy.AggregatePoints_cartography(bf_group,halfway_polys, "7.5 meters")

        #use fill gaps function to fill in gaps in the data
        points=os.path.join(env.workspace,naming+"_slopepoints"+str(counter))
        

        if counter!=1:
                polys=fill_polygon_gaps(points,halfway_polys,ac_polys,counter)
                arcpy.Append_management([polys],complete_polys)

        else:
                complete_polys=fill_polygon_gaps(points,halfway_polys,ac_polys,counter)

        return halfway_polys,complete_polys

def fill_polygon_gaps(points,master_polys,ac_polys,counter):

        #calculate dist of points from ac polygons
        arcpy.Near_analysis(points,ac_polygons)

        #copy result into second field
        arcpy.AddField_management(points, "NEAR_DIST2", "FLOAT")
        arcpy.CalculateField_management (points, "NEAR_DIST2", "!NEAR_DIST!", "PYTHON_9.3")
        
        #calculate dist of points from bankfull polys
        arcpy.Near_analysis(points,master_polys)

        #select points that are adj to ac_polys, but not adj to bankfull polys
        query="NEAR_DIST2<=5 AND NEAR_DIST>0"
        lyr=arcpy.MakeFeatureLayer_management(points,"layera",query)

        #save these points into new feature class
        copy_features(lyr,env.workspace,naming+"gap_points"+str(counter))
        gap_points=os.path.join(env.workspace,naming+"gap_points"+str(counter))

        #calculate dist of gap points to other points
        arcpy.Near_analysis(points,gap_points)

        #select points that are adj to gap points and not in ac_polys
        query="NEAR_DIST<=7.071 AND NEAR_DIST2>0"
        lyr=arcpy.MakeFeatureLayer_management(points,"layerb",query)

        #save these points into new feature class
        copy_features(lyr,env.workspace, naming+"gap_points2"+str(counter))
        gap_points=os.path.join(env.workspace,naming+"gap_points2"+str(counter))

        #turn these points into polygons
        gap_polys=os.path.join(env.workspace,naming+"bankfull_polys_with_gaps"+str(counter))
        arcpy.AggregatePoints_cartography(gap_points,gap_polys, "7.5 meters")

        #merge these polygons with the master bankfull polygons
        filled_polys=os.path.join(env.workspace, naming+"bankfull_beforeagg"+str(counter))
        arcpy.Merge_management([gap_polys,master_polys], filled_polys)

        #aggregate polys
        final_polys=os.path.join(env.workspace,naming+"bankfull_polys_final"+str(counter))
        arcpy.AggregatePolygons_cartography(filled_polys, final_polys, "7.5 Meters")

        return final_polys

#######################################################################################################################################

#check resolution of slope. resolution must be 5x5 for this process to work
slope=check_resolution(slope)

##arcpy.AddMessage("making feature layer")        
#makes streamlines into feature layer so you can iterate through it
streamlines=arcpy.MakeFeatureLayer_management(streamlines,"slayer")
ac_polygons=arcpy.MakeFeatureLayer_management(ac_polygons,"layer")

##arcpy.AddMessage("getting count")   
streamlines_count = int(arcpy.GetCount_management(streamlines).getOutput(0))

counter=1
iteration_count=1
bankfull_list=[]

search_fields=["OBJECTID"]

with arcpy.da.SearchCursor(streamlines, (search_fields)) as search:
        for row in search:
                while streamlines_count>counter:
                        arcpy.AddMessage("Analyzing Area "+str(iteration_count)+" of " + str(int(math.ceil(float(streamlines_count)/float(3)))))
##                        arcpy.AddMessage("Beginning process for count:"+str(counter)+"-"+str(counter+2))
##                        arcpy.AddMessage("selecting lines")
##                        arcpy.AddMessage("OBJECTID >="+str(counter)+" AND OBJECTID<="+str(counter+2))
                        #select some streamlines

                        streamlines_select=arcpy.MakeFeatureLayer_management(streamlines,"layerp","OBJECTID >="+str(counter)+" AND OBJECTID<="+str(counter+2))

                        #extract points for selected streamlines
                        extracted_points=extract_selection(streamlines_select,counter,slope)

                        #select ac polygons corresponding to selected streamlines
##                        arcpy.AddMessage("selecting polygons")
                        arcpy.SelectLayerByLocation_management(ac_polygons, "intersect", streamlines_select)

                        #load points and polygons into calculate bankfull function
##                        arcpy.AddMessage("calculating bankfull")
                        calculate_bankfull(extracted_points,ac_polygons)

                        #take bf points, copy them into perm memory
                        bf_group=os.path.join(env.workspace,"section_bankfull")
                        copy_features(bf_group,env.workspace, "test")
##                        arcpy.AddMessage("exporting bankfull")

                        #load data into export bankfull to build polygons
                        if counter==1:
                                result=export_bankfull(bf_group,counter,None,ac_polygons,None)

                        else:
                                result=export_bankfull(bf_group,counter,result[0],ac_polygons,result[1])

                        #increment counter
                        counter+=3
                        iteration_count+=1
                        
arcpy.SelectLayerByAttribute_management(ac_polygons, "CLEAR_SELECTION")
#clean up bankfull polygon overextractions by getting rid of bankfull polys that are not adj to
#ac polys
close_bankfull=os.path.join(env.workspace,naming+"bankfull_polys_final1")
arcpy.Near_analysis(close_bankfull,ac_polygons)
query="NEAR_DIST=0"
lyr=arcpy.MakeFeatureLayer_management(close_bankfull,"layerz",query)

#copy final features into input gdb (the other one was just for dumping temporary data)
env.workspace=arcpy.GetParameterAsText(3) 
copy_features(lyr,env.workspace, naming+"_Bankfull_Polygons")

#clean up ac polygon overextractions by getting rid of ac polys that are not adj to
#bankfull polys
final_bankfull=os.path.join(env.workspace,naming+"_Bankfull_Polygons")
arcpy.Near_analysis(ac_polygons,final_bankfull)
query="NEAR_DIST=0"
lyr=arcpy.MakeFeatureLayer_management(ac_polygons,"layery",query)
copy_features(lyr,env.workspace, naming+"_Active_Channel_polys_FINAL")

#delete dump gdb created for dumping data for processing
#delete dump gdb created for dumping data for processing
dump="C:/bankfull_dump.gdb"

try:
        arcpy.Delete_management(dump)

except:
        arcpy.AddMessage("Completed running tool but failed to automatically delete gdb for trash data (C:/bankfull_dump.gdb)\
        None of the data is this gdb is needed anymore and it may be deleted manually.")

