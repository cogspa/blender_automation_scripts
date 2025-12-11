import bpy
import json
import os
from mathutils import Matrix

def export_scene_full():
    # Define output path
    output_dir = "/Users/joem/.gemini/antigravity/scratch/blender_bridge"
    output_filename = "scene_dump.json"
    output_path = os.path.join(output_dir, output_filename)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Start Exporting to {output_path}...")
    
    data = {
        "file": bpy.data.filepath,
        "objects": [],
        "armatures": []
    }
    
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # --------------------------------------------------------------------
    # 1. MESHES (Snapshot of deformed geometry)
    # --------------------------------------------------------------------
    for obj in bpy.data.objects:
        if obj.type != 'MESH': continue
        
        # Apply modifiers (Armature, Subsurf, etc) to get final shape
        try:
            obj_eval = obj.evaluated_get(depsgraph)
            mesh = obj_eval.to_mesh()
        except:
            continue

        mw = obj.matrix_world
        
        verts = []
        for v in mesh.vertices:
            co = mw @ v.co
            verts.append([round(co.x, 4), round(co.y, 4), round(co.z, 4)])
            
        faces = []
        for p in mesh.polygons:
            faces.append(list(p.vertices))
            
        data["objects"].append({
            "name": obj.name,
            "type": "MESH",
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "mesh_data": {
                "vertex_count": len(verts),
                "face_count": len(faces),
                "vertices": verts,
                "faces": faces
            }
        })
        obj_eval.to_mesh_clear()

    # --------------------------------------------------------------------
    # 2. ARMATURES (Rig Structure & IK)
    # --------------------------------------------------------------------
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE': continue
        
        arm_data = {
            "name": obj.name,
            "type": "ARMATURE",
            "location": list(obj.location),
            "bones": []
        }
        
        # We use the Pose Bones to get the current state and constraints
        for pbone in obj.pose.bones:
            # Basic Bone Info (Head/Tail in Armature Space)
            # To get World Space, multiply by obj.matrix_world
            mat = obj.matrix_world
            head_world = mat @ pbone.head
            tail_world = mat @ pbone.tail
            
            bone_info = {
                "name": pbone.name,
                "parent": pbone.parent.name if pbone.parent else None,
                "head": [round(head_world.x, 4), round(head_world.y, 4), round(head_world.z, 4)],
                "tail": [round(tail_world.x, 4), round(tail_world.y, 4), round(tail_world.z, 4)],
                "constraints": []
            }
            
            # Extract IK Constraints
            for const in pbone.constraints:
                if const.type == 'IK':
                    ik_info = {
                        "type": "IK",
                        "name": const.name,
                        "target": const.target.name if const.target else None,
                        "subtarget": const.subtarget if const.subtarget else None,
                        "pole_target": const.pole_target.name if const.pole_target else None,
                        "chain_count": const.chain_count,
                        "influence": const.influence
                    }
                    bone_info["constraints"].append(ik_info)
            
            arm_data["bones"].append(bone_info)
            
        data["armatures"].append(arm_data)
        
    # --------------------------------------------------------------------
    # WRITE
    # --------------------------------------------------------------------
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"DONE. Exported {len(data['objects'])} meshes and {len(data['armatures'])} armatures.")
    
    # UI Feedback
    def draw(self, context):
        self.layout.label(text=f"Exported to scene_dump.json")
    bpy.context.window_manager.popup_menu(draw, title="Full Export Complete", icon='CHECKMARK')

if __name__ == "__main__":
    export_scene_full()
