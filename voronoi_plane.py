import bpy
import random
import addon_utils

# --- Parameters ---
NUM_CELLS = 25
OFFSET = 0.1
PADDING = 0.05 # Gap size

def run():
    # 1. Setup
    print("-" * 30)
    print("Starting Voronoi Generation...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        
    addon_utils.enable("object_fracture_cell")

    # 2. Prepare Collection
    col_name = "Voronoi_Collection"
    if col_name in bpy.data.collections:
        col = bpy.data.collections[col_name]
        for obj in col.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)

    # 3. Create Source Object (Cube)
    # Using a standard Cube to ensure volume calculations work
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    source = bpy.context.active_object
    source.name = "Voronoi_Source"
    source.scale = (5, 5, 0.2) # Wide and flat-ish
    
    # We do NOT apply scale this time to test if that was the issue
    # But for Particles to distribute correctly in a flattened object, 
    # we usually want applied scale. Let's try applying it.
    bpy.ops.object.transform_apply(scale=True)
    
    # Move to collection
    for c in source.users_collection:
        c.objects.unlink(source)
    col.objects.link(source)
    
    # 4. Add Particles (The seeds for Voronoi)
    bpy.ops.object.particle_system_add()
    psys = source.particle_systems.active
    pset = psys.settings
    pset.count = NUM_CELLS
    pset.frame_start = 1
    pset.frame_end = 1
    pset.distribution = 'RANDOM'
    pset.emit_from = 'VOLUME'
    
    # 5. Fracture
    print("Fracturing...")
    
    # Selection dance
    bpy.ops.object.select_all(action='DESELECT')
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    
    # Record existing objects to identify new ones later
    existing_objs = set(bpy.data.objects)
    
    try:
        res = bpy.ops.object.add_fracture_cell_objects(
            source_limit=NUM_CELLS,
            source_noise=0.1, # Add noise for more organic look
            use_smooth_faces=False,
            margin=0.001
        )
        print(f"Fracture Result: {res}")
    except Exception as e:
        print(f"Fracture Exception: {e}")
    
    # 6. Find New Cells
    new_objs = list(set(bpy.data.objects) - existing_objs)
    cells = [o for o in new_objs if o.type == 'MESH']
    
    print(f"Generated {len(cells)} cells.")
    
    if not cells:
        print("Fracture failed to generate cells. Keeping source object.")
        return

    # 7. Cleanup Source
    bpy.data.objects.remove(source, do_unlink=True)
    
    # 8. Post-Process Cells
    for obj in cells:
        # Link to collection
        if col.name not in [c.name for c in obj.users_collection]:
            col.objects.link(obj)
            # Unlink from others
            for c in obj.users_collection:
                if c != col:
                    c.objects.unlink(obj)
        
        # Center Origin
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        
        # Scale (Gap)
        s = 1.0 - PADDING
        obj.scale = (s, s, 1.0) # Scale XY only? Or all? Let's do all for safety on shards
        
        # Random Color
        mat = bpy.data.materials.new(name="VColor")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (
                random.random(), random.random(), random.random(), 1
            )
        obj.data.materials.append(mat)
        
    print("Done.")

if __name__ == "__main__":
    run()
