#Stephen Skilton
#CPLN 673 - Geospatial Software Development
#Final Project
#December 18, 2015

"""

This script takes 4 inputs and from that calculates (where it can) the area of
front and back yards of every house and places them into two fields in a new parcels layers.

To do this the script does the following:

1.  Takes the zoning layer and filters out only the houses and parcels that are single family
detached. (It can only calculate when there are side yards, and we don't need non-residential.)

2. It turns the parcel into a pefect rectangle using a bounding box.
(Thus yard size is only an approximation)

3.  It determines where the front, back, and side yards are in relation to a road.
(This only works on single loaded lots, and not corner lots.)

4.  It determines where the front and back yards begin based on the placement of the house.

5. It cuts the parcel, measures the yards and incorporates the area back into the attribute table
of a new shapefile.

The final outputs are the houses and yards processed, and the new parcel file.


Areas for improvement:

1.  Calculating attached homes that may not have side yards.
2.  Calulating double loaded and corner lots.
3.  Improving the calculation from the boudning box approximation, and dealing with irregularly
shaped lots that are less accurately calculted with this tool.
4.  Moving pieces of the code into separate modules (such as the first part that picks certain zoning codes.)


Final goals:

1.  The ability to measure the yards for any home in Philadelphia.
2.  Incorporating this tool  as one factor into a subdivision/redevelopment susceptibility analysis
for Chestnut Hill.


Inputs:

1. buildings    - feature layer - input
2. zoning       - feature layer - input
3. parcels      - feature layer - input
4. roads        - feature layer - input
5. outputdirector - TestData in the data folder

One more caveat: This script was run and tested using a small test set of 4 atttached homes and 2 detached, with one road
and mostly rectangular parcels.


All of the output file paths need work first. And all the temp files need to be cleaned up.
Also it would be good to remove the line that deletes the yards that are cut in half.
"""



import sys, os, string, math, arcpy, traceback
arcpy.env.overwriteOutput = True

try:



    from arcpy import env

#Select your 4 input layers


    buildings               = arcpy.GetParameterAsText(0)
    zoning                  = arcpy.GetParameterAsText(1)
    parcels                 = arcpy.GetParameterAsText(2)
    roads                   = arcpy.GetParameterAsText(3)
    outputdirectory         = arcpy.GetParameterAsText(4)

#set up some ooutputs
    arcpy.env.workspace = outputdirectory
    outfc = r"tempbuildings.shp"
    outfc1 = r"/TestData"
    outtestparcels = r"testparcels1.shp"
    outtestbldgs = r"testbldgs1"
    outbox = r"parcelbox.shp"
    targetFeatures = buildings 
    joinFeatures = zoning 
     
#Join and export zoning with buildings and filter residential detached.
    arcpy.SpatialJoin_analysis(buildings , zoning, outfc, "#", "#")


    delimitedField = arcpy.AddFieldDelimiters(outfc, "LONG_CODE")
    expression = delimitedField + "LIKE 'RSD%'"
    arcpy.FeatureClassToFeatureClass_conversion(outfc, outfc1,outtestbldgs, expression) 


#Now grab the matching parcels

    testparcels1 = r"/testparcels1.shp"
    testbldgs1 = r"/testbldgs1.shp"
    testbldgs = r"/testbldgs1.shp"
    arcpy.SpatialJoin_analysis(parcels, testbldgs, outtestparcels, "#", "KEEP_COMMON","#", "CONTAINS")
    arcpy.Delete_management(r"/tempbuildings.shp")


#Good, now lets add just the buidling and parcels we are working with to the map.

    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
    newlayer = arcpy.mapping.Layer(testparcels1)
    newlayer1 = arcpy.mapping.Layer(testbldgs1)
    arcpy.mapping.AddLayer(df, newlayer,"TOP")
    arcpy.mapping.AddLayer(df, newlayer1,"TOP")


#Parcels are weird shapes and I need just 4 sides so using a bounding box.

    arcpy.MinimumBoundingGeometry_management(outtestparcels , outbox, 
                                             "RECTANGLE_BY_WIDTH", "NONE")






