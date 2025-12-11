import bpy
import traceback

def create_v6_nodes():
    # --- Clean Start ---
    group_name = "VoronoiCity_V6"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Interface ---
    def add_socket(name, type_str, default, min_v=None, max_v=None):
        if hasattr(ng, 'interface'):
            sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=type_str)
            sock.default_value = default
            if min_v is not None: sock.min_value = min_v
        else:
            sock = ng.inputs.new(type_str, name)
            sock.default_value = default

    if hasattr(ng, 'interface'):
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        ng.inputs.new('NodeSocketGeometry', 'Geometry')
        ng.outputs.new('NodeSocketGeometry', 'Geometry')

    add_socket("Resolution", 'NodeSocketInt', 40, 2)
    add_socket("Distortion", 'NodeSocketFloat', 5.0, 0.0)
    add_socket("Inset Amount", 'NodeSocketFloat', 0.15, 0.0, 0.9)
    add_socket("Height Scale", 'NodeSocketFloat', 0.12)
    add_socket("Height Amp", 'NodeSocketFloat', 8.0)
    add_socket("Seed", 'NodeSocketInt', 123)

    nodes = ng.nodes
    links = ng.links
    
    # --- THE ROBUST LINKER ---
    def link_safe(from_s, to_node, preferred_idx_or_name=0):
        target = None
        # 1. Try by Name
        if isinstance(preferred_idx_or_name, str):
            if preferred_idx_or_name in to_node.inputs:
                target = to_node.inputs[preferred_idx_or_name]
        
        # 2. Try by Index
        if not target and isinstance(preferred_idx_or_name, int):
             if preferred_idx_or_name < len(to_node.inputs):
                 target = to_node.inputs[preferred_idx_or_name]

        # 3. Fallback: Find FIRST compatible type? 
        # For now, if we fail, we try index 0 (Geometry) which works for most geo nodes
        if not target and len(to_node.inputs) > 0:
            target = to_node.inputs[0]

        if target:
            links.new(from_s, target)
        else:
            print(f"FAILED to link to {to_node.name}")

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-1800, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (1800, 0)
    n_out.is_active_output = True

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-1600, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(n_in.outputs[1], n_grid, 2) # Res X
    link_safe(n_in.outputs[1], n_grid, 3) # Res Y
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1400, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-1600, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_safe(n_in.outputs[6], n_noise, 'W')

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs['Color'], n_sub, 0)
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_safe(n_sub.outputs[0], n_scale, 0)
    link_safe(n_in.outputs[2], n_scale, 3) # Distortion Amt
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_safe(n_scale.outputs[0], n_flat, 0)
    
    link_safe(n_grid.outputs[0], n_set_pos, 0) # Geometry is usually index 0!
    link_safe(n_flat.outputs[0], n_set_pos, 'Offset') # Offset is usually named Offset
    
    # 3. Voronoi Core (Triangulate -> Dual Mesh)
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1200, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0) # Index 0 is always Mesh/Geometry
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1000, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # 4. Inset (Buildings)
    n_inset = nodes.new('GeometryNodeScaleElements')
    n_inset.location = (-800, 200)
    n_inset.domain = 'FACE'
    
    n_math_gap = nodes.new('ShaderNodeMath')
    n_math_gap.operation = 'SUBTRACT'
    n_math_gap.inputs[0].default_value = 1.0
    link_safe(n_in.outputs[3], n_math_gap, 1) # Inset
    
    link_safe(n_dual.outputs[0], n_inset, 0)
    link_safe(n_math_gap.outputs[0], n_inset, 'Scale')
    
    # 5. Extrude
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-500, 200)
    link_safe(n_inset.outputs[0], n_ext, 0)
    
    # Height Noise
    n_h_noise = nodes.new('ShaderNodeTexNoise')
    n_h_noise.location = (-800, 500)
    link_safe(n_in.outputs[6], n_h_noise, 'W')
    link_safe(n_in.outputs[4], n_h_noise, 'Scale')
    
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (-1000, 500)
    link_safe(n_pos.outputs[0], n_h_noise, 'Vector')
    
    n_h_mult = nodes.new('ShaderNodeMath')
    n_h_mult.operation = 'MULTIPLY'
    link_safe(n_h_noise.outputs[0], n_h_mult, 0) # Factor
    link_safe(n_in.outputs[5], n_h_mult, 1) # Amp
    
    n_h_add = nodes.new('ShaderNodeMath')
    n_h_add.operation = 'ADD'
    n_h_add.inputs[1].default_value = 0.5
    link_safe(n_h_mult.outputs[0], n_h_add, 0)
    
    link_safe(n_h_add.outputs[0], n_ext, 'Offset Scale')
    
    # Materials
    n_mat_b = nodes.new('GeometryNodeSetMaterial')
    n_mat_b.location = (-200, 200)
    n_mat_b.label = "Set Building Material"
    link_safe(n_ext.outputs[0], n_mat_b, 0)
    
    # 6. Roads
    n_mat_r = nodes.new('GeometryNodeSetMaterial')
    n_mat_r.location = (-200, -200)
    n_mat_r.label = "Set Road Material"
    
    n_trans_r = nodes.new('GeometryNodeTransform')
    n_trans_r.location = (-400, -200)
    n_trans_r.inputs['Translation'].default_value = (0, 0, -0.01)
    
    link_safe(n_dual.outputs[0], n_trans_r, 0)
    link_safe(n_trans_r.outputs[0], n_mat_r, 0)
    
    # 7. Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (200, 0)
    link_safe(n_mat_r.outputs[0], n_join, 0)
    link_safe(n_mat_b.outputs[0], n_join, 0)
    
    link_safe(n_join.outputs[0], n_out, 0)
    return ng

def create_scene_v6():
    print("-" * 30)
    print("Creating Voronoi City V6 (Safe Index Linking)...")
    if "CityV6" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CityV6"], do_unlink=True)
        
    mesh = bpy.data.meshes.new("CityV6Mesh")
    obj = bpy.data.objects.new("CityV6", mesh)
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)
    
    m_road = bpy.data.materials.new("RoadMatV6")
    m_road.use_nodes = True
    m_road.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

    m_bldg = bpy.data.materials.new("BldgMatV6")
    m_bldg.use_nodes = True
    m_bldg.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.1, 0.3, 0.8, 1)
    
    obj.data.materials.append(m_road)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    
    try:
        ng = create_v6_nodes()
        mod = obj.modifiers.new("CityGenV6", 'NODES')
        mod.node_group = ng
        
        for n in ng.nodes:
            if n.type == 'SET_MATERIAL':
                if "Road" in n.label: n.inputs[2].default_value = m_road
                if "Building" in n.label: n.inputs[2].default_value = m_bldg
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    create_scene_v6()
