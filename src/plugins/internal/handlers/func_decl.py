from src.plugins.handler import Handler
from src.core.utils import NodeHandleResult
from src.core.logger import *

class HandleFuncDecl(Handler):
    """
    handle the func decl and ast closure
    """
    def process(self):
        obj_nodes = self.G.get_func_decl_objs_by_ast_node(self.node_id,
                    scope=self.G.find_ancestor_scope())
        if not obj_nodes:
            obj_nodes = [decl_function(self.G, self.node_id)]
        return NodeHandleResult(obj_nodes=obj_nodes)

def decl_function(G, node_id, func_name=None, obj_parent_scope=None,
    scope_parent_scope=None, add_to_scope=True):
    '''
    Declare a function as an object node.
    
    Args:
        G (Graph): Graph.
        node_id: The function's AST node (AST_FUNC_DECL).
        func_name (str, optional): The function's name. Defaults to
            None, which means getting name from its AST children.
        obj_parent_scope (optional): Which scope the function object
            should be placed to. Defaults to current scope.
        scope_parent_scope (optional): Where the function's scopes
            should be put. See comments below. Defaults to current
            scope.
    
    Returns:
        added_obj: The function's object node.
    '''
    # for a function decl, if already visited, return
    # if "VISITED" in G.get_node_attr(node_id):
    #     return None

    if obj_parent_scope is None:
        obj_parent_scope = G.cur_scope
    if scope_parent_scope is None:
        scope_parent_scope = G.cur_scope
    if func_name is None:
        func_name = G.get_name_from_child(node_id)
    # add function declaration object
    added_obj = G.add_obj_node(node_id, "function")
    G.set_node_attr(added_obj, ('name', func_name))
    # memorize its parent scope
    # Function scopes are not created when the function is declared.
    # Instead, they are created before each time the function is
    # executed. Because the function can be called in any scope but its
    # scope should be put under where it is defined, we need to memorize
    # its original parent scope.
    G.set_node_attr(added_obj, ('parent_scope', scope_parent_scope))
    G.set_node_attr(added_obj, ('parent_scope_this', G.cur_objs))

    if func_name is not None and func_name != '{anon}' and add_to_scope:
        G.add_obj_to_scope(name=func_name, scope=obj_parent_scope,
            tobe_added_obj=added_obj)
        G.add_obj_as_prop('name', node_id, 'string', func_name, added_obj)
    param_list = G.get_child_nodes(node_id, edge_type='PARENT_OF',
        child_type='AST_PARAM_LIST')
    params = G.get_ordered_ast_child_nodes(param_list)
    length = len(params)
    if length > 0:
        if G.get_node_attr(params[-1]).get('flags:string[]') \
            == 'PARAM_VARIADIC':
            length -= 1
    G.add_obj_as_prop('length', node_id, 'number', length, added_obj)
    # G.set_node_attr(node_id, ("VISITED", "1"))
    loggers.main_logger.debug(f'{sty.ef.b}Declare function{sty.rs.all} {func_name} as {added_obj}')
    return added_obj
