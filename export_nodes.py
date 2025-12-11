import bpy
import json
import os

def export_active_modifier_nodes():
    # 1. Get Active Object
    obj = bpy.context.active_object
    if not obj:
        print("No active object found.")
        return

    # 2. Find Geometry Nodes Modifier
    mod = None
    for m in obj.modifiers:
        if m.type == 'NODES':
            mod = m
            break
    
    if not mod or not mod.node_group:
        print(f"Object '{obj.name}' has no Geometry Nodes modifier.")
        return

    ng = mod.node_group
    
    # 3. Serialize Nodes
    nodes_data = []
    for node in ng.nodes:
        node_info = {
            "name": node.name,
            "type": node.type,
            "label": node.label,
            "location": [node.location.x, node.location.y],
            "width": node.width,
            "inputs": [],
            "outputs": []
        }
        
        # Sockets
        for i, sock in enumerate(node.inputs):
             node_info["inputs"].append({
                 "index": i,
                 "name": sock.name,
                 "type": sock.type,
                 # "default_value": str(sock.default_value) # Complex types make this hard to serialze genericallly
             })
             
        for i, sock in enumerate(node.outputs):
             node_info["outputs"].append({
                 "index": i,
                 "name": sock.name,
                 "type": sock.type
             })
             
        nodes_data.append(node_info)

    # 4. Serialize Links
    links_data = []
    for link in ng.links:
        links_data.append({
            "from_node": link.from_node.name,
            "from_socket": link.from_socket.name,
            "to_node": link.to_node.name,
            "to_socket": link.to_socket.name
        })

    # 5. Interface (Inputs/Outputs of the group)
    interface_data = {
        "inputs": [],
        "outputs": []
    }
    
    # Handle 4.0 interface vs 3.x inputs
    if hasattr(ng, 'interface'):
        # 4.0+
        for item in ng.interface.items_tree:
            if item.item_type == 'SOCKET':
                target_list = interface_data["inputs"] if item.in_out == 'INPUT' else interface_data["outputs"]
                target_list.append({"name": item.name, "type": item.socket_type})
    else:
        # 3.x
        for sock in ng.inputs:
            interface_data["inputs"].append({"name": sock.name, "type": sock.type})
        for sock in ng.outputs:
            interface_data["outputs"].append({"name": sock.name, "type": sock.type})

    # 6. Assemble
    export_data = {
        "name": ng.name,
        "blender_version": bpy.app.version_string,
        "interface": interface_data,
        "nodes": nodes_data,
        "links": links_data
    }
    
    # 7. Save
    # Save to the same folder as this script (blender_bridge)
    out_path = "/Users/joem/.gemini/antigravity/scratch/blender_bridge/geonodes_export.json"
    
    with open(out_path, 'w') as f:
        json.dump(export_data, f, indent=2)
        
    print(f"Successfully exported Geometry Nodes to: {out_path}")

if __name__ == "__main__":
    export_active_modifier_nodes()
