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
thwag_network_lyr=arcpy.GetParameterAsText(0)
env.workspace=arcpy.GetParameterAsText(1)
naming="test"

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

def convert_list(listt):
        #remove blanks from export list
        listt=[x for x in listt if x != [[]]]
        string=str(listt)
        almost=string.replace("[","")
        there=almost.replace("]","")
        fixed="("+there+")"

        return fixed

#make pgdb version for easy distinct query (this cannot be done in gdb)
pgdb=arcpy.CreatePersonalGDB_management("Q:/", "dummy.mdb")
##env.workspace=pgdb
##thwag_network_pgdb=os.path.join(pgdb,naming+"thwag_network")
arcpy.CopyFeatures_management(thwag_network_lyr,"Q:/dummy.mdb/thwag_network")
pgdb_points="Q:/dummy.mdb/thwag_network"

#select points that are from buffers where more then 1 point was selected due to
#more than one point possessing the minimum elevation
distinct_query="[oneline_halfm_test2_bufferraster] IN \
(SELECT [oneline_halfm_test2_bufferraster] \
FROM thwag_network \
GROUP BY [oneline_halfm_test2_bufferraster] HAVING \
Count( [oneline_halfm_test2_bufferraster] )>1)"
duplicates_lyr=arcpy.MakeFeatureLayer_management(pgdb_points,"duplicates.lyr", distinct_query)
duplicates=os.path.join(env.workspace,naming+"_duplicates")
arcpy.CopyFeatures_management(duplicates_lyr,duplicates)

duplicate_list=set()
search_fields=["OID@","oneline_halfm_test2_bufferraster","pointid"]
#create duplicates list by iterating through duplicate point lyr and appending buffer raster to duplicate list
with arcpy.da.SearchCursor(duplicates_lyr, (search_fields)) as search:
        for row in search:
                duplicate_list.add(row[1])

duplicates_sorted=os.path.join(env.workspace,naming+"_duplicates_sorted")
arcpy.Sort_management(duplicates, duplicates_sorted, [["oneline_halfm_test2_bufferraster"]])

value=0

#sort line by bufferraster ASCENDING
thwag_network_sorted=os.path.join(env.workspace,naming+"sorted_thwag")
arcpy.Sort_management(thwag_network_lyr, thwag_network_sorted, [["oneline_halfm_test2_bufferraster", "ASCENDING"]])

dont_delete_list=set()

#iterate through sorted points
with arcpy.da.SearchCursor(thwag_network_sorted, (search_fields)) as search:
        for row in search:

                #if buffer raster value is not a repeat
                if row[1]!=value:

                        #if point is not first, build line sorted properly
                        if value!=0:

                                #set value equal to bufferaster
                                value=row[1]

                                arcpy.AddMessage("value is "+str(value))

                                #if point is a duplicate buffer
                                if row[1] in duplicate_list:
                                        arcpy.AddMessage("duplicate detected")

                                        #create layer of only points that have been iterated through
                                        working_points=arcpy.MakeFeatureLayer_management(thwag_network_lyr, "workling_points.lyr","oneline_halfm_test2_bufferraster>="+str(value))
                                        working_line=os.path.join(env.workspace,naming+"working_line")
                                        arcpy.AddMessage("building line")
                                        arcpy.PointsToLine_management(working_points, working_line, "NEAR_FID", "oneline_halfm_test2_bufferraster")

                                        #select all points with in same buffer
                                        dup_points=arcpy.MakeFeatureLayer_management(thwag_network_lyr,"dup_points.lyr","oneline_halfm_test2_bufferraster="+str(value))
                                        #calcuate dist of duplicates from working line
                                        arcpy.AddMessage("nearing")
                                        arcpy.Near_analysis(dup_points,working_line)

                                        arcpy.AddMessage("iterating through duplicates")
                                        #iterate through dup points and find one with min dist
                                        min_dist=99999999999999
                                        search_fields2=["pointid","NEAR_DIST"]
                                        with arcpy.da.SearchCursor(dup_points, (search_fields2)) as search:
                                                for row in search:
                                                        if min_dist>row[1]:
                                                                min_dist=row[1]
                                                                min_id=row[0]

                                        #append min_id to don't delte list
                                        arcpy.AddMessage("dont delete "+str(min_id))
                                        dont_delete_list.add(min_id)

                                #if point is not a dupolicate
                                else:
                                        #append point id to don't delte list
                                        arcpy.AddMessage("dont delete "+str(row[2]))
                                        dont_delete_list.add(row[2])


                        #else if point is first in iteration
                        else:
                                arcpy.AddMessage("in first point")
                                #set value equal to bufferaster
                                value=row[1]
                                
                                #append point id to don't delte list
                                arcpy.AddMessage("dont delete "+str(row[2]))
                                dont_delete_list.add(row[2])                        
                                                        

#convert list to useable sql list
dont_delete_list=convert_list(dont_delete_list)

points_wo_dups_lyr=arcpy.MakeFeatureLayer_management(thwag_network_lyr,"remove_nondups.lyr","pointid IN "+dont_delete_list)

points_wo_dups=os.path.join(env.workspace,naming+"points_wo_dups")
arcpy.CopyFeatures_management(points_wo_dups_lyr,points_wo_dups)
