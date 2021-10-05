from src.plugins.handler import Handler
from src.core.utils import ExtraInfo
from src.core.graph import Graph
from src.core.logger import loggers
from . import func_decl 

class HandleClass(Handler):
    """
    hander for class
    """
    def process(self):
        handle_class(self.G, self.node_id, self.extra)

class HandleMethod(Handler):
    """
    hander for class method
    """
    def process(self):
        handle_method(self.G, self.node_id, self.extra)


def handle_class(G: Graph, ast_node, extra):
    children = G.get_ordered_ast_child_nodes(ast_node)
    name = G.get_node_attr(children[0]).get('code')
    class_obj = G.add_obj_node(ast_node=None, js_type='function')
    G.set_node_attr(class_obj, ('name', name))
    G.set_node_attr(class_obj, ('value', f'[class {name}]'))
    toplevel = children[4]
    body = G.get_child_nodes(toplevel, edge_type='PARENT_OF',
                             child_type='AST_STMT_LIST')[0]
    prev_dont_quit = G.dont_quit
    G.dont_quit = True
    simurun_class_body(G, body, ExtraInfo(extra, class_obj=class_obj))
    G.dont_quit = prev_dont_quit
    if G.get_obj_def_ast_node(class_obj) is None:
        ast = G.add_blank_func(name)
        G.add_edge(class_obj, ast, {'type:TYPE': 'OBJ_TO_AST'})
    if G.find_nearest_upper_CPG_node(ast_node) == ast_node:
        G.add_obj_to_scope(name, tobe_added_obj=class_obj)
    
def handle_method(G: Graph, ast_node, extra):
    assert extra.class_obj is not None
    name = G.get_name_from_child(ast_node)
    if name == 'constructor':
        G.add_edge(extra.class_obj, ast_node, {'type:TYPE': 'OBJ_TO_AST'})
    else:
        method_obj = func_decl.decl_function(G, ast_node, add_to_scope=False)
        prototypes = G.get_prop_obj_nodes(extra.class_obj, 'prototype', 
                                          branches=extra.branches)
        for p in prototypes:
            G.add_obj_as_prop(name, parent_obj=p, tobe_added_obj=method_obj)

def simurun_class_body(G, ast_node, extra):
    """
    Simurun the body of a class
    """
    from src.plugins.manager_instance import internal_manager
    if extra is None or extra.branches is None:
        branches = BranchTagContainer()
    else:
        branches = extra.branches

    loggers.main_logger.info('BLOCK {} STARTS, SCOPE {}'.format(ast_node, G.cur_scope))
    stmts = G.get_ordered_ast_child_nodes(ast_node)
    # control flows
    for last_stmt in G.last_stmts:
        G.add_edge(last_stmt, ast_node, {'type:TYPE': 'FLOWS_TO'})
    G.last_stmts = [ast_node]
    # simulate statements
    for stmt in stmts:
        # build control flows from the previous statement to the current one
        for last_stmt in G.last_stmts:
            G.add_edge(last_stmt, stmt, {'type:TYPE': 'FLOWS_TO'})
        G.last_stmts = [stmt]
        G.cur_stmt = stmt
        internal_manager.dispatch_node(stmt,
            ExtraInfo(extra, branches=branches))

        if G.finished:
            break

        if G.get_node_attr(stmt).get('type') == 'AST_RETURN':
            G.last_stmts = []