#Splitting the box into 4 sides that will be: front, back and sides.
#I also need the center of the sides to figure out relation to road.

    tempPolyToLine = r"/temppolytoline.shp"
    arcpy.PolygonToLine_management(outbox, 
                               tempPolyToLine,
                               "IGNORE_NEIGHBORS")
    tempSplitLines = r"/tempSplitLines.shp"
    arcpy.SplitLine_management(tempPolyToLine, tempSplitLines)
    splitLineCenter = r"/splitLineCenter.shp"
    arcpy.FeatureToPoint_management(tempSplitLines, splitLineCenter, "INSIDE")
    buildingsCenter = r"/buildingsCenter.shp"
    arcpy.FeatureToPoint_management(outtestbldgs, buildingsCenter, "INSIDE")

    splitLineCenter = r"/splitLineCenter.shp"
    #delete above line after testing

#Ok not which is closest/furtherst from the road?
    arcpy.Near_analysis(splitLineCenter, roads)
    arcpy.AddField_management(splitLineCenter, "max", "LONG")
    tempsplitLineCenterDist = r"/tempsplitLineCenterDist.shp"
    arcpy.Sort_management(splitLineCenter, tempsplitLineCenterDist, [["TARGET_FID", "ASCENDING"]])


#This part is tricky, I need to group the ones from each parcel and rank their distance,
#Then tag them all in the attribute table. 3 = front, 0 = sides, 1 = back
#Code is repreated twice for front and back.

    ## make a list of unique area_id values
    LineList = []       
    with arcpy.da.SearchCursor(tempsplitLineCenterDist, ["TARGET_FID"]) as cur1:
        for row1 in cur1:
            if row1[0] not in LineList:
                LineList.append(row1[0])

    ## for every area_id, make a list of unique height values and get the highest value
    for i in LineList:
        DistList = []
        where = """{} = {}""".format("TARGET_FID", i)    # or use this line if the area_id field is numeric.
        with arcpy.da.SearchCursor(tempsplitLineCenterDist, ["NEAR_DIST"], where) as cur2:
            for row2 in cur2:
                if row2[0] not in DistList:
                    DistList.append(row2[0])
        DistList.sort()
        max_dist = DistList[-1]

        ## select the highest value for every area_id and assign the value '1' to its 'highest' field
        where2 = """{} = {} AND {} = {}""".format("TARGET_FID", i, "NEAR_DIST", max_dist) # if area_id is numeric.
#       where2 = """{} = '{}' AND {} = {}""".format("area_id", i, "height", max_height) # if area_id is numeric.


        with arcpy.da.UpdateCursor(tempsplitLineCenterDist, ["max"], where2) as cur3:
            for row3 in cur3:
                row3[0] = 1
                cur3.updateRow(row3)
                break   # this will tag only 1 of the highest points for every area_id.
                        # If you want to tag all highest points, remove this line.


    ## make a list of unique area_id values
    LineList = []       
    with arcpy.da.SearchCursor(tempsplitLineCenterDist, ["TARGET_FID"]) as cur1:
        for row1 in cur1:
            if row1[0] not in LineList:
                LineList.append(row1[0])

    ## for every area_id, make a list of unique height values and get the highest value
    for i in LineList:
        DistList = []
        where = """{} = {}""".format("TARGET_FID", i)    # or use this line if the area_id field is numeric.
        with arcpy.da.SearchCursor(tempsplitLineCenterDist, ["NEAR_DIST"], where) as cur2:
            for row2 in cur2:
                if row2[0] not in DistList:
                    DistList.append(row2[0])
        DistList.sort(reverse=True)
        max_dist = DistList[-1]

        ## select the highest value for every area_id and assign the value '1' to its 'highest' field
        where2 = """{} = {} AND {} = {}""".format("TARGET_FID", i, "NEAR_DIST", max_dist) # if area_id is numeric.
#       where2 = """{} = '{}' AND {} = {}""".format("area_id", i, "height", max_height) # if area_id is numeric.


        with arcpy.da.UpdateCursor(tempsplitLineCenterDist, ["max"], where2) as cur3:
            for row3 in cur3:
                row3[0] = 3
                cur3.updateRow(row3)
                break   # this will tag only 1 of the highest points for every area_id.
                        # If you want to tag all highest points, remove this line.


#Ok now I know where the side yards are. I just need to draw lines from the sides, to the center
#of the house. This will create front and back yard boundaries within the parcel.

