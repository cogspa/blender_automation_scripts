import bpy

def create_body():
    # 1. Clean up if exists
    if "body" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["body"], do_unlink=True)
        
    # 2. Add Cube
    # Default size is 2m, which is fine
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    body = bpy.context.active_object
    body.name = "body"
    
    # 3. Move Upward
    # Assuming "upward" means placing it roughly above the floor or origin, 
    # or aligning with the top of the legs (which were height 4).
    # Let's move it to Z=4 to sit on top of the leg origin? 
    # Or just "Move upward" usually implies G Z <mouse move>.
    # Let's pick a reasonable height, say Z=5 or Z=6?
    # Or matches leg height (4m).
    # Let's put center at Z=5.
    
    body.location.z = 5.0
    
    print("Created 'body' cube at Z=5.0")

if __name__ == "__main__":
    create_body()
