import bpy
import traceback

def create_voronoi_nodes():
    group_name = "VoronoiCity_GN"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Interface ---
    # Helper to add sockets robustly for 4.0+
    def add_socket(name, type_str, default, min_v=None, max_v=None):
        # 4.0+ API
        if hasattr(ng, 'interface'):
            sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=type_str)
            sock.default_value = default
            if min_v is not None: sock.min_value = min_v
            if max_v is not None: sock.max_value = max_v
        else:
            # 3.6 API
            sock = ng.inputs.new(type_str, name)
            sock.default_value = default
            if min_v is not None: sock.min_value = min_v
            if max_v is not None: sock.max_value = max_v

    # Output Gemoetry
    if hasattr(ng, 'interface'):
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        ng.inputs.new('NodeSocketGeometry', 'Geometry')
        ng.outputs.new('NodeSocketGeometry', 'Geometry')

    # Add Params
    add_socket("Resolution", 'NodeSocketInt', 50, 2, 500)
    add_socket("Randomness", 'NodeSocketFloat', 0.8, 0.0, 1.0)
    add_socket("Road Gap", 'NodeSocketFloat', 0.1, 0.0, 0.99)
    add_socket("Min Height", 'NodeSocketFloat', 0.5, 0.1)
    add_socket("Max Height", 'NodeSocketFloat', 4.0, 0.1)
    add_socket("Seed", 'NodeSocketInt', 0)

    # --- Nodes ---
    nodes = ng.nodes
    links = ng.links
    
    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-1400, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (1200, 0)
    n_out.is_active_output = True
    
    # helper to find input index by checking length or defaults
    # Input Indices: 0:Geo, 1:Res, 2:Rand, 3:Gap, 4:MinH, 5:MaxH, 6:Seed
    
    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-1200, 0)
    n_grid.inputs[0].default_value = 20.0 # Size X
    n_grid.inputs[1].default_value = 20.0 # Size Y
    
    if len(n_in.outputs) > 1:
        links.new(n_in.outputs[1], n_grid.inputs[2]) # Vertices X
        links.new(n_in.outputs[1], n_grid.inputs[3]) # Vertices Y
    
    # 2. Randomness (Noise)
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1000, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-1200, -250)
    n_noise.inputs['Scale'].default_value = 10.0
    n_noise.noise_dimensions = '4D'
    if len(n_in.outputs) > 6:
        links.new(n_in.outputs[6], n_noise.inputs['W']) # Seed
    
    # Math: (Noise - 0.5) * Randomness
    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    links.new(n_noise.outputs[0], n_sub.inputs[0]) # Color -> Vector
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    links.new(n_sub.outputs[0], n_scale.inputs[0])
    if len(n_in.outputs) > 2:
        links.new(n_in.outputs[2], n_scale.inputs[3]) # Scale (Randomness)
    
    # Zero Z (Multiply by 1,1,0)
    n_mult = nodes.new('ShaderNodeVectorMath')
    n_mult.operation = 'MULTIPLY'
    n_mult.inputs[1].default_value = (1.0, 1.0, 0.0)
    links.new(n_scale.outputs[0], n_mult.inputs[0])
    
    links.new(n_grid.outputs[0], n_set_pos.inputs[0]) # Grid Mesh -> Geometry
    links.new(n_mult.outputs[0], n_set_pos.inputs[2]) # Offset
    
    # 3. Triangulate
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-800, 0)
    links.new(n_set_pos.outputs[0], n_tri.inputs[0])
    
    # 4. Dual Mesh
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-600, 0)
    links.new(n_tri.outputs[0], n_dual.inputs[0])
    
    # 5. Scale Elements (Road Gap)
    n_scale_elem = nodes.new('GeometryNodeScaleElements')
    n_scale_elem.location = (-400, 0)
    n_scale_elem.domain = 'FACE'
    
    # Gap calc: 1 - Gap
    n_sub_gap = nodes.new('ShaderNodeMath')
    n_sub_gap.operation = 'SUBTRACT'
    n_sub_gap.inputs[0].default_value = 1.0
    if len(n_in.outputs) > 3:
        links.new(n_in.outputs[3], n_sub_gap.inputs[1])
    
    links.new(n_dual.outputs[0], n_scale_elem.inputs[0]) # Geometry
    links.new(n_sub_gap.outputs[0], n_scale_elem.inputs[2]) # Scale
    
    # 6. Extrude
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-200, 0)
    links.new(n_scale_elem.outputs[0], n_ext.inputs[0])
    
    # Random Height
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-400, -300)
    if len(n_in.outputs) > 5:
        links.new(n_in.outputs[4], n_rand.inputs[0]) # Min
        links.new(n_in.outputs[5], n_rand.inputs[1]) # Max
        links.new(n_in.outputs[6], n_rand.inputs[8]) # Seed (Index 8 for integer seed usually, check socket list?) 
        # Actually random value node sockets vary by type. 
        # Float Min=0, Max=1, ID=2, Seed=3.
        # Let's rely on names for this node as it's complex or just use default links
        # Better: Safe Link by name
        try:
             links.new(n_in.outputs[4], n_rand.inputs['Min'])
             links.new(n_in.outputs[5], n_rand.inputs['Max'])
             links.new(n_in.outputs[6], n_rand.inputs['Seed'])
        except:
             pass
    
    # Extrude Offset Scale
    links.new(n_rand.outputs[0], n_ext.inputs[3]) # Offset Scale (usually index 3)
    
    # 7. Material
    n_mat = nodes.new('GeometryNodeSetMaterial')
    n_mat.location = (100, 0)
    links.new(n_ext.outputs[0], n_mat.inputs[0])
    
    # OUT
    links.new(n_mat.outputs[0], n_out.inputs[0])
    
    return ng

def create_scene():
    print("-" * 30)
    print("Creating Voronoi City (Fixed Version)...")
    
    # Clean previous
    if "CityVoronoi" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CityVoronoi"], do_unlink=True)
        
    mesh = bpy.data.meshes.new("CityVoronoiMesh")
    obj = bpy.data.objects.new("CityVoronoi", mesh)
    
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)
        
    bpy.context.view_layer.objects.active = obj
    
    # Material
    mat_name = "CityMat"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        # FIX: Use mat.node_tree, not mat.node_group
        if mat.node_tree:
             nodes = mat.node_tree.nodes
             bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
             if bsdf:
                 bsdf.inputs['Base Color'].default_value = (0.2, 0.2, 0.2, 1)

    obj.data.materials.append(mat)
    
    # Modifier
    try:
        ng = create_voronoi_nodes()
        mod = obj.modifiers.new("CityGen", 'NODES')
        mod.node_group = ng
        
        # Link Material to Node
        # We need to find the Set Material node and assign the material object to it
        set_mat = next((n for n in ng.nodes if n.type == 'SET_MATERIAL'), None)
        if set_mat:
            # Index 2 is usually the Material socket selection
            set_mat.inputs[2].default_value = mat
            
    except Exception as e:
        print(f"Error building nodes: {e}")
        traceback.print_exc()

    print("Success. Object 'CityVoronoi' created.")

if __name__ == "__main__":
    try:
        create_scene()
    except:
        traceback.print_exc()
