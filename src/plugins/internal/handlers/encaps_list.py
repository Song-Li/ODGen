from src.core.graph import Graph 
from src.core.utils import ExtraInfo, NodeHandleResult, BranchTagContainer
from src.plugins.internal.utils import get_df_callback
from src.plugins.handler import Handler
from src.core.helpers import to_values, to_obj_nodes, val_to_str, wildcard
from src.core.helpers import add_contributes_to
from src.core.logger import loggers, ATTENTION
import os

class HandleEncapsList(Handler):
    """
    the var type handler including 
    AST_VAR, AST_CONST, AST_NAME
    """
    def process(self):
        return handle_template(self.G, 
                self.node_id, self.extra)

def handle_template(G: Graph, ast_node, extra=ExtraInfo()):
    '''
    Handle template strings by DFS. Be aware of possible possibility
    explosion. The number of possibilites is the product of the number
    of each element.
    Args:
        G (Graph): Graph.
        ast_node: AST node of the template string.
        extra (ExtraInfo, optional): Extra info
    Returns:
        list, set: List of result objects, set of used objects.
    '''
    from src.plugins.manager_instance import internal_manager as im 

    children = G.get_ordered_ast_child_nodes(ast_node)
    if len(children) == 0:
        return NodeHandleResult(ast_node=ast_node,
                                values=[""], value_sources=[ast_node])
    if len(children) == 1:
        return im.dispatch_node(children[0], extra)
    results = []
    all_used_objs = set()
    def dfs(i=0, buffer="", used_objs=[]):
        nonlocal G, children, results, ast_node, extra
        if i == len(children):
            result_obj = G.add_obj_node(ast_node, 'string', value=buffer)
            add_contributes_to(G, used_objs, result_obj,
                               operation='string_concat')
            results.append(result_obj)
            all_used_objs.update(used_objs)
            return
        handled_element = im.dispatch_node(children[i], extra)
        objs = to_obj_nodes(G, handled_element, ast_node=children[i])
        for obj in objs:
            typ = G.get_node_attr(obj).get('type')
            value = val_to_str(G.get_node_attr(obj).get('code'))
            if buffer == wildcard or value == wildcard:
                dfs(i + 1, wildcard, used_objs + [obj])
            elif typ == 'string':
                dfs(i + 1, buffer + value, used_objs + [obj])
            else: # including 'number'
                dfs(i + 1, buffer + val_to_str(value), used_objs + [obj])
    dfs()
    return NodeHandleResult(ast_node=ast_node, obj_nodes=results,
        used_objs=list(all_used_objs), callback=get_df_callback(G))

