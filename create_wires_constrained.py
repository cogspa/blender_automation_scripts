import bpy
import bmesh
import math
import random
from mathutils import Vector

"""
CONSTRAINED WIRE GENERATOR (FIXED)
==================================
Creates wires between rooftop vertices that stay connected
when you modify the building geometry.

NOTE: This script works best on REAL MESH objects.
If using with Geometry Nodes, you must APPLY the modifier first!

HOW IT WORKS:
1. Finds vertices on rooftop faces
2. Creates empties attached to those vertices (Vertex Parent)
   * ERROR FIX: Now correctly zeros local location so they match vertex position
3. Creates curves between empties with Hooks

USAGE:
1. Select a mesh object (Apply modifiers if procedural!)
2. Run this script
"""

# =====================
# PARAMETERS
# =====================
NUM_WIRE_POINTS = 15          # Max vertices to sample for wire endpoints
MAX_WIRE_DISTANCE = 10.0      # Max distance between connected points
MIN_WIRE_DISTANCE = 2.0       # Min distance (avoid very short wires)
WIRE_RADIUS = 0.015
SUBDIVISIONS = 8              # Curve smoothness
SAG_AMOUNT = 0.2              # Wire droop
ROOF_NORMAL_THRESHOLD = 0.7   # Normal.z > this = rooftop
ROOF_HEIGHT_PERCENTILE = 0.5  # Use vertices in top X% of height
MAX_CONNECTIONS_PER_POINT = 2
RANDOM_SEED = None
WIRE_MATERIAL_NAME = "Wire_Material"
WIRE_COLOR = (0.08, 0.08, 0.08, 1)
EMPTY_SIZE = 0.2              # Increased size for visibility
HIDE_EMPTIES = False          # Show them so user can debug positions


