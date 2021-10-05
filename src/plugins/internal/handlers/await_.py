from src.plugins.handler import Handler
from .functions import call_function
from src.core.utils import NodeHandleResult, ExtraInfo
from src.plugins.internal.utils import get_df_callback, to_obj_nodes

class HandleAwait(Handler):
    """
    the handler to handle await(AST_YIELD)
    """
    def __init__(self, G, node_id, extra=None):
        self.G = G
        self.node_id = node_id
        self.extra = extra

    def process(self):
        from src.plugins.manager_instance import internal_manager
        promises = internal_manager.dispatch_node(self.G.get_ordered_ast_child_nodes(self.node_id)[0])
        returned_objs = set()
        # prepare a callback (onFulfilled) function
        def python_callback(
                G, caller_ast, extra, _, value=NodeHandleResult(), *args):
            nonlocal returned_objs
            returned_objs.update(to_obj_nodes(G, value, self.node_id))
            return NodeHandleResult()
        cb = self.G.add_blank_func_with_og_nodes(
            'pythonCallback', python_func=python_callback)
        # call promise.then
        for promise in promises.obj_nodes:
            then = self.G.get_prop_obj_nodes(
                        self.G.promise_prototype, 'then', self.extra.branches)
            result, _ = call_function(self.G, then,
                    args=[NodeHandleResult(obj_nodes=[cb])],
                    this=NodeHandleResult(obj_nodes=[promise]),
                    extra=self.extra, caller_ast=self.node_id)
        # add control flows from the callback function's EXIT node to
        # the current statement
        cb_ast = self.G.get_obj_def_ast_node(cb)
        exit_node = self.G.get_successors(cb_ast, edge_type='EXIT')[0]
        self.G.add_edge_if_not_exist(exit_node,
            self.G.find_nearest_upper_CPG_node(self.node_id), {"type:TYPE": "FLOWS_TO"})
        return NodeHandleResult(ast_node=self.node_id,
                                obj_nodes=list(returned_objs),
                                used_objs=promises.obj_nodes,
                                callback=get_df_callback(self.G))
