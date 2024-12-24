import arcpy
import os

# Define paths
input_gdb = r"E:\Sheltech\Exercise\Chhatak_SA_46_04 Dec 2024\Distribution\Sumon_Nandile\Geodatabase.gdb"
output_folder = r"E:\Sheltech\Exercise\Chhatak_SA_46_04 Dec 2024\Distribution\Sumon_Nandile"
output_gdb_name = "Topology_MD_SD.gdb"
output_gdb = os.path.join(output_folder, output_gdb_name)
output_dataset = "Topology"
output_polygon_dataset = "Polygon"

# Create the output geodatabase if it doesn't exist
if not arcpy.Exists(output_gdb):
    arcpy.CreateFileGDB_management(output_folder, output_gdb_name)
    print("Created Geodatabase: {}".format(output_gdb_name))

# Create new feature datasets in the output geodatabase if they don't exist
if not arcpy.Exists(os.path.join(output_gdb, output_dataset)):
    arcpy.CreateFeatureDataset_management(output_gdb, output_dataset, spatial_reference=None)
    print("Created Feature Dataset: {}".format(output_dataset))
else:
    print("Feature Dataset {} already exists".format(output_dataset))

if not arcpy.Exists(os.path.join(output_gdb, output_polygon_dataset)):
    arcpy.CreateFeatureDataset_management(output_gdb, output_polygon_dataset, spatial_reference=None)
    print("Created Feature Dataset: {}".format(output_polygon_dataset))
else:
    print("Feature Dataset {} already exists".format(output_polygon_dataset))

# Set workspace to input geodatabase
arcpy.env.workspace = input_gdb

# Filter only line feature classes
line_features = [fc for fc in arcpy.ListFeatureClasses() if arcpy.Describe(fc).shapeType == "Polyline"]

# Process each line feature class
for feature_class in line_features:

    # Copy feature class to output dataset
    arcpy.FeatureClassToFeatureClass_conversion(feature_class, os.path.join(output_gdb, output_dataset), feature_class)
    print("Copied {} to feature dataset".format(feature_class))

    # Create a topology for the feature class
    topology_name = "{}_Topology".format(feature_class)
    arcpy.CreateTopology_management(os.path.join(output_gdb, output_dataset), topology_name, 0.001)
    print("Created topology for {}".format(feature_class))

    # Add feature class to topology
    arcpy.AddFeatureClassToTopology_management(
        os.path.join(output_gdb, output_dataset, topology_name), 
        os.path.join(output_gdb, output_dataset, feature_class), 
        1, 1
    )

    # Define topology rules
    rules = [
        "Must Not Have Pseudo-Nodes (Line)",
        "Must Not Have Dangles (Line)",
        "Must Not Overlap (Line)"
    ]

    # Add rules to topology
    for rule in rules:
        arcpy.AddRuleToTopology_management(
            os.path.join(output_gdb, output_dataset, topology_name),
            rule,
            os.path.join(output_gdb, output_dataset, feature_class)
        )
        print("Added rule '{}' to topology for: {}".format(rule, topology_name))

    # Validate topology
    arcpy.ValidateTopology_management(os.path.join(output_gdb, output_dataset, topology_name))
    print("Validated topology for {}_Topology".format(feature_class))

# Additional process to convert _LD lines to polygons and perform spatial join with _ND
ld_features = [fc for fc in line_features if fc.endswith("_LD")]
nd_features = [fc for fc in arcpy.ListFeatureClasses() if fc.endswith("_ND")]

for ld_fc in ld_features:
    # Convert _LD lines to polygons
    polygon_fc_name = "{}_To_MD".format(ld_fc)
    arcpy.FeatureToPolygon_management(ld_fc, os.path.join(output_gdb, output_polygon_dataset, polygon_fc_name))
    print("Converted {} to polygon feature class {}".format(ld_fc, polygon_fc_name))

    # Find corresponding _ND feature class
    base_name = "_".join(ld_fc.split("_")[:-1])
    nd_fc = next((fc for fc in nd_features if fc.startswith(base_name)), None)
    
    if nd_fc:
        # Create a temporary feature class for the spatial join
        temp_spatial_join_output = "in_memory/temp_spatial_join"

        # Delete the temporary feature class if it exists
        if arcpy.Exists(temp_spatial_join_output):
            arcpy.Delete_management(temp_spatial_join_output)
            print("Deleted existing in-memory temporary feature class")

        # Perform spatial join and store the result in the temporary feature class
        arcpy.SpatialJoin_analysis(
            os.path.join(output_gdb, output_polygon_dataset, polygon_fc_name), 
            nd_fc, 
            temp_spatial_join_output
        )
        print("Performed spatial join for {} with {}".format(polygon_fc_name, nd_fc))

        # Delete the existing feature class if it exists
        if arcpy.Exists(os.path.join(output_gdb, output_polygon_dataset, polygon_fc_name)):
            arcpy.Delete_management(os.path.join(output_gdb, output_polygon_dataset, polygon_fc_name))
            print("Deleted existing feature class {}".format(polygon_fc_name))

        # Overwrite the polygon feature class with the spatial join result
        arcpy.CopyFeatures_management(temp_spatial_join_output, os.path.join(output_gdb, output_polygon_dataset, polygon_fc_name))
        print("Overwritten {} with spatial join result".format(polygon_fc_name))

# Additional process to convert specific L_CODE values to polygons
code_list = {
    "32": "Tin Shed Structure",
    "33": "Other Structure",
    "34": "Pan Boroj",
    "35": "Pond",
    "36": "Graveyard",
    "37": "Beel",
    "38": "Char",
    "39": "Pond Bank",
    "13": "Embankment",
    "31": "Permanent Structure (Dalan)"
}

sd_features = [fc for fc in arcpy.ListFeatureClasses() if fc.endswith("_SD")]

for ld_fc in ld_features:
    # Find corresponding _SD feature class
    base_name = "_".join(ld_fc.split("_")[:-1])
    sd_fc = next((fc for fc in sd_features if fc.startswith(base_name)), None)

    if sd_fc:
        # Delete the in-memory selected feature class if it exists
        selected_fc_path = "in_memory/selected_fc"
        if arcpy.Exists(selected_fc_path):
            arcpy.Delete_management(selected_fc_path)
            print("Deleted existing in-memory selected feature class")

        # Select features with specific L_CODE values
        query = "L_CODE IN (31, 32, 33, 34, 35, 36, 37, 38, 39, 13)"
        selected_fc = arcpy.Select_analysis(ld_fc, selected_fc_path, query)
        print("Selected features from {} with L_CODE values {}".format(ld_fc, query))

        if int(arcpy.GetCount_management(selected_fc).getOutput(0)) > 0:
            print("Features found within L_CODE in {}".format(ld_fc))
            # Convert selected _LD lines to polygons for _To_SD
            polygon_fc_sd_name = "{}_To_SD".format(ld_fc)
            arcpy.FeatureToPolygon_management(selected_fc, os.path.join(output_gdb, output_polygon_dataset, polygon_fc_sd_name))
            print("Converted selected {} to polygon feature class {}".format(ld_fc, polygon_fc_sd_name))
        else:
            print("No features with specified L_CODE found in {}".format(ld_fc))
    else:
        print("Not found SD of {} for converting to polygon feature class".format(ld_fc))

print("Topology validation and additional processing completed. Check the output geodatabase for details.")
