import bpy

def reset_scene():
    print("-" * 30)
    print("Reseting Scene to Blank State...")
    
    # 1. Switch to Object Mode
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 2. Select All & Delete Objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 3. Clear Collections (except Master Collection)
    for c in bpy.data.collections:
        bpy.data.collections.remove(c)

    # 4. Purge Orphan Data (Meshes, Materials, Node Groups)
    # We run this a few times because deleting a mesh might orphan a material
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    print("Scene Cleaned.")

if __name__ == "__main__":
    reset_scene()
