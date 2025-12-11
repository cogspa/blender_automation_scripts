import bpy
import traceback

def create_v7_nodes():
    group_name = "VoronoiCity_V7"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Interface ---
    def add_socket(name, type_str, default, min_v=None):
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

    add_socket("Resolution", 'NodeSocketInt', 150, 2)
    add_socket("Distortion", 'NodeSocketFloat', 5.0, 0.0)
    add_socket("Street Width", 'NodeSocketFloat', 0.9, 0.0)
    add_socket("Min Height", 'NodeSocketFloat', 0.5, 0.0)
    add_socket("Max Height", 'NodeSocketFloat', 6.0, 0.0)
    add_socket("Seed", 'NodeSocketInt', 123)

    nodes = ng.nodes
    links = ng.links
    
    # --- Robust Linker V7 (Fixed) ---
    def link_safe(from_s, to_node, idx_or_name=0):
        target = None
        # Try by Name
        if isinstance(idx_or_name, str):
            if idx_or_name in to_node.inputs:
                target = to_node.inputs[idx_or_name]
        # Try by Index
        elif isinstance(idx_or_name, int):
             if idx_or_name < len(to_node.inputs):
                 target = to_node.inputs[idx_or_name]
        
        # Fallback to Index 0 if we failed
        if not target and len(to_node.inputs) > 0:
            target = to_node.inputs[0]

        if target:
            links.new(from_s, target)

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-2000, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (2000, 0)
    n_out.is_active_output = True

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-1800, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(n_in.outputs[1], n_grid, 2)
    link_safe(n_in.outputs[1], n_grid, 3)
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1600, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-1800, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_safe(n_in.outputs[6], n_noise, 'W')

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs[0], n_sub, 0) # Color
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_safe(n_sub.outputs[0], n_scale, 0)
    link_safe(n_in.outputs[2], n_scale, 3) # Distortion Amt
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_safe(n_scale.outputs[0], n_flat, 0)
    
    link_safe(n_grid.outputs[0], n_set_pos, 0)
    link_safe(n_flat.outputs[0], n_set_pos, 2) # Offset
    
    # 3. Dual Mesh
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1400, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0)
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1200, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # 4. SPLIT EDGES
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1000, 0)
    link_safe(n_dual.outputs[0], n_split, 0)
    
    # 5. Capture ID
    n_store_id = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store_id.location = (-800, 0)
    n_store_id.data_type = 'INT'
    n_store_id.domain = 'FACE'
    n_store_id.name = "CellID"
    
    n_idx = nodes.new('GeometryNodeInputIndex')
    n_idx.location = (-1000, -200)
    
    link_safe(n_split.outputs[0], n_store_id, 0)
    link_safe(n_idx.outputs[0], n_store_id, 3) # Value
    
    # 6. Shrink Cells (Street Width)
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-600, 0)
    n_shrink.domain = 'FACE'
    
    link_safe(n_store_id.outputs[0], n_shrink, 0)
    link_safe(n_in.outputs[3], n_shrink, 2) # Street Width Scale
    
    # 7. EXTRUDE
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-300, 0)
    link_safe(n_shrink.outputs[0], n_ext, 0)
    
    # Random Height by CellID
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-600, -400)
    n_rand.data_type = 'FLOAT'
    
    n_read_id = nodes.new('GeometryNodeInputNamedAttribute')
    n_read_id.location = (-800, -400)
    n_read_id.data_type = 'INT'
    n_read_id.inputs[0].default_value = "CellID"
    
    link_safe(n_in.outputs[4], n_rand, 0) # Min
    link_safe(n_in.outputs[5], n_rand, 1) # Max
    link_safe(n_read_id.outputs[0], n_rand, 2) # ID
    link_safe(n_in.outputs[6], n_rand, 3) # Seed
    
    link_safe(n_rand.outputs[1], n_ext, 'Offset Scale') # Offset Scale is usually index 3 or named
    
    # 8. Material
    n_mat = nodes.new('GeometryNodeSetMaterial')
    n_mat.location = (0, 0)
    link_safe(n_ext.outputs[0], n_mat, 0)
    
    link_safe(n_mat.outputs[0], n_out, 0)
    return ng

def create_scene_v7():
    print("Creating Voronoi City V7 (Individual Prims)...")
    if "CityV7" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CityV7"], do_unlink=True)
        
    mesh = bpy.data.meshes.new("CityV7Mesh")
    obj = bpy.data.objects.new("CityV7", mesh)
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)
    
    m_bldg = bpy.data.materials.new("BldgMatV7")
    m_bldg.use_nodes = True
    m_bldg.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.8, 0.4, 0.1, 1)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    
    try:
        ng = create_v7_nodes()
        mod = obj.modifiers.new("CityGenV7", 'NODES')
        mod.node_group = ng
        
        for n in ng.nodes:
            if n.type == 'SET_MATERIAL':
                n.inputs[2].default_value = m_bldg
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    create_scene_v7()
