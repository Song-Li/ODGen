# This module is used to handle all the block level nodes
from src.core.graph import Graph
from src.core.logger import *
from src.core.utils import ExtraInfo, BranchTagContainer
from src.core.garbage_collection import cleanup_scope
from ..utils import decl_vars_and_funcs, to_obj_nodes

def simurun_block(G, ast_node, parent_scope=None, branches=None,
    block_scope=True, decl_var=False):
    """
    Simurun a block by running its statements one by one.
    A block is a BlockStatement in JavaScript,
    or an AST_STMT_LIST in PHP.
    """
    from src.plugins.manager_instance import internal_manager
    if branches is None:
        branches = BranchTagContainer()
    returned_objs = set()
    used_objs = set()
    if parent_scope == None:
        parent_scope = G.cur_scope
    if block_scope:
        G.cur_scope = \
            G.add_scope('BLOCK_SCOPE', decl_ast=ast_node,
                        scope_name=G.scope_counter.gets(f'Block{ast_node}'))
    loggers.main_logger.log(ATTENTION, 'BLOCK {} STARTS, SCOPE {}'.format(ast_node, G.cur_scope))
    decl_vars_and_funcs(G, ast_node, var=decl_var)
    stmts = G.get_ordered_ast_child_nodes(ast_node)
    # simulate statements
    for stmt in stmts:
        if G.cfg_stmt is not None:
            G.add_edge_if_not_exist(G.cfg_stmt, stmt, {"type:TYPE": "FLOWS_TO"})

        G.cur_stmt = stmt
        G.cfg_stmt = stmt
        # add control flow edges here
        handled_res = internal_manager.dispatch_node(stmt, ExtraInfo(branches=branches))

    returned_objs = G.function_returns[G.find_ancestor_scope()][1]
    
    if block_scope:

        G.cur_scope = parent_scope

    
    return list(returned_objs), list(used_objs)
