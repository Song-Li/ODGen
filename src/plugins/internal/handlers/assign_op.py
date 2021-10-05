from src.plugins.handler import Handler
from src.core.utils import ExtraInfo, NodeHandleResult
from src.plugins.internal.utils import to_obj_nodes, wildcard, add_contributes_to, get_df_callback
from . import operators

class HandleAssignOP(Handler):
    def process(self):
        return handle_op_by_objs(self.G, self.node_id, self.extra, manager=self.internal_manager)

def handle_op_by_objs(G, ast_node, extra=ExtraInfo(), saved={}, manager=None):
    left_child, right_child = G.get_ordered_ast_child_nodes(ast_node)
    flag = G.get_node_attr(ast_node).get('flags:string[]')
    handled_left = manager.dispatch_node(left_child, extra)
    handled_right = manager.dispatch_node(right_child, extra)
    left_objs = to_obj_nodes(G, handled_left, ast_node)
    right_objs = to_obj_nodes(G, handled_right, ast_node)
    func_scope = G.find_ancestor_scope()
    used_objs = set()
    if len(left_objs) * len(right_objs) > 200:
        if (func_scope, ast_node) in saved:
            return saved[(func_scope, ast_node)]
    def get_value_and_type(node):
        nonlocal G
        attrs = G.get_node_attr(node)
        value = attrs.get('code')
        if value is None:
            value = wildcard
        return value, attrs.get('type')
    results = []
    if flag == 'BINARY_ADD':
        for i, o1 in enumerate(left_objs):
            for j, o2 in enumerate(right_objs):
                v1, t1 = get_value_and_type(o1)
                v2, t2 = get_value_and_type(o2)
                if v1 != wildcard and v2 != wildcard:
                    if t1 == 'number' and t2 == 'number':
                        result = float(v1 + v2)
                        t = 'number'
                        op = 'numeric_add'
                    else:
                        result = str(v1) + str(v2)
                        t = 'string'
                        op = 'string_concat'
                else:
                    result = wildcard
                    t = None # implies 'object'
                    op = 'unknown_add'
                result_obj = G.add_obj_node(ast_node, t, result)
                # logger.log(ATTENTION, f'{v1} + {v2}: {o1} {o2} -> {result_obj}')
                add_contributes_to(G, [o1, o2], result_obj, op)
                results.append(result_obj)
                used_objs.add(o1)
                used_objs.add(o2)
        if len(left_objs) * len(right_objs) == 0:
            # always returns at least one value
            results.append(G.add_obj_node(ast_node, None, wildcard))
    elif flag == 'BINARY_SUB':
        for i, o1 in enumerate(left_objs):
            for j, o2 in enumerate(right_objs):
                v1, _ = get_value_and_type(o1)
                v2, _ = get_value_and_type(o2)
                if v1 != wildcard and v2 != wildcard:
                    try:
                        result = float(v1) - float(v2)
                        t = 'number'
                    except ValueError:
                        result = float('nan')
                        t = 'number'
                else:
                    result = wildcard
                    t = None # implies 'object'
                result_obj = G.add_obj_node(ast_node, t, result)
                add_contributes_to(G, [o1, o2], result_obj, 'sub')
                results.append(result_obj)
                used_objs.add(o1)
                used_objs.add(o2)
        if len(left_objs) * len(right_objs) == 0:
            # always returns at least one value
            results.append(G.add_obj_node(ast_node, None, wildcard))
    if G.get_node_attr(ast_node).get('type') == 'AST_ASSIGN_OP':
        operators.do_assign(G, handled_left, NodeHandleResult(obj_nodes=results),
            branches=extra.branches, ast_node=ast_node)
    res = NodeHandleResult(ast_node=ast_node, obj_nodes=results,
        used_objs=list(used_objs), callback=get_df_callback(G))
    if len(results) > 200:
        saved[(func_scope, ast_node)] = res
    return res