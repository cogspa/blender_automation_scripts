import bpy
import bmesh
import math

"""
WIRE GENERATOR
==============
Converts selected edges into tubular wires with optional sag.

USAGE:
1. Select a mesh object
2. Enter Edit Mode
3. Select edges you want to convert to wires (edge loops work great)
4. Run this script

PARAMETERS (adjust below):
- WIRE_RADIUS: Thickness of the wire
- WIRE_RESOLUTION: Smoothness of the circular profile
- SUBDIVISIONS: Number of segments along wire (more = smoother sag)
- SAG_AMOUNT: How much the wire droops (0 = straight, 0.5 = heavy sag)
- SEPARATE_OBJECT: Create wires as new object or add to existing
- WIRE_MATERIAL_NAME: Name for wire material (created if doesn't exist)
"""

# =====================
# PARAMETERS - Adjust these
# =====================
WIRE_RADIUS = 0.015
WIRE_RESOLUTION = 8
SUBDIVISIONS = 8
SAG_AMOUNT = 0.3  # 0 = no sag, higher = more droop
SEPARATE_OBJECT = True
WIRE_MATERIAL_NAME = "Wire_Material"
WIRE_COLOR = (0.1, 0.1, 0.1, 1)  # Dark gray/black


def get_selected_edges_as_coords(obj):
    """Extract world-space coordinates of selected edge endpoints"""
    # Ensure we are in object mode to read proper data if we aren't editing
    # But if we are in EDIT mode, we verify selection from BMesh
    
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        bm.select_flush(True) # Ensure selection state is current
    else:
        # If in Object mode, we can read directly if we trust the selection state
        # But usually selection state is only valid if we were in edit mode nicely.
        # Let's switch to edit mode briefly to get bmesh or read from mesh directly
        bm = bmesh.new()
        bm.from_mesh(obj.data)
    
    edges_data = []
    for edge in bm.edges:
        if edge.select:
            # Get world space coordinates
            v1 = obj.matrix_world @ edge.verts[0].co
            v2 = obj.matrix_world @ edge.verts[1].co
            edges_data.append((v1.copy(), v2.copy()))
    
    if obj.mode != 'EDIT':
        bm.free()
    
    return edges_data


def create_wire_curve(edges_data, name="WireCurve"):
    """Create a curve object from edge data with sag"""
    # Create curve data
    curve_data = bpy.data.curves.new(name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12
    curve_data.bevel_depth = WIRE_RADIUS
    curve_data.bevel_resolution = WIRE_RESOLUTION
    
    for i, (start, end) in enumerate(edges_data):
        # Create a new spline for each wire segment
        spline = curve_data.splines.new('POLY')
        
        # Calculate intermediate points with sag
        num_points = SUBDIVISIONS + 1
        spline.points.add(num_points - 1)  # Already has 1 point
        
        for j in range(num_points):
            t = j / (num_points - 1)
            
            # Linear interpolation
            x = start.x + t * (end.x - start.x)
            y = start.y + t * (end.y - start.y)
            z = start.z + t * (end.z - start.z)
            
            # Add parabolic sag: 4 * t * (1-t) peaks at 0.5
            wire_length = (end - start).length
            sag = SAG_AMOUNT * wire_length * 4 * t * (1 - t)
            z -= sag
            
            spline.points[j].co = (x, y, z, 1)  # w=1 for POLY splines
    
    # Create object
    curve_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    return curve_obj


def create_wire_material():
    """Create or get wire material (Safe for Blender 4.0+)"""
    if WIRE_MATERIAL_NAME in bpy.data.materials:
        return bpy.data.materials[WIRE_MATERIAL_NAME]
    
    mat = bpy.data.materials.new(WIRE_MATERIAL_NAME)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    
    if bsdf:
        bsdf.inputs[0].default_value = WIRE_COLOR
        
        # Check for Metallic/Roughness sockets properly
        for socket in bsdf.inputs:
            if socket.name == 'Metallic':
                socket.default_value = 0.8
            elif socket.name == 'Roughness':
                socket.default_value = 0.4
    
    mat.diffuse_color = WIRE_COLOR
    return mat


def convert_curve_to_mesh(curve_obj):
    """Convert curve to mesh for more control"""
    # Select and convert
    bpy.ops.object.select_all(action='DESELECT')
    curve_obj.select_set(True)
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.convert(target='MESH')
    return curve_obj


def main():
    print("-" * 30)
    print("Running Wire Generator...")
    # Check we have an active mesh object
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("Error: Please select a mesh object")
        return
    
    # Store current mode
    original_mode = obj.mode
    print(f"Active Object: {obj.name} (Mode: {original_mode})")
    
    # Get selected edges
    # Note: If object is purely procedural (modifiers only), we might need to apply them to see edges
    # But usually this script implies working on a real mesh.
    
    edges_data = get_selected_edges_as_coords(obj)
    
    if not edges_data:
        print("Warning: No edges selected.")
        print("  - If this is a procedural object, apply modifiers first.")
        print("  - If in Edit Mode, ensure edges are selected.")
        return
    
    print(f"Found {len(edges_data)} selected edges. Creating wires...")
    
    # Return to object mode to create new objects
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Create wire curve
    wire_curve = create_wire_curve(edges_data, name="Manual_Wires")
    
    # Apply material
    wire_mat = create_wire_material()
    wire_curve.data.materials.append(wire_mat)
    
    # Optionally convert to mesh
    # convert_curve_to_mesh(wire_curve)
    
    print(f"Created wire object: {wire_curve.name}")
    print(f"  - {len(edges_data)} wire segments")
    print(f"  - Radius: {WIRE_RADIUS}")
    print(f"  - Sag: {SAG_AMOUNT}")
    
    # Select the new wire object
    bpy.ops.object.select_all(action='DESELECT')
    wire_curve.select_set(True)
    bpy.context.view_layer.objects.active = wire_curve
    
    # Restore mode if desired, but usually we stay in Object mode to see result
    # bpy.ops.object.mode_set(mode=original_mode)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
