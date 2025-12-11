import bpy
import traceback

def set_socket_value(node, socket_names, value):
    """Helper to set value on first matching socket name."""
    if isinstance(socket_names, str):
        socket_names = [socket_names]
        
    for name in socket_names:
        if name in node.inputs:
            # Check if it's a vector
            if node.inputs[name].type == 'VECTOR':
                # If value is scalar, set all 3
                if isinstance(value, (int, float)):
                     node.inputs[name].default_value = (value, value, value)
                else:
                     node.inputs[name].default_value = value
            else:
                node.inputs[name].default_value = value
            return True
    return False

def create_city_generator_group():
    group_name = "CityGenerator"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Interface ---
    is_4_0_plus = bpy.app.version >= (4, 0, 0)
    
    if is_4_0_plus:
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        
        s = ng.interface.new_socket("City Scale", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 5.0
        s = ng.interface.new_socket("Road Width", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 0.1
        s = ng.interface.new_socket("Building Density", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 10.0
        s = ng.interface.new_socket("Min Height", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 0.5
        s = ng.interface.new_socket("Max Height", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 3.0
        
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        # Legacy
        ng.inputs.new('NodeSocketGeometry', 'Geometry')
        # ... (simplified legacy fallback, assuming valid vars)
        ng.inputs.new('NodeSocketFloat', 'City Scale').default_value = 5.0
        ng.inputs.new('NodeSocketFloat', 'Road Width').default_value = 0.1
        ng.inputs.new('NodeSocketFloat', 'Building Density').default_value = 10.0
        ng.inputs.new('NodeSocketFloat', 'Min Height').default_value = 0.5
        ng.inputs.new('NodeSocketFloat', 'Max Height').default_value = 3.0
        ng.outputs.new('NodeSocketGeometry', 'Geometry')

    # --- Nodes ---
    nodes = ng.nodes
    links = ng.links
    
    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-1200, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (1000, 0)
    n_out.is_active_output = True
    
    # 1. Subdivide
    n_subdiv = nodes.new('GeometryNodeSubdivideMesh')
    n_subdiv.location = (-1000, 0)
    n_subdiv.inputs['Level'].default_value = 5
    links.new(n_in.outputs['Geometry'], n_subdiv.inputs['Mesh'])
    
    # 2. Voronoi
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (-1000, 300)
    
    n_voronoi = nodes.new('ShaderNodeTexVoronoi')
    n_voronoi.location = (-800, 300)
    n_voronoi.voronoi_dimensions = '2D'
    n_voronoi.feature = 'DISTANCE_TO_EDGE'
    
    # Input mapping: [Geo, Scale, Road, Density, MinH, MaxH]
    # Use indices to be safe against name changes
    links.new(n_in.outputs[1], n_voronoi.inputs['Scale'])
    links.new(n_pos.outputs['Position'], n_voronoi.inputs['Vector'])
    
    # 3. Math (Less Than)
    n_less = nodes.new('ShaderNodeMath')
    n_less.location = (-600, 300)
    n_less.operation = 'LESS_THAN'
    links.new(n_voronoi.outputs['Distance'], n_less.inputs[0])
    links.new(n_in.outputs[2], n_less.inputs[1]) # Road Width
    
    # 4. Separate
    n_sep = nodes.new('GeometryNodeSeparateGeometry')
    n_sep.location = (-600, 0)
    links.new(n_subdiv.outputs['Mesh'], n_sep.inputs['Geometry'])
    links.new(n_less.outputs['Value'], n_sep.inputs['Selection'])
    
    # 5. Distribute
    n_dist = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist.location = (-300, 0)
    n_dist.distribute_method = 'POISSON'
    n_dist.inputs['Distance Min'].default_value = 0.4
    links.new(n_sep.outputs['Inverted'], n_dist.inputs['Mesh'])
    links.new(n_in.outputs[3], n_dist.inputs['Density Max']) # Density
    
    # 6. Random Height
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-300, -300)
    links.new(n_in.outputs[4], n_rand.inputs['Min']) # Min H
    links.new(n_in.outputs[5], n_rand.inputs['Max']) # Max H
    
    n_comb = nodes.new('ShaderNodeCombineXYZ')
    n_comb.location = (-100, -300)
    n_comb.inputs['X'].default_value = 1.0
    n_comb.inputs['Y'].default_value = 1.0
    links.new(n_rand.outputs['Value'], n_comb.inputs['Z'])
    
    # 7. Instance Cube [THE FIX]
    n_cube = nodes.new('GeometryNodeMeshCube')
    n_cube.location = (-100, 200)
    
    # Try different socket names for Size
    # In 4.0+, it is often 'Size' (Vector), but sometimes split.
    # We check keys.
    if 'Size' in n_cube.inputs:
        n_cube.inputs['Size'].default_value = (0.5, 0.5, 1.0)
    elif 'Size X' in n_cube.inputs:
        n_cube.inputs['Size X'].default_value = 0.5
        n_cube.inputs['Size Y'].default_value = 0.5
    else:
        # Fallback: Print keys to debug if it fails again
        print(f"DEBUG: Cube inputs are: {n_cube.inputs.keys()}")
    
    n_inst = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst.location = (200, 0)
    links.new(n_dist.outputs['Points'], n_inst.inputs['Points'])
    links.new(n_cube.outputs['Mesh'], n_inst.inputs['Instance'])
    links.new(n_comb.outputs['Vector'], n_inst.inputs['Scale'])
    
    # 8. Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (500, 0)
    links.new(n_sep.outputs['Selection'], n_join.inputs['Geometry'])
    links.new(n_inst.outputs['Instances'], n_join.inputs['Geometry'])
    
    # Output
    links.new(n_join.outputs['Geometry'], n_out.inputs[0])
    
    return ng

def create_city():
    print("-" * 30)
    print("Creating City (Robust Version 2)...")
    
    if "CityPlane" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CityPlane"], do_unlink=True)
        
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))
    obj = bpy.context.active_object
    obj.name = "CityPlane"
    
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)

    try:
        ng = create_city_generator_group()
    except Exception as e:
        print(f"FAILED to build node tree: {e}")
        traceback.print_exc()
        return

    mod = obj.modifiers.new(name="CityGen", type='NODES')
    mod.node_group = ng
    print("Success. Modifier added.")

if __name__ == "__main__":
    try:
        create_city()
    except Exception:
        traceback.print_exc()
