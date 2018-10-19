import arcpy
import os
from arcpy import env
from arcpy.sa import *
from arcpy import da

arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)
arcpy.CheckOutExtension("spatial")

#this variable is for counting how many stream orders ranks have been written
#need this so code knows when to stop
TOTAL_STREAMS_IDed=0

def collect_point_info(points,mem_lines,order_rank,TOTAL_STREAMS_IDed):
    
##    arcpy.AddMessage("order_count "+str(order_rank))
    search_fields = ["SHAPE@", "LineOID", "Position"]
    update_fields = ["OID@","Stream_Order"]

##    arcpy.AddMessage("here")
    #iterate through points that were passed to funtion that met criteria
    with arcpy.da.SearchCursor(points, (search_fields)) as search:

        for row in search:
##            arcpy.AddMessage("here2")

            with arcpy.da.UpdateCursor(mem_lines, (update_fields)) as updatecur:

                #iterate through all lines and look for line that is paired with startng point
                for roww in updatecur:
                    
                    if roww[0]==row[1] and (roww[1]==None):

##                        arcpy.AddMessage("matched point "+str(row[1])+" with line "+str(roww[0]))

                        #if we aren't looking for 1st order streams
                        if order_rank!=1:
                            #isolate only the starting point that has found a line partner
                            arcpy.AddMessage("LineOID="+str(roww[0])+" AND Position=0")
                            paired_point=arcpy.MakeFeatureLayer_management(points,"paired_point_layer","LineOID="+str(roww[0])+" AND Position=0")
                            paired_point=arcpy.CopyFeatures_management(paired_point,os.path.join(env.workspace,"temp"+str(roww[0])))
                            mem_lines=arcpy.CopyFeatures_management(mem_lines,os.path.join(env.workspace,"templines"+str(roww[0])))
                            
                            #find lines nearest to it

                            #this is where its crashing
##                            arcpy.AddMessage("nearing")
                            arcpy.Near_analysis(mem_lines,paired_point)


##                            arcpy.AddMessage("nearing again")
                            mem_lines=arcpy.CopyFeatures_management(mem_lines,os.path.join(env.workspace,"lines_copy"+str(roww[0])))
                            arcpy.Near_analysis(mem_lines,paired_point)

                            #isolate lines that are adj to it (NEAR_DIST=0) and not the start of the line itself
                            adj_lines=arcpy.MakeFeatureLayer_management(mem_lines,"adj_lines_layer","NEAR_DIST=0 AND OBJECTID <> "+str(roww[0]))

##                            env.workspace="N:/Wortmr/throwaway.gdb"
##                            why=os.path.join(env.workspace,"whyy")
##                            arcpy.CopyFeatures_management(mem_lines,why)
                            
                            order_rank_list=[]

                            with arcpy.da.SearchCursor(adj_lines, (update_fields)) as search_lines:

                                for rowww in search_lines:
##                                    arcpy.AddMessage("adding "+str(rowww[1]))
                                    order_rank_list.append(rowww[1])

##                            arcpy.AddMessage("order rank list is "+str(order_rank_list))

                            #if all the adj ranks are known
                            if None not in order_rank_list:
                                start=order_rank_list[0]

                                #check to see if all elements in list are the same
                                is_list_uniform=all(x==order_rank_list[0] for x in order_rank_list)

                                #if they are all the same AND THERE'S MORE THAN ONE, its time to move up to the next order rank
                                if is_list_uniform==True and (len(order_rank_list)>1):
                                    roww[1]=max(order_rank_list)+1
                                    
                                #if there are multiple different adj ranks, write in the highest,
                                #this is the case where the same stream order rank is continuing
                                else:
                                    roww[1]=max(order_rank_list)

                                TOTAL_STREAMS_IDed+=1

                        #if we are looking for first order streams     
                        else:        
                            roww[1]=order_rank
                            TOTAL_STREAMS_IDed+=1
                            
                        updatecur.updateRow(roww)

    return TOTAL_STREAMS_IDed
        
mem_lines = arcpy.GetParameterAsText(0)
env.workspace=arcpy.env.scratchGDB
##env.workspace="N:/Wortmr/throwaway.gdb"

mem_lines=arcpy.MakeFeatureLayer_management(mem_lines, "copy.lyr")

#count number of streams so code knows when to stop
countingstreams=arcpy.GetCount_management(mem_lines)
streamcount=int(countingstreams.getOutput(0))
arcpy.AddMessage("Tool will finish after all streamlines are classifed.")
##arcpy.AddMessage(str(streamcount)+" Total Streamlines in Feature Class")

##env.workspace="N:/Wortmr/throwaway.gdb"

search_fields = ["SHAPE@", "OID@"]
insert_fields = ["SHAPE@", "LineOID", "Position"]

#make sure Stream Order field doesnt already exist
field_names = [f.name for f in arcpy.ListFields(mem_lines)]

#if it does, delete and make a new one
if "Stream_Order" in field_names:
##    arcpy.AddMessage("Deleting field name")
    arcpy.DeleteField_management(mem_lines,"Stream_Order")
    
arcpy.AddField_management(mem_lines, "Stream_Order", "LONG")

##mem_lines=arcpy.MakeFeatureLayer_management(mem_lines,"lines_layer")
mem_point = arcpy.CreateFeatureclass_management(r"in_memory", "points_in_memory", "POINT", "", "DISABLED", "DISABLED", mem_lines)

arcpy.AddField_management(mem_point, "LineOID", "LONG")
arcpy.AddField_management(mem_point, "Position", "LONG")

