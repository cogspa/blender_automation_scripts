import bpy

def separate_city_to_objects():
    print("Separating City into Individual Objects...")
    
    obj = bpy.context.view_layer.objects.active
    if not obj or "City" not in obj.name:
        print("Please select the City object first.")
        # Try to find it
        for o in bpy.data.objects:
            if "City" in o.name:
                obj = o
                bpy.context.view_layer.objects.active = o
                obj.select_set(True)
                break
    
    if not obj:
        print("No City Object found.")
        return

    # 1. Apply Modifier
    print(f"Applying modifiers on {obj.name}...")
    try:
        bpy.ops.object.modifier_apply(modifier="CityGenV12") # Try specific name
    except:
        try:
            bpy.ops.object.modifier_apply(modifier="CityGenV11")
        except:
             # Just apply all
            for mod in obj.modifiers:
                bpy.ops.object.modifier_apply(modifier=mod.name)

    # 2. Separate by Loose Parts
    print("Separating by loose parts...")
    bpy.ops.mesh.separate(type='LOOSE')
    
    # 3. Rename Logic
    # The largest piece is likely the road (by bounds or vert count)
    print("Renaming parts...")
    selected_objects = bpy.context.selected_objects
    
    # Sort by volume/size roughly? or just iterate
    # Usually the Road layer has the most vertices/largest bbox
    best_road = None
    max_dim = 0
    
    buildings = []
    
    for o in selected_objects:
        # Calculate dimension magnitude
        dim = o.dimensions.length_squared
        if dim > max_dim:
            max_dim = dim
            best_road = o
        buildings.append(o)
        
    if best_road:
        best_road.name = "City_Roads"
        buildings.remove(best_road)
        
    for i, b in enumerate(buildings):
        b.name = f"City_Building_{i:03d}"
        
    print(f"Done! Created {len(buildings)} buildings and 1 road network.")

if __name__ == "__main__":
    separate_city_to_objects()