#Fileter out the side yards into their own shapefile.
    tempsideyards = outputdirectory
    tempsidename = "tempsideyards"
    delimitedField = arcpy.AddFieldDelimiters(tempsplitLineCenterDist, "max")
    expression = delimitedField + "= 0"
    arcpy.FeatureClassToFeatureClass_conversion(tempsplitLineCenterDist, tempsideyards,tempsidename, expression) 
    tempsideyardsfull = r"/tempsideyards.shp"
    tempsideyardsfull1 = r"/tempsideyards1.shp"
    arcpy.SpatialJoin_analysis(tempSplitLines,tempsideyardsfull, tempsideyardsfull1, "#", "KEEP_COMMON")

    buildingsCenter1 = r"/buildingsCenter1.shp"
    arcpy.SpatialJoin_analysis(buildingsCenter,outtestparcels, buildingsCenter1, "#", "KEEP_COMMON")


#This is a workaraound. Evventually I need to change this to near distance for each side, and its
#corresponding building center (by parcel ID) but the centroid of each side will do for now as
#a placeholder.


    tempsideyardcenter = r"/tempsideyardcenter.shp"
    arcpy.SpatialJoin_analysis(splitLineCenter,tempsideyardsfull1, tempsideyardcenter, "#", "KEEP_COMMON")

#Draw lines from sides to center.
    arcpy.AddXY_management(tempsideyardcenter)
    arcpy.AddXY_management(buildingsCenter1)
    arcpy.JoinField_management(tempsideyardcenter, "PARCEL", buildingsCenter1, "PARCEL", ["POINT_X","POINT_Y"])
    temptempsideyardcenter = r"/tempsideyardcenter.dbf"



#Now cut the yards into separate shapes that can be measured.

    cutlines = "/tempcutlines.shp"
    arcpy.XYToLine_management(temptempsideyardcenter,cutlines, "POINT_X", "POINT_Y", "POINT_X_1", "POINT_Y_1")
    tempdirtyyards = "/tempdirtyyards.shp"
    arcpy.FeatureToPolygon_management([outbox,cutlines],tempdirtyyards)

    tempdirtyyards1 = "/tempdirtyyards1.shp"
    arcpy.Erase_analysis(tempdirtyyards,testbldgs1, tempdirtyyards1)


    arcpy.AddField_management(tempdirtyyards,"area","Double")
    expression1 = "{0}".format("!SHAPE.area@SQUAREFEET!")        
    arcpy.CalculateField_management(tempdirtyyards1, "area", expression1, "PYTHON", )


#The bounding boxes made some really small overlapping shapes that I need to clean up.
    tempcleanyardfolder = outputdirectory
    tempcleanyardname = "tempcleanyards"
    delimitedField = arcpy.AddFieldDelimiters(tempdirtyyards1, "AREA")
    expression = delimitedField + "> 15"
    arcpy.FeatureClassToFeatureClass_conversion(tempdirtyyards1,tempcleanyardfolder,tempcleanyardname, expression) 
    tempcleanyard = r"/tempcleanyards.shp"




    temptagbyardfolder = outputdirectory
    temptagbyardfile = "temptagbyard"
    


#Phew, almost done. Now I need to just calculate the area, and tag which is front and back (using the 3, 0, 1 categories
#I created earlier with the parcel box line boundaries.



    delimitedField = arcpy.AddFieldDelimiters(tempsplitLineCenterDist, "max")
    expression = delimitedField + "= 1"
    arcpy.FeatureClassToFeatureClass_conversion(tempsplitLineCenterDist, temptagbyardfolder,temptagbyardfile, expression) 
    temptagbyard = r"/temptagbyard.shp"

    tempcleanbyard = r"/tempcleanbyards.shp"
    arcpy.SpatialJoin_analysis(tempcleanyard,temptagbyard, tempcleanbyard, "#", "KEEP_COMMON")


    arcpy.AddField_management(tempcleanbyard,"Byard","Double")
    delimitedField1 = arcpy.AddFieldDelimiters(tempcleanbyard, "!AREA!")
    arcpy.CalculateField_management(tempcleanbyard, "Byard", delimitedField1,"PYTHON_9.3")
    tempcleanbyardpt = r"/tempcleanbyardpt.shp"
    arcpy.FeatureToPoint_management(tempcleanbyard, tempcleanbyardpt, "CENTROID")

    temptagfyardfolder = r"/TestData"
    temptagfyardfile = "temptagfyard"
    
    
    delimitedField = arcpy.AddFieldDelimiters(tempsplitLineCenterDist, "max")
    expression = delimitedField + "= 3"
    arcpy.FeatureClassToFeatureClass_conversion(tempsplitLineCenterDist, temptagfyardfolder,temptagfyardfile, expression) 
    temptagfyard = r"/TestData/temptagfyard.shp"

    tempcleanfyard = r"TestData/tempcleanfyards.shp"
    arcpy.SpatialJoin_analysis(tempcleanyard,temptagfyard, tempcleanfyard, "#", "KEEP_COMMON")


    arcpy.AddField_management(tempcleanfyard,"Fyard","Double")
    delimitedField1 = arcpy.AddFieldDelimiters(tempcleanfyard, "!AREA!")
    arcpy.CalculateField_management(tempcleanfyard, "Fyard", delimitedField1,"PYTHON_9.3")
    tempcleanfyardpt = r"/tempcleanfyardpt.shp"
    arcpy.FeatureToPoint_management(tempcleanfyard, tempcleanfyardpt, "CENTROID")



