import bpy
import random
import math
import imp
import sys

# Ensure path
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

import create_pathless_walk
import create_body_noise

from mathutils import Vector

def create_swarm(count=3, range_x=80, range_y=80):
    print(f"--------------------------------------------------")
    print(f"CREATING SPIDER SWARM (INLINE LOGIC)")
    print(f"--------------------------------------------------")

    source_name = "character_controller"
    
    # 0. Auto-Build if Missing
    if source_name not in bpy.data.objects:
        print(f"Source '{source_name}' not found. Building Spider from scratch...")
        import build_full_spider
        imp.reload(build_full_spider)
        build_full_spider.build_spider()
        
        if source_name not in bpy.data.objects:
             print("Error: Build failed to create source spider.")
             return

    # Keep track of positions to avoid overlap
    spawned_positions = []
    source_obj = bpy.data.objects[source_name]
    spawned_positions.append(source_obj.location.to_2d())

    # 1. Convert Source to Delta first
    print(f"Converting Source '{source_name}' to Delta Animation...")
    imp.reload(create_pathless_walk)
    create_pathless_walk.create_pathless_walk(source_name)
    
    # Randomize Source Location (so it's not always at 0,0,0)
    rx = random.uniform(-range_x, range_x)
    ry = random.uniform(-range_y, range_y)
    source_obj.location.x = rx
    source_obj.location.y = ry
    spawned_positions[0] = source_obj.location.to_2d()
    print(f"Moved Source Spider to ({rx:.1f}, {ry:.1f})")

    # 2. Loop
    for i in range(count):
        print(f"\n[Instance {i+1}] Duplicating...")
        
        # A. Gather Objects (The Safe Selection Logic)
        source_master = bpy.data.objects[source_name]
        objects_to_dup = set()
        objects_to_dup.add(source_master)
        
        # Recursive Children
        def recurse(obj):
            for child in obj.children:
                if child.name not in [o.name for o in objects_to_dup]:
                    objects_to_dup.add(child)
                    recurse(child)
        recurse(source_master)
        
        # Dependency Check (IK Targets)
        base_list = list(objects_to_dup)
        for obj in base_list:
            # Check constraints
            for c in obj.constraints:
                if c.target and c.target not in objects_to_dup:
                    print(f"  + Added Dependency: {c.target.name}")
                    objects_to_dup.add(c.target)
            # Check Armature constraints
            if obj.type == 'ARMATURE':
                for pb in obj.pose.bones:
                    for c in pb.constraints:
                        if c.target and c.target not in objects_to_dup:
                             print(f"  + Added Dependency (Bone): {c.target.name}")
                             objects_to_dup.add(c.target)

        # B. Duplicate
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects_to_dup:
            obj.select_set(True)
            
        bpy.context.view_layer.objects.active = source_master
        
        # Duplicate
        bpy.ops.object.duplicate(linked=False)
        
        # New Master is active
        new_master = bpy.context.view_layer.objects.active
        if new_master.name == source_name:
             print("  ERROR: Duplication didn't result in new active object? (Or name identical?)")
             # Try finding object with pattern .001 etc?
             # But active usually updates.
             
        # C. Scatter with Overlap Check
        found_spot = False
        attempts = 0
        min_dist = 15.0 # Minimum 15 meters apart
        
        rx, ry = 0, 0
        
        while not found_spot and attempts < 100:
            rx = random.uniform(-range_x, range_x)
            ry = random.uniform(-range_y, range_y)
            pos_2d = Vector((rx, ry))
            
            # Check dist
            too_close = False
            for p in spawned_positions:
                if (p - pos_2d).length < min_dist:
                    too_close = True
                    break
            
            if not too_close:
                found_spot = True
            else:
                attempts += 1
        
        spawned_positions.append(Vector((rx, ry)))
        
        rz = random.uniform(0, math.pi*2)
        
        # Use location (not delta) for base scatter?
        # NO, we want to set the BASE location.
        # If we use Delta Animation, `location` is free.
        new_master.location.x = rx
        new_master.location.y = ry
        new_master.rotation_euler.z = rz
        
        # Clear Animation Data on Duplicate?
        # Duplicate copies animation.
        # But create_pathless_walk REPLACES it. So it should be fine.
        new_master.animation_data_clear() # Start fresh just in case
        
        print(f"  Scattered to ({rx:.1f}, {ry:.1f})")
        
        # D. Reset IK Targets (in selection)
        for obj in bpy.context.selected_objects:
            if "IK_Target" in obj.name:
                obj.location = (0,0,0)
        
        # E. Walk
        create_pathless_walk.create_pathless_walk(new_master.name)
        
        # F. Random Body Noise
        imp.reload(create_body_noise)
        for obj in bpy.context.selected_objects:
            if "Spider_Body" in obj.name:
                create_body_noise.add_body_noise(obj.name)


    print("--------------------------------------------------")
    print("POST-CREATION SCATTER VALIDATION")
    print("--------------------------------------------------")
    
    controllers = [o for o in bpy.data.objects if o.name.startswith("character_controller")]
    final_positions = [] # Tuple (x,y)
    
    for ctrl in controllers:
        # Skip checking against itself if already in list? 
        # Actually easier to just check if at 0,0,0 first.
        
        # If actually at 0,0,0 (tolerance)
        if ctrl.location.length < 0.1:
             print(f"WARNING: {ctrl.name} found at Origin! Re-scattering...")
             # Force move
             rx = random.uniform(-range_x, range_x)
             ry = random.uniform(-range_y, range_y)
             ctrl.location.x = rx
             ctrl.location.y = ry
             print(f"  -> Moved to ({rx:.1f}, {ry:.1f})")
             
    print("Swarm Creation Complete.")

if __name__ == "__main__":
    create_swarm()
