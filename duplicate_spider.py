import bpy

def duplicate_spider(source_master_name="character_controller"):
    """
    Safely duplicates a spider hierarchy, ensuring all dependencies (Constraints, IK Targets)
    are included in the duplication to preventing stretching/linking issues.
    """
    print(f"--------------------------------------------------")
    print(f"DUPLICATING SPIDER (Constraint-Safe)")
    print(f"--------------------------------------------------")
    
    if source_master_name not in bpy.data.objects:
        print(f"Error: Source '{source_master_name}' not found.")
        return None

    master = bpy.data.objects[source_master_name]

    # 1. GATHER OBJECTS
    # We start with the Master and its Hierarchy
    objects_to_dup = set()
    objects_to_dup.add(master)
    
    def get_children_recursive(obj):
        for child in obj.children:
            objects_to_dup.add(child)
            get_children_recursive(child)
            
    get_children_recursive(master)
    
    # 2. FIND MISSING DEPENDENCIES (The "Floaters")
    # Specifically: IK Targets might not be parented to Master, but are targeted by Rigs.
    
    # Scan for Rigs inside our collected set
    rigs = [o for o in objects_to_dup if o.type == 'ARMATURE']
    
    for rig in rigs:
        # Check Pose Bone Constraints (IK)
        for pose_bone in rig.pose.bones:
            for c in pose_bone.constraints:
                if (c.type == 'IK' or c.type == 'DAMPED_TRACK' or c.type == 'COPY_TRANSFORMS') and c.target:
                    if c.target not in objects_to_dup:
                        print(f"  Found detached dependency: {c.target.name} (targeted by {rig.name})")
                        objects_to_dup.add(c.target)
                        
    # Check for Follow Path targets (WalkPaths)
    # If WalkPath works via constraint, ensure target is in set.
    # Usually WalkPath is child of Master, so it's in.
    # But IK Target Follow Path -> WalkPath.
    
    # We added IK Targets above ^. Now check THEIR dependencies.
    # Scan constraints of ALL objects in set
    # (Since set grows, convert to list loop or do a second pass)
    
    # Safe 2nd pass
    current_list = list(objects_to_dup)
    for obj in current_list:
        for c in obj.constraints:
             if c.target and c.target not in objects_to_dup:
                 print(f"  Found detached dependency: {c.target.name} (targeted by {obj.name})")
                 objects_to_dup.add(c.target)

    # 3. DUPLICATE
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects_to_dup:
        obj.select_set(True)
        
    bpy.context.view_layer.objects.active = master
    
    print(f"Selected {len(objects_to_dup)} objects for duplication.")
    
    # Execute Duplicate
    bpy.ops.object.duplicate(linked=False)
    
    new_master = bpy.context.view_layer.objects.active
    
    print(f"Success! New Spider Master: {new_master.name}")
    return new_master

if __name__ == "__main__":
    duplicate_spider()
