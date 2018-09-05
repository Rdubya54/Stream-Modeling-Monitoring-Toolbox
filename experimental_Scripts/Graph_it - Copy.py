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

def listsum(numList):
    theSum = 0
    for i in numList:
        theSum = theSum + i
    return theSum

def convert_list(listt):
        #remove blanks from export list
        listt=[x for x in listt if x != [[]]]
        string=str(listt)
        almost=string.replace("[","")
        there=almost.replace("]","")
        fixed="("+there+")"

        return fixed

def find_two_highest_runs(line_list,append_list):

    summ_list=[]
    master_key_list=[]

    #iterate through list of run dicts
    for dicton in line_list:

        summ=0
        numbercounter=0
        key_list=[]

        #in each run dict find the sum of slopes and make a key list
        for key, value in dicton.iteritems():
            summ+=value
            numbercounter+=1
            key_list.append(key)

        #append the key list and average list to master lists
        try:
            summ_list.append(summ/numbercounter)
            master_key_list.append(key_list)
        except:
            pass

    index_counter=0
    maxx_slope=0
    runner_up_slope=0
    
    for summ in summ_list:

        arcpy.AddMessage("summ is  "+str(summ))

        if summ>maxx_slope:
            #if there is new max slope, push the old one to runner up
            if maxx_slope>runner_up_slope and maxx_slope!=0:
                runner_up_index=top_index
                runner_up_slope=maxx_slope
                
            maxx_slope=summ    
            top_index=index_counter

        elif summ>runner_up_slope:
            runner_up_index=index_counter
            runner_up_slope=maxx_slope

        index_counter+=1

    top_ids=master_key_list[top_index]
    runner_up_ids=master_key_list[runner_up_index]

    append_list.append(top_ids)
    append_list.append(runner_up_ids)

    return append_list
#get parameters
cross_section_many_points=arcpy.GetParameterAsText(0)
env.workspace=arcpy.GetParameterAsText(1)
naming=arcpy.GetParameterAsText(2)

search_fields = ["SHAPE@", "PointOID","LineOID", "Value","Hinkson_Slope","OID@"]

line_dict=dict()
running=False
line_list=[]
append_list=[]
prev_oid=1

#iterate thorugh cross sectin points
with arcpy.da.SearchCursor(cross_section_many_points, (search_fields)) as search:
        for row in search:

            arcpy.AddMessage("Oid is "+str(row[1]))
            #if not on a new cross section line
            if row[1]==prev_oid:

                #if point has large enough value to be slope, flip the switch and
                #strat a new run dict
                if row[4]>=5 and running==False:
                    running=True
                    run_dict=dict()
                    run_dict[row[5]]=row[4]
                    
                #if point is another run point and run already started
                elif running==True and row[4]>=5:
                    run_dict[row[5]]=row[4]

                #if run is over
                elif running==True and row[4]<5:
                    running=False
                    line_list.append(run_dict)

            #if on a new cross section line
            else:

                #if last line was still on run
                if running==True:
                    line_list.append(run_dict)

                running==False
                run_dict=dict()
                
                append_list=find_two_highest_runs(line_list,append_list)
                arcpy.AddMessage("append list is "+str(append_list))

                line_list=[]
                #now carry on as usual
                #if point has large enough value to be slope, flip the switch and
                #strat a new run dict
                if row[4]>=5 and running==False:
                    running=True
                    run_dict=dict()
                    run_dict[row[5]]=row[4]
                    
                #if point is another run point and run already started
                elif running==True and row[4]>=5:
                    run_dict[row[5]]=row[4]

                #if run is over
                elif running==True and row[4]<5:
                    running=False
                    line_list.append(run_dict)

            prev_oid=row[1]

append_list=convert_list(append_list)

arcpy.AddMessage("summ is  "+append_list)
lyr=arcpy.MakeFeatureLayer_management(cross_section_many_points,"slayer","OBJECTID IN "+append_list)

bf_points=os.path.join(env.workspace,naming+"bf_points")
arcpy.CopyFeatures_management(lyr,bf_points)
    
##with arcpy.da.SearchCursor(cross_section_many_points, (search_fields)) as search:
##        for row in search:
##                arcpy.AddMessage("adding points")
##                if row[1]==1:
##                    pass
##                
##                elif row[1]==2:
##                     objects.append(row[4])
##                     distance.append(row[3])
##
##                elif row[1]!=1 or row[1]!=2:
##                        break
##
##arcpy.AddMessage("making graph")
##import matplotlib.pyplot as plt; plt.rcdefaults()
##import numpy as np
##import matplotlib.pyplot as plt
##import matplotlib.ticker as ticker
##
##
##y_pos = np.arange(len(objects))
##
##objects_reduced=[i for i in objects]
####objects_reduced=np.arrange([500,600,700,800,900])
## 
##plt.bar(distance, objects_reduced, 2, -2000, align='edge', alpha=0.5)
##plt.yticks(y_pos, objects)
##plt.xlabel('dist')
##plt.ylabel('elevation')
##plt.title('Cross Gradeint')
##
##
##ax = plt.axes()
##ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
##ax.xaxis.set_minor_locator(ticker.MultipleLocator(5))

##plt.show()



