from src.core.logger import *
from src.core.graph import Graph
from src.core.utils import BranchTagContainer 
from src.core.utils import NodeHandleResult, ExtraInfo
from src.core.esprima import esprima_search, esprima_parse
from src.core.checker import traceback, vul_checking
from src.core.garbage_collection import cleanup_scope
# function is higher than block
from .blocks import simurun_block
# a little bit risky to use handle prop
# should be fine
from . import vars
from . import property
from src.core.utils import get_random_hex, wildcard, undefined, BranchTag
from src.core.helpers import to_values
from src.plugins.handler import Handler
from itertools import chain
from . import modeled_builtin_modules
from . import file
from ..utils import get_df_callback, to_obj_nodes, add_contributes_to, merge
import sty
import traceback as tb
from collections import defaultdict
from src.core.options import options

class HandleClass(Handler):
    """
    the class handler
    """
    def __init__(self, G, node_id, extra=None):
        self.G = G
        self.node_id = node_id
        self.extra = extra

    def process(self):
        """
        the pre processing function
        """
        r = ast_call_function(self.G, self.node_id, self.extra)
        return NodeHandleResult(obj_nodes=r.obj_nodes, used_objs=r.used_objs,
            values=r.values, value_sources=r.value_sources,
            ast_node=self.node_id, callback=get_df_callback(self.G))

def ast_call_function(G, ast_node, extra):
    '''
    Call a function (AST_CALL/AST_METHOD_CALL/AST_NEW).
    
    Args:
        G (Graph): graph
        ast_node: the Call/New expression's AST node.
        extra (ExtraInfo): extra information.

    Returns:
        NodeHandleResult: Returned objects and used objects.
    '''
    from src.plugins.manager_instance import internal_manager
    if G.finished:
        return NodeHandleResult()

    # handle the callee and parent object (for method calls)
    handled_parent = None
    if G.get_node_attr(ast_node).get('type') == 'AST_METHOD_CALL':
        handled_callee, handled_parent = property.handle_prop(G, ast_node, extra)
    else:
        callee = G.get_ordered_ast_child_nodes(ast_node)[0]
        handled_callee = internal_manager.dispatch_node(callee, extra)

    # handle arguments
    handled_args = []
    arg_list_node = G.get_ordered_ast_child_nodes(ast_node)[-1]
    arg_list = G.get_ordered_ast_child_nodes(arg_list_node)
    for arg in arg_list:
        handled_arg = internal_manager.dispatch_node(arg, extra)
        handled_args.append(handled_arg)
