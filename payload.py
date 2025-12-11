import bpy

print("--------------------------------------------------")
print("ADDING COPY ROTATION CONSTRAINT TO PATHS")
print("--------------------------------------------------")

if "Direction_Controller" not in bpy.data.objects:
    print("Error: Direction_Controller not found!")
else:
    controller = bpy.data.objects["Direction_Controller"]
    
    # helper
    def add_copy_rotation(obj):
        # Check if already exists?
        for c in obj.constraints:
            if c.type == 'COPY_ROTATION' and c.target == controller:
                return # Already added
                
        c = obj.constraints.new('COPY_ROTATION')
        c.target = controller
        c.name = "Steering"
        # Defaults are usually good: Target/Owner Space World, Mix Replace, XYZ.
        print(f"  Added Copy Rotation to {obj.name}")

    count = 0
    for obj in bpy.data.objects:
        if obj.name.startswith("WalkPath"):
            add_copy_rotation(obj)
            count += 1
            
    print(f"Applied Steering constraint to {count} paths.")
