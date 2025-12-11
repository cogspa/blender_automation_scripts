import bpy

def create_master_controller():
    print("--------------------------------------------------")
    print("CREATING MASTER CHARACTER CONTROLLER")
    print("--------------------------------------------------")

    # 1. Check/Cleanup
    if "character_controller" in bpy.data.objects:
        print("character_controller already exists. Selecting it.")
        master = bpy.data.objects["character_controller"]
    else:
        # Create
        bpy.ops.object.empty_add(type='CUBE', location=(0,0,0))
        master = bpy.context.active_object
        master.name = "character_controller"
        master.empty_display_size = 5.0
        print("Created 'character_controller' (Cube Empty).")

    # 2. Collect Children
    children_to_parent = []
    
    # Direction Controller
    if "Direction_Controller" in bpy.data.objects:
        children_to_parent.append(bpy.data.objects["Direction_Controller"])
        
    # Spider Body
    if "Spider_Body" in bpy.data.objects:
        children_to_parent.append(bpy.data.objects["Spider_Body"])
        
    # Walk Paths
    for obj in bpy.data.objects:
        if obj.name.startswith("WalkPath"):
            children_to_parent.append(obj)
            
    if not children_to_parent:
        print("No children found to parent!")
        return

    # 3. Parent
    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select Children
    for child in children_to_parent:
        child.select_set(True)
        print(f"  Scheduling parent: {child.name}")
        
    # Select Parent (Active)
    master.select_set(True)
    bpy.context.view_layer.objects.active = master
    
    # Execute Parent Set
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    
    print(f"Parented {len(children_to_parent)} objects to 'character_controller'.")

if __name__ == "__main__":
    create_master_controller()
