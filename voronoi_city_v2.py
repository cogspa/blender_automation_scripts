import bpy
import bmesh
import random
import addon_utils
import mathutils

# --- Configuration ---
NUM_CELLS = 50
GAP_SIZE = 0.2
MIN_HEIGHT = 1.0
MAX_HEIGHT = 4.0
SEED = 99

def build_voronoi_city():
    print(f"\n{'='*40}")
    print(f"--- Voronoi City V2.1 (Seed {SEED}) ---")
    random.seed(SEED)
    
    # 1. Setup & Cleanup
    if bpy.context.object and bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        
    addon_utils.enable("object_fracture_cell")
    
    col_name = "Voronoi_City"
    if col_name in bpy.data.collections:
        c = bpy.data.collections[col_name]
        for o in c.objects:
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
    
    c = bpy.data.collections.new(col_name)
    bpy.context.scene.collection.children.link(c)
        
    # 2. Base Slab
    print("Creating Base Slab...")
    bpy.ops.mesh.primitive_cube_add(size=1)
    slab = bpy.context.active_object
    slab.name = "City_Base"
    slab.scale = (10, 10, 0.1) 
    
    # Apply Scale is CRITICAL
    bpy.ops.object.transform_apply(scale=True)
    
    # Move to collection
    for old_c in slab.users_collection: old_c.objects.unlink(slab)
    c.objects.link(slab)
    
    # 3. Particles
    print("Adding Particles...")
    bpy.ops.object.particle_system_add()
    ps = slab.particle_systems.active
    pset = ps.settings
    pset.count = NUM_CELLS
    pset.frame_start = 1
    pset.frame_end = 1
    pset.emit_from = 'VOLUME'
    pset.distribution = 'RANDOM'
    
    # IMPORTANT: Force update so particles are calculated
    bpy.context.view_layer.update()
    
    # 4. Fracture
    print("Fracturing...")
    bpy.ops.object.select_all(action='DESELECT')
    slab.select_set(True)
    bpy.context.view_layer.objects.active = slab
    
    # Context override often helps with operators running from scripts
    ctx = bpy.context.copy()
    ctx['active_object'] = slab
    ctx['selected_objects'] = [slab]
    
    objs_before = set(bpy.data.objects)
    
    try:
        # We use a slight margin; 0 can sometimes cause issues.
        bpy.ops.object.add_fracture_cell_objects(
            ctx,
            source_limit=NUM_CELLS,
            source_noise=0.1, 
            use_smooth_faces=False,
            margin=0.001
        )
    except Exception as e:
        print(f"!!! Fracture Operator Failed: {e}")
        return

    objs_after = set(bpy.data.objects)
    new_cells = list(objs_after - objs_before)
    
    # Filter only meshes (sometimes fracture makes empties or groups)
    new_cells = [o for o in new_cells if o.type == 'MESH']
    
    if not new_cells:
        print("!!! No cells generated. Fracture failed silently.")
        # Do not delete slab so user can see it
        return
        
    # Clean up base
    bpy.data.objects.remove(slab, do_unlink=True)
        
    print(f"Success! {len(new_cells)} cells created. Extruding...")
    
    # 5. Process Cells
    for obj in new_cells:
        # Ensure inside collection
        if c.name not in [x.name for x in obj.users_collection]:
            c.objects.link(obj)
            # Unlink from others
            for x in obj.users_collection: 
                if x != c: x.objects.unlink(obj)

        bpy.context.view_layer.objects.active = obj
        
        # A. Center Origin for Scaling
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        
        # B. Shrink (Gap)
        s = 1.0 - GAP_SIZE
        obj.scale = (s, s, 1.0)
        bpy.ops.object.transform_apply(scale=True)
        
        # C. Extrude Top Face
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Select Top Faces
        bpy.ops.mesh.select_all(action='DESELECT')
        # We do this manually via bmesh to be precise (Normal Z > 0.5)
        top_faces = [f for f in bm.faces if f.normal.z > 0.5]
        
        for f in top_faces:
            f.select = True
            
        bmesh.update_edit_mesh(obj.data) # Flush selection
        
        # Extrude ONLY if we found a top face
        if top_faces:
             h = random.uniform(MIN_HEIGHT, MAX_HEIGHT)
             bpy.ops.mesh.extrude_region_move(
                 TRANSFORM_OT_translate={"value": (0, 0, h)}
             )
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # D. Color
        mat = bpy.data.materials.new(name=f"BuildingMat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            col = (random.random(), random.random(), random.random(), 1.0)
            bsdf.inputs['Base Color'].default_value = col
        obj.data.materials.append(mat)

    print("Voronoi City V2 Complete.")

if __name__ == "__main__":
    build_voronoi_city()