#place endpoints on every line
# makes search cursor and insert cursor into search/insert
with arcpy.da.SearchCursor(mem_lines, (search_fields)) as search:
    with arcpy.da.InsertCursor(mem_point, (insert_fields)) as insert:
        for row in search:
            
                #line geom is shape in search fields
                line_geom = row[0]
                
                #oid is OID@ in search fields            
                oid = str(row[1])

                #creates a point at the start and end of line for final point that is less then the userdistance away
                start_of_line = arcpy.PointGeometry(line_geom.firstPoint)
                end_of_line = arcpy.PointGeometry(line_geom.lastPoint)

                insert.insertRow((start_of_line, oid,0))
                insert.insertRow((end_of_line, oid,1))

del search
del insert

#select all start of line point
start_points=arcpy.MakeFeatureLayer_management(mem_point,"start_points_layer","Position=0")

#select all end of line points
end_points=arcpy.MakeFeatureLayer_management(mem_point,"end_points_layer","Position=1")
                                 
#calculate dist start points are from end points
arcpy.Near_analysis(start_points,end_points)

######################FIRST ORDER#####################################################################
#select only start points where NEAR_DIST to end points is >0
first_order_points=arcpy.MakeFeatureLayer_management(start_points,"first_order_points","NEAR_DIST>0")

order_rank=1

TOTAL_STREAMS_IDed=collect_point_info(first_order_points,mem_lines,order_rank,TOTAL_STREAMS_IDed)
previous_TOTAL_STREAMS_IDed=None

order_rank+=1
old_string="None"
string=str(TOTAL_STREAMS_IDed)+" of "+str(streamcount)+" streams classified"

###########################################################################################################

while TOTAL_STREAMS_IDed<streamcount:

    #this is for when line is stuck in an infinite loop due to errors in the line network

    if string!=old_string:
        arcpy.AddMessage(string)
        old_string=string

    #this is all for when code still hasn't seen all the lines yet. 30 is kind of an arbitary number.
    #I was just using a value high enough that I was sure by then all streams would have been looked at once.
    if order_rank<30:

        #select only lines that have NEAR DIST OF 0 to two or more firs order endpoints
        ####make first order stream only layer
        arcpy.AddMessage("Making feature layer selection")
        past_order_streams=arcpy.MakeFeatureLayer_management(mem_lines,"first_order_lines","Stream_Order="+str(order_rank-1))

        ###calculate dist of starting points from selected streams
##        arcpy.AddMessage("doing near")
        arcpy.Near_analysis(start_points,past_order_streams)
        ####select only points that are starting points and are adj to first order streams
##        arcpy.AddMessage("selecting other")
        order_rank_points=arcpy.MakeFeatureLayer_management(start_points,"order_rank_start","NEAR_DIST=0")

##        arcpy.AddMessage("lauching function")
        TOTAL_STREAMS_IDed=collect_point_info(order_rank_points,mem_lines,order_rank,TOTAL_STREAMS_IDed)

    #this is just for when after code is done iterating through all the lines once. This is where goes through
    #and fills in the blanks that it left due to not haveing a enough information
    else:
        if previous_TOTAL_STREAMS_IDed!=TOTAL_STREAMS_IDed:
            #select only lines with still unknown stream order
            null_streams=arcpy.MakeFeatureLayer_management(mem_lines,"first_order_lines","Stream_Order IS NULL")
            ###calculate dist of starting points from selected streams

            try:
                arcpy.Near_analysis(start_points,null_streams)

            except arcpy.ExecuteError:

                msgs = arcpy.GetMessages(2) 

                # Return tool error messages for use with a script tool 
                #
                arcpy.AddError(msgs)
                
                start_points=arcpy.CopyFeatures_management(start_points,"copy.lyr")
                arcpy.Near_analysis(start_points,null_streams)

            ####select only points that are starting points and are adj to null order streams
            order_rank_points=arcpy.MakeFeatureLayer_management(start_points,"order_rank_start","NEAR_DIST=0")

            previous_TOTAL_STREAMS_IDed=TOTAL_STREAMS_IDed
            TOTAL_STREAMS_IDed=collect_point_info(order_rank_points,mem_lines,order_rank,TOTAL_STREAMS_IDed)

        #this is for catching situations where user has added lines to network incorrectly, causing code to get stuck in
        #infinte loop
        else:
            arcpy.AddMessage("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
            arcpy.AddMessage("LINE NETWORK ERROR!")
            arcpy.AddMessage("One or more of the edited input lines were not drawn according to the rules outlined in the Stream Modeling Manual.")
            arcpy.AddMessage("To find out which ones are incorrect, look in the Stream_Order field in the input line network's attribute table.")
            arcpy.AddMessage("The lines that are a problem will have a NULL value.")
            arcpy.AddMessage("However, not all of the NULL value lines are problem lines. Some will only be NULL because they were adjacent to problem lines.")
            arcpy.AddMessage("Also, only lines that the user added will be possible problem lines.")
            arcpy.AddMessage("Narrow your search for the problem lines according to this criteria.")
            arcpy.AddMessage("The problem lines will need to be redrawn according to the guidelines in the Stream Modeling Manual.")
            arcpy.AddMessage("Fix the problem lines and then run this tool again.")
            import sys
            sys.exit()

    order_rank+=1
    string=str(TOTAL_STREAMS_IDed)+" of "+str(streamcount)+" streams classified"
    
##output_lines=os.path.join(env.workspace,"sample_lines")
##arcpy.CopyFeatures_management(mem_lines,output_lines)
##arcpy.CopyFeatures_management(mem_point,output_points)
