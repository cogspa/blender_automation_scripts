import bpy
import random

def add_body_noise(target_name="Spider_Body"):
    print("--------------------------------------------------")
    print(f"ADDING RANDOM NOISE TO BODY: {target_name}")
    print("--------------------------------------------------")

    if target_name in bpy.data.objects:
        body = bpy.data.objects[target_name]
        
        # 1. Insert Initial Keyframes to create F-Curves
        # We need these to attach modifiers to.
        # Insert at 1 and 100 to enable a clear range (though noise works on infinite)
        body.keyframe_insert(data_path="location", frame=1)
        body.keyframe_insert(data_path="location", frame=100)
        body.keyframe_insert(data_path="rotation_euler", frame=1)
        body.keyframe_insert(data_path="rotation_euler", frame=100)
        
        # Ensure F-Curves are updated
        if body.animation_data and body.animation_data.action:
            action = body.animation_data.action
            
            # Helper to find F-Curves recursively for Blender 4.3+ Layered Actions
            all_fcurves = []
            
            def recursive_find_fcurves(obj, visited=None):
                if visited is None: visited = set()
                if obj in visited: return
                visited.add(obj)
                
                # Check directly if it has fcurves collection
                if hasattr(obj, 'fcurves'):
                    try:
                        for fc in obj.fcurves:
                            all_fcurves.append(fc)
                    except: pass
                
                # Recurse Attributes
                search_attrs = ['layers', 'strips', 'channelbags'] 
                for attr in search_attrs:
                    if hasattr(obj, attr):
                        try:
                            for item in getattr(obj, attr):
                                recursive_find_fcurves(item, visited)
                        except: pass

            recursive_find_fcurves(action)
            
            print(f"DEBUG: Found {len(all_fcurves)} F-Curves on Spider_Body action '{action.name}'.")

            # 2. Iterate F-Curves and Add Noise
            if not all_fcurves:
                 print("WARNING: No F-Curves found to apply noise to!")
            
            for fcurve in all_fcurves:
                print(f"  Processing Curve: {fcurve.data_path} [{fcurve.array_index}]")
                
                # Clear existing modifiers
                for m in fcurve.modifiers:
                    fcurve.modifiers.remove(m)
                    
                # Add Noise Modifier
                noise = fcurve.modifiers.new('NOISE')
                
                # Common settings
                noise.scale = 15.0
                noise.phase = random.uniform(0, 100) 
                noise.use_restricted_range = False 
                
                # Specific Settings based on Data Path
                if "location" in fcurve.data_path:
                     noise.strength = 1.0 # Back to 1.0 per user request
                     
                elif "rotation" in fcurve.data_path:
                    noise.strength = 0.4 
                
                # Ensure modifier is active/valid
                noise.show_expanded = False
                
                print(f"    -> Added NOISE: Scale={noise.scale}, Str={noise.strength:.2f}")

        print("Noise setup complete.")
    else:
        print("Error: Spider_Body not found.")

if __name__ == "__main__":
    add_body_noise()