def get_rooftop_vertices(obj):
    """Find vertices that belong to rooftop (upward-facing) faces"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # Find height range
    all_z = [v.co.z for v in bm.verts]
    if not all_z:
        bm.free()
        return []
    
    min_z, max_z = min(all_z), max(all_z)
    height_threshold = min_z + (max_z - min_z) * ROOF_HEIGHT_PERCENTILE
    
    # Find vertices on rooftop faces
    rooftop_vert_indices = set()
    
    for face in bm.faces:
        if face.normal.z > ROOF_NORMAL_THRESHOLD:
            # Check face center height
            face_center_z = sum(v.co.z for v in face.verts) / len(face.verts)
            if face_center_z > height_threshold:
                for v in face.verts:
                    rooftop_vert_indices.add(v.index)
    
    # Get world-space positions for sorting/distance logic only
    rooftop_verts = []
    for idx in rooftop_vert_indices:
        v = bm.verts[idx]
        world_pos = obj.matrix_world @ v.co
        rooftop_verts.append({
            'index': idx,
            'local_co': v.co.copy(),
            'world_co': world_pos,
        })
    
    bm.free()
    return rooftop_verts


def sample_vertices(vertices, num_samples):
    if len(vertices) <= num_samples:
        return vertices
    return random.sample(vertices, num_samples)


def find_wire_connections(vertices, max_dist, min_dist):
    connections = []
    connection_count = {i: 0 for i in range(len(vertices))}
    potential = []
    
    for i, v1 in enumerate(vertices):
        for j, v2 in enumerate(vertices):
            if i >= j: continue
            dist = (v1['world_co'] - v2['world_co']).length
            if min_dist <= dist <= max_dist:
                potential.append((dist, i, j))
    
    potential.sort(key=lambda x: x[0])
    
    for dist, i, j in potential:
        if (connection_count[i] < MAX_CONNECTIONS_PER_POINT and
            connection_count[j] < MAX_CONNECTIONS_PER_POINT):
            connections.append((i, j))
            connection_count[i] += 1
            connection_count[j] += 1
            
    return connections


def create_vertex_parented_empty(obj, vert_index, name, collection):
    """Create an empty attached exactly to a vertex"""
    # Create empty
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = 'SPHERE'
    empty.empty_display_size = EMPTY_SIZE
    collection.objects.link(empty)
    
    # Parent FIRST
    empty.parent = obj
    empty.parent_type = 'VERTEX'
    empty.parent_vertices = [vert_index, 0, 0]
    
    # Reset location to (0,0,0) so it sits exactly on the parent vertex
    empty.location = (0, 0, 0)
    
    if HIDE_EMPTIES:
        empty.hide_viewport = True
    
    return empty


def create_wire_curve_with_hooks(empty_start, empty_end, name, collection):
    """Create a curve between two empties with hook modifiers"""
    
    # Calculate initial positions in WORLD space (for curve creation)
    # The empties are now correctly placed
    start_pos = empty_start.matrix_world.translation.copy()
    end_pos = empty_end.matrix_world.translation.copy()
    wire_length = (end_pos - start_pos).length
    
    # Create curve
    curve_data = bpy.data.curves.new(name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12
    curve_data.bevel_depth = WIRE_RADIUS
    curve_data.bevel_resolution = 4
    
    spline = curve_data.splines.new('POLY')
    num_points = SUBDIVISIONS + 2
    spline.points.add(num_points - 1)
    
    for i in range(num_points):
        t = i / (num_points - 1)
        # Linear interpolation
        pos = start_pos.lerp(end_pos, t)
        # Sag
        if 0 < i < num_points - 1:
            sag = SAG_AMOUNT * wire_length * 4 * t * (1 - t)
            pos.z -= sag
        
        spline.points[i].co = (pos.x, pos.y, pos.z, 1)
    
    curve_obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(curve_obj)
    
    # Hook Start
    hook_start = curve_obj.modifiers.new(name="Hook_Start", type='HOOK')
    hook_start.object = empty_start
    
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.select_all(action='DESELECT')
    
    # Assign hook start
    curve_data.splines[0].points[0].select = True
    bpy.ops.object.hook_assign(modifier="Hook_Start")
    bpy.ops.curve.select_all(action='DESELECT')
    
    # Assign hook end
    curve_data.splines[0].points[-1].select = True
    bpy.ops.object.mode_set(mode='OBJECT')
    hook_end = curve_obj.modifiers.new(name="Hook_End", type='HOOK')
    hook_end.object = empty_end
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.hook_assign(modifier="Hook_End")
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return curve_obj


def create_wire_material():
    if WIRE_MATERIAL_NAME in bpy.data.materials:
        return bpy.data.materials[WIRE_MATERIAL_NAME]
    
    mat = bpy.data.materials.new(WIRE_MATERIAL_NAME)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs[0].default_value = WIRE_COLOR
    mat.diffuse_color = WIRE_COLOR
    return mat


def main():
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
    
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("Error: Please select a mesh object")
        return
    
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Analyzing mesh: {obj.name}")
    
    # Find rooftop vertices
    rooftop_verts = get_rooftop_vertices(obj)
    
    if not rooftop_verts:
        print("Error: No rooftop vertices found. Did you apply modifiers?")
        return
    
    print(f"Found {len(rooftop_verts)} rooftop vertices")
    
    # Sample subset
    sampled_verts = sample_vertices(rooftop_verts, NUM_WIRE_POINTS)
    print(f"Sampled {len(sampled_verts)} vertices")
    
    # Find connections
    connections = find_wire_connections(sampled_verts, MAX_WIRE_DISTANCE, MIN_WIRE_DISTANCE)
    
    if not connections:
        print("Error: No connections found.")
        return
    
    print(f"Creating {len(connections)} wires")
    
    # Create collections
    col_name = "Wire_System_Fixed"
    if col_name not in bpy.data.collections:
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
    else:
        col = bpy.data.collections[col_name]
        
    # Create empties
    empties = {}
    used_indices = set()
    for i, j in connections:
        used_indices.add(i)
        used_indices.add(j)
        
    for idx in used_indices:
        vert = sampled_verts[idx]
        # FIXED PARENTING LOGIC
        empty = create_vertex_parented_empty(obj, vert['index'], f"Anchor_{vert['index']}", col)
        empties[idx] = empty
        
    # Force update to ensure empty positions are correct before curve creation
    bpy.context.view_layer.update()
    
    # Create wires
    wire_mat = create_wire_material()
    for i, j in connections:
        curve = create_wire_curve_with_hooks(empties[i], empties[j], "BoundWire", col)
        curve.data.materials.append(wire_mat)
    
    print("Done! Wires created.")

if __name__ == "__main__":
    main()
