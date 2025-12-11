import bpy
import traceback

def create_scene_v8():
    # --- 1. RESET SCENE ---
    print("-" * 30)
    print("RESETTING SCENE + Creating V8...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for c in bpy.data.collections:
        bpy.data.collections.remove(c)
        
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    # --- 2. NODE TREE ---
    group_name = "VoronoiCity_V8"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # helper for Interface
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
    
    # Robust Linker that PRINTS failures
    def link_safe(from_s, to_node, idx_or_name=0):
        target = None
        if isinstance(idx_or_name, str):
            if idx_or_name in to_node.inputs: target = to_node.inputs[idx_or_name]
        elif isinstance(idx_or_name, int):
             if idx_or_name < len(to_node.inputs): target = to_node.inputs[idx_or_name]
        
        # Fallback to 0 if standard geom node
        if not target and len(to_node.inputs) > 0:
            # Only do this if we suspect it's a geometry node logic
            # e.g. NodeTriangulate input 0 is Geometry
            target = to_node.inputs[0]

        if target:
            links.new(from_s, target)
        else:
            print(f"!!! FAILED LINK: {to_node.name} Socket {idx_or_name}")

    # Start constructing
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
    
    # 2. Distortion Logic
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1600, 0)
    
    # Noise -> Subtract 0.5 -> Scale -> Flatten Z -> Offset
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-2000, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_safe(n_in.outputs[6], n_noise, 'W')

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs[0], n_sub, 0)
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_safe(n_sub.outputs[0], n_scale, 0)
    link_safe(n_in.outputs[2], n_scale, 3) # Distortion Param
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_safe(n_scale.outputs[0], n_flat, 0)
    
    # Link Grid -> Set Pos
    link_safe(n_grid.outputs[0], n_set_pos, 0)
    # Link Vector -> Set Pos Offset
    # Offset is typically index 2 ("Offset") or 3 depending on Blender ver
    # 4.0: Geometry, Selection, Position, Offset (Index 3)
    # 3.6: Geometry, Selection, Position, Offset (Index 3)
    # Wait, usually it is Geometry(0), Selection(1), Position(2), Offset(3).
    # But named check is safest.
    link_safe(n_flat.outputs[0], n_set_pos, "Offset")
    
    # 3. Voronoi Creation
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1400, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0)
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1200, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # 4. SPLIT
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1000, 0)
    link_safe(n_dual.outputs[0], n_split, 0)
    
    # 5. INSET (Street Width)
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-800, 0)
    n_shrink.domain = 'FACE'
    
    link_safe(n_split.outputs[0], n_shrink, 0) # Geometry
    link_safe(n_in.outputs[3], n_shrink, 2) # Scale
    
    # 6. EXTRUDE (Height)
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-500, 0)
    link_safe(n_shrink.outputs[0], n_ext, 0)
    
    # Random Height Logic
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-800, -400)
    n_rand.data_type = 'FLOAT'
    
    # Index Node
    n_idx = nodes.new('GeometryNodeInputIndex')
    n_idx.location = (-1000, -400)
    
    link_safe(n_in.outputs[4], n_rand, 0) # Min
    link_safe(n_in.outputs[5], n_rand, 1) # Max
    link_safe(n_idx.outputs[0], n_rand, 2) # ID
    link_safe(n_in.outputs[6], n_rand, 3) # Seed
    
    # Offset Scale input for Extrude
    # Usually index 3 ("Offset Scale")
    link_safe(n_rand.outputs[1], n_ext, "Offset Scale")
    
    # 7. Material
    n_mat = nodes.new('GeometryNodeSetMaterial')
    n_mat.location = (-200, 0)
    link_safe(n_ext.outputs[0], n_mat, 0)
    
    # OUTPUT
    link_safe(n_mat.outputs[0], n_out, 0)


    # --- 3. OBJECT CREATION ---
    mesh = bpy.data.meshes.new("CityV8Mesh")
    obj = bpy.data.objects.new("CityV8", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    m_bldg = bpy.data.materials.new("BldgMatV8")
    m_bldg.use_nodes = True
    m_bldg.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.1, 0.4, 0.9, 1)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV8", 'NODES')
    mod.node_group = ng
    
    # Assign material input
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            n.inputs[2].default_value = m_bldg

    print("V8 Success.")

if __name__ == "__main__":
    try:
        create_scene_v8()
    except Exception as e:
        print(f"Crash: {e}")
        traceback.print_exc()