#So close. Now I have 2 files: one with front yard size, and another with back.
#I need to join these back to a new parcel file. But I only want to bring in just the one field with the Front & Back
#Area.
#To select only one field in a join you have to use the FieldMapping algorithm. The variables are labeled weird because I just
#carefully copied them directly from the example to get the function to work.

    fieldmappings = arcpy.FieldMappings()
    fieldmappings.addTable(outtestparcels)
    fieldmappings.addTable(tempcleanbyardpt)
     


    fm_type = arcpy.FieldMap()
    fms = arcpy.FieldMappings()
    tree_type = "Byard"
    fm_type.addInputField(tempcleanbyardpt, tree_type)
    type_name = fm_type.outputField
    type_name.name = "Byard"
    fm_type.outputField = type_name
    fms.addFieldMap(fm_type)

    tempparcelyard = r"/tempparcelyard.shp"
    arcpy.SpatialJoin_analysis(outtestparcels,tempcleanbyardpt, tempparcelyard, "#", "#", fms)


    fieldmappings = arcpy.FieldMappings()
    fieldmappings.addTable(tempparcelyard)
    fieldmappings.addTable(tempcleanfyardpt)
     
    fm_type = arcpy.FieldMap()
    fm_diam = arcpy.FieldMap()
    fms = arcpy.FieldMappings()

    tree_type = "Byard"
    plant_diam = "Fyard"

    fm_type.addInputField(tempparcelyard, tree_type)
    fm_diam.addInputField(tempcleanfyardpt, plant_diam )

    type_name = fm_type.outputField
    type_name.name = "Byard"
    fm_type.outputField = type_name 

    diam_name = fm_diam.outputField
    diam_name.name = "Fyard"
    fm_diam.outputField = diam_name

    fms.addFieldMap(fm_type)
    fms.addFieldMap(fm_diam)

    parcelwithyardareas = r"/parcelwithyardareas.shp"
    arcpy.SpatialJoin_analysis(tempparcelyard,tempcleanfyardpt, parcelwithyardareas, "#", "#", fms)


#There you go. Now I have that final output. I'll add it to the map using this script below that I've been using for debugging:

    thetempsideyardcenter = r"/parcelwithyardareas.shp"
    #thetempsideyards1 = r"C:/Users/Stephen/Desktop/TestData/tempsideyards1.shp"
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
    newlayer = arcpy.mapping.Layer(parcelwithyardareas)
    arcpy.mapping.AddLayer(df, newlayer,"TOP")
    #newlayer = arcpy.mapping.Layer(thetempsideyards1)
    #arcpy.mapping.AddLayer(df, newlayer,"TOP")




#Ok, time to clean up all those intermediate files:


    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/outtestyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/parcelbox.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/splitLineCenter.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempcleanbyardpt.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempcleanbyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempcleanfyardpt.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempcleanfyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempcleanyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempcutlines.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempdirtyyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempdirtyyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempdirtyyards1.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempparcelyard.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/temppolytoline.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempsideyardcenter.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempsideyards.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempsideyards1.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempsplitLineCenterDist.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/tempSplitLines.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/temptagbyard.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/temptagfyard.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/temptempsideyardcenter.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/test.shp")
    arcpy.Delete_management("C:/Users/Stephen/Desktop/TestData/test1.shp")




except Exception as e:
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.message )
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")



#The end!