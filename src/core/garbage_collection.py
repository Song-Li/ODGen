from src.core.graph import Graph
from src.core.logger import loggers

def get_inside_reachable_childern(G, name_nodes):
    """
    give a list of name nodes, if a obj node only reachable by name nodes
    in the name_nodes list, this is a inside reachable childern. We will 
    return a list of inside reachable childern 
    """
    objs = []
    res = set()
    outside_reachable = False
    for name_node in name_nodes:
        objs += G.get_objs_by_name_node(name_node)
    for obj in set(objs):
        outside_reachable = False
        #if G.get_node_attr(obj).get('export'):
        #    continue
        reachable_name_nodes = G.get_name_nodes_to_obj(obj)
        for nn in reachable_name_nodes:
            if nn not in name_nodes:
                outside_reachable = True
        if not outside_reachable:
            res.add(obj)

    return res

def cleanup_scope(G, scope_node, exceptions=[]):
    """
    the cleanup of scopes is based on the scope node
    we will go through the name nodes of the scope, recursively,
    if a obj node is only referenced by the name nodes under the scope
    delete the obj node

    Args:
        scope_node (str): the scope node
    Returns:
        list: a list of removed nodes
    """
    child_name_nodes = G.get_all_child_name_nodes(scope_node) 
    #for nn in child_name_nodes:
    #    print(G.get_node_attr(nn))
    inside_objs = get_inside_reachable_childern(G, child_name_nodes)
    inside_objs = [obj for obj in inside_objs if obj not in exceptions]
    G.remove_nodes_from(list(inside_objs))
    G.num_removed += len(inside_objs)
    loggers.main_logger.info("removed {} for garbage collection".format(inside_objs))
