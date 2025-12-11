import bpy
import json
import os

def import_scene_from_json(json_path):
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    print(f"Importing scene from {json_path}...")
    
    # Optional: Clear existing scene?
    # bpy.ops.object.select_all(action='SELECT')
    # bpy.ops.object.delete()

    collection = bpy.context.collection

    for obj_data in data.get('objects', []):
        mesh_data = obj_data.get('mesh')
        if not mesh_data:
            continue

        name = obj_data.get('name', 'ImportedObject')
        vertices = mesh_data.get('vertices', [])
        faces = mesh_data.get('faces', [])

        # Create Mesh
        mesh = bpy.data.meshes.new(name + "_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()

        # Create Object
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)

        # NOTE: The vertices in the JSON were exported in WORLD SPACE.
        # This means they already contain the location, rotation, and scale transforms.
        # Therefore, we leave the new object at (0,0,0) with Identity rotation/scale.
        # If we applied obj_data['location'], we would apply the transform twice!
        
        # However, we can construct the object such that its origin is at the exported world location, 
        # but that requires subtracting that location from all vertices. 
        # For a simple "Visual Keep", keeping vertices as-is and object at 0,0,0 is accurate.

    print(f"Successfully imported {len(data['objects'])} objects.")

if __name__ == "__main__":
    # Default path based on previous context
    json_file = "/Users/joem/.gemini/antigravity/scratch/blender_bridge/scene_meshes.json"
    import_scene_from_json(json_file)
