import arcpy
import os

# Define paths
input_gdb = r"Input_your_gdb_file.gdb"
output_folder = r"Replace_With_Output_folder_Location"
output_gdb_name = "Give_a_gdb_file_name.gdb"
output_gdb = os.path.join(output_folder, output_gdb_name)
output_dataset = "Give_a_Dataset_name"

# Create the output geodatabase if it doesn't exist
if not arcpy.Exists(output_gdb):
    arcpy.CreateFileGDB_management(output_folder, output_gdb_name)
    print("Created Geodatabase: {}".format(output_gdb_name))

# Create a new feature dataset in the output geodatabase
arcpy.CreateFeatureDataset_management(output_gdb, output_dataset, spatial_reference=None)
print("Created Feature Dataset: {}".format(output_dataset))

# Set workspace to input geodatabase
arcpy.env.workspace = input_gdb

# Filter only line feature classes
line_features = [fc for fc in arcpy.ListFeatureClasses() if arcpy.Describe(fc).shapeType == "Polyline"]

# Process each line feature class
for feature_class in line_features:

    # Copy feature class to output dataset
    arcpy.FeatureClassToFeatureClass_conversion(feature_class, os.path.join(output_gdb, output_dataset), feature_class)
    print("Copied {} to feature dataset".format(feature_class) )

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

print("Topology validation completed for all line features. Check the output geodatabase for details.")
