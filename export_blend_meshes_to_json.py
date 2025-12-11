import bpy
import json
import sys
import os
from mathutils import Matrix

def export_meshes_to_json(output_path, apply_modifiers=False, world_space=False):
    """
    Export all mesh objects in the current .blend file to a JSON file.
    """
    data = {
        "file": bpy.data.filepath,
        "objects": []
    }

    # Get depsgraph for evaluated meshes (modifiers)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        if apply_modifiers:
            obj_eval = obj.evaluated_get(depsgraph)
            mesh = obj_eval.to_mesh()
        else:
            mesh = obj.data

        # Choose transform space
        if world_space:
            transform_matrix = obj.matrix_world
        else:
            transform_matrix = Matrix.Identity(4)

        # Collect vertices
        vertices = []
        for v in mesh.vertices:
            co = transform_matrix @ v.co
            vertices.append([co.x, co.y, co.z])

        # Collect faces (polygons)
        faces = []
        for poly in mesh.polygons:
            faces.append(list(poly.vertices))

        # Object transform
        obj_info = {
            "name": obj.name,
            "location": list(obj.location),
            "rotation_euler": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "mesh": {
                "vertex_count": len(vertices),
                "face_count": len(faces),
                "vertices": vertices,
                "faces": faces
            }
        }

        data["objects"].append(obj_info)
        count += 1

        if apply_modifiers:
            obj_eval.to_mesh_clear()

    # Write JSON
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"SUCCESS: Exported {count} mesh object(s) to '{output_path}'")
        
        # Show a popup message if running in UI
        def draw(self, context):
            self.layout.label(text=f"Exported {count} meshes to: {os.path.basename(output_path)}")
        bpy.context.window_manager.popup_menu(draw, title="Export Successful", icon='CHECKMARK')
        
    except Exception as e:
        print(f"FAILED to write JSON: {e}")
        def draw_err(self, context):
            self.layout.label(text=f"Export Failed: {e}")
        bpy.context.window_manager.popup_menu(draw_err, title="Export Failed", icon='ERROR')


def main():
    # 1. Output Path Determination
    # Default to a fixed path in your scratch directory so we can find it easily
    # Or simple 'scene_meshes.json' next to the blend file
    
    default_dir = "/Users/joem/.gemini/antigravity/scratch/blender_bridge"
    filename = "scene_meshes.json"
    
    # If the blend file is saved, try to save next to it? 
    # But user wants us to see it. Let's force it to the bridge folder.
    output_path = os.path.join(default_dir, filename)

    # CLI Argument Parsing (for headless mode)
    argv = sys.argv
    apply_mods = True
    use_world = True
    
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        if len(args) >= 1:
            output_path = args[0]
    
    print(f"Exporting to: {output_path}")
    export_meshes_to_json(output_path, apply_modifiers=apply_mods, world_space=use_world)

if __name__ == "__main__":
    main()
