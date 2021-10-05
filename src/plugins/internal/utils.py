from src.core.graph import Graph
from src.core.utils import NodeHandleResult, ExtraInfo, BranchTag
from src.core.utils import wildcard, undefined
import math
from typing import Callable, List, Iterable
from collections import defaultdict
from src.core.logger import *
import secrets

def decl_function(G, node_id, func_name=None, obj_parent_scope=None,
    scope_parent_scope=None):
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

    if func_name is not None and func_name != '{closure}':
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

def register_func(G, node_id):
    """
    deprecated

    register the function to the nearest parent function like node
    we assume the 1-level parent node is the stmt of parent function

    Args:
        G (Graph): the graph object
        node_id (str): the node that needed to be registered
    """
    # we assume this node only have one parent node
    # sometimes this could be the root node and do not have any parent nodes
    if len(G.get_in_edges(node_id, edge_type="PARENT_OF")) == 0:
        return None
    parent_stmt_nodeid = G.get_in_edges(node_id, edge_type = "PARENT_OF")[0][0]
    parent_func_nodeid = G.get_in_edges(parent_stmt_nodeid, edge_type = "PARENT_OF")[0][0]
    G.set_node_attr(parent_func_nodeid, ("HAVE_FUNC", node_id))
    if parent_func_nodeid not in G.registered_funcs:
        G.registered_funcs[parent_func_nodeid] = set()
    G.registered_funcs[parent_func_nodeid].add(node_id)

    loggers.main_logger.info(sty.ef.b + sty.fg.green + "REGISTER {} to {}".format(node_id, parent_func_nodeid) + sty.rs.all)

def decl_vars_and_funcs(G, ast_node, var=True, func=True):
    # pre-declare variables and functions
    func_scope = G.find_ancestor_scope()
    children = G.get_ordered_ast_child_nodes(ast_node)
    for child in children:
        node_type = G.get_node_attr(child)['type']
        if var and node_type == 'AST_VAR' and \
            G.get_node_attr(child)['flags:string[]'] == 'JS_DECL_VAR':
            # var a;
            name = G.get_name_from_child(child)
            if G.get_name_node(name, scope=func_scope,
                               follow_scope_chain=False) is None:
                G.add_obj_to_scope(name=name, scope=func_scope,
                                   tobe_added_obj=G.undefined_obj)
        elif var and node_type == 'AST_ASSIGN':
            # var a = ...;
            children = G.get_ordered_ast_child_nodes(child)
            if G.get_node_attr(children[0])['type'] == 'AST_VAR' and \
                G.get_node_attr(children[0])['flags:string[]'] == 'JS_DECL_VAR':
                name = G.get_name_from_child(children[0])
                # if name node does not exist, add a name node in the scope
                # and assign it to the undefined object
                if G.get_name_node(name, scope=func_scope,
                                   follow_scope_chain=False) is None:
                    G.add_obj_to_scope(name=name, scope=func_scope,
                                       tobe_added_obj=G.undefined_obj)
                else:
                    pass
        elif func and node_type == 'AST_FUNC_DECL':
            func_name = G.get_name_from_child(child)
            func_obj = decl_function(G, child, obj_parent_scope=func_scope)

        elif node_type in ['AST_IF', 'AST_IF_ELEM', 'AST_FOR', 'AST_FOREACH',
            'AST_WHILE', 'AST_SWITCH', 'AST_SWITCH_CASE', 'AST_EXPR_LIST']:
            decl_vars_and_funcs(G, child, var=var, func=False)

def eval_value(G: Graph, s: str, return_obj_node=False, ast_node=None):
    '''
    Experimental. Extract Python values, JavaScript types from literal
    values (presented by JavaScript code) and create object nodes.
    
    Args:
        G (Graph): Graph.
        s (str): The literal value (as JavaScript code).
        return_obj_node (bool, optional): Create/return an object node
            for the value. Defaults to False.
        ast_node (optional): The value's AST node. Defaults to None.
    
    Returns:
        evaluated, js_type, result: the Python value, JavaScript type
            (in string), and object node (optional).
    '''
    js_type = None
    result = None
    if s == 'true':
        evaluated = True
        js_type = 'boolean'
        result = NodeHandleResult(name='true', obj_nodes=[G.true_obj])
    elif s == 'false':
        evaluated = False
        js_type = 'boolean'
        result = NodeHandleResult(name='false', obj_nodes=[G.false_obj])
    elif s == 'NaN':
        evaluated = math.nan
        js_type = 'number'
        result = NodeHandleResult(name='NaN', obj_nodes=[G.false_obj])
    elif s == 'Infinity':
        evaluated = math.inf
        js_type = 'number'
        result = NodeHandleResult(name='Infinity', obj_nodes=[G.infinity_obj])
    elif s == '-Infinity':
        evaluated = -math.inf
        js_type = 'number'
        result = NodeHandleResult(name='-Infinity', obj_nodes=[
            G.negative_infinity_obj])
    else:
        evaluated = eval(s)
        if type(evaluated) is float or type(evaluated) is int:
            js_type = 'number'
        elif type(evaluated) is str:
            js_type = 'string'
        if return_obj_node:
            added_obj = G.add_obj_node(ast_node, js_type, s)
            result = NodeHandleResult(obj_nodes=[added_obj])
    if return_obj_node:
        return evaluated, js_type, result
    else:
        return evaluated, js_type

def to_obj_nodes(G: Graph, handle_result: NodeHandleResult, ast_node=None,
    incl_existing_obj_nodes=True):
    '''
    Experimental. Converts 'values' field into object nodes.
    Returns converted object nodes as a list.
    '''
    returned_objs = []
    if handle_result.values:
        for i, value in enumerate(handle_result.values):
            if type(value) in [int, float]:
                added_obj = G.add_obj_node(ast_node, 'number', value)
            else:
                added_obj = G.add_obj_node(ast_node, 'string', value)
            if handle_result.value_tags:
                G.set_node_attr(added_obj, 
                    ('for_tags', handle_result.value_tags[i]))
            returned_objs.append(added_obj)
            # add CONTRIBUTES_TO edges from sources to the added object
            if i < len(handle_result.value_sources):
                for obj in handle_result.value_sources[i]:
                    if obj is not None:
                        add_contributes_to(G, [obj], added_obj)
    if incl_existing_obj_nodes:
        returned_objs.extend(handle_result.obj_nodes)
    return returned_objs

def to_values(G: Graph, handle_result: NodeHandleResult,
    incl_existing_values=True, for_prop=False):
    '''
    Experimental. Get values ('code' fields) in object nodes.
    Returns values, sources and tags in lists.
    '''
    values = []
    sources = []
    tags = []
    if incl_existing_values:
        values = list(handle_result.values)
        if for_prop:
            values = list(map(val_to_str, values))
        if handle_result.value_sources:
            sources = handle_result.value_sources
        else:
            sources = [[]] * len(handle_result.values)
        if handle_result.value_tags:
            tags = handle_result.value_tags
        else:
            tags = [[] for i in range(len(handle_result.values))]
    for obj in handle_result.obj_nodes:
        attrs = G.get_node_attr(obj)
        if for_prop:
            if attrs.get('code') == wildcard:
                value = wildcard
            elif obj == G.undefined_obj:
                value = undefined
            elif attrs.get('code') is not None:
                value = val_to_str(attrs.get('code'))
            else:
                value = 'Obj#' + obj
        else:
            if attrs.get('code') is not None:
                value = attrs.get('code')
            else:
                value = wildcard
        values.append(value)
        sources.append([obj])
        tags.append(G.get_node_attr(obj).get('for_tags', []))
    # print(values, sources)
    values, sources = combine_values(values, sources)
    return values, sources, tags

def combine_values(values, sources, *arg):
    d = defaultdict(lambda: [])
    for i, v in enumerate(values):
        d[v].extend(sources[i])
    return (list(d.keys()), list(d.values()), *arg)

def peek_variables(G: Graph, ast_node, extra: ExtraInfo):
    '''
    Experimental. Peek what variable is used in the statement and get
    their object nodes. Currently, you must ensure the statement you
    want tho peek is in the same scope as your current scope.
    
    Args:
        G (Graph): Graph.
        ast_node: AST node of the statement.
        handling_func (Callable): Function to handle the variable node.
            Normally you should use handle_var.
        extra (ExtraInfo): Extra info.
    '''
    returned_dict = {}
    from src.plugins.manager_instance import internal_manager
    if G.get_node_attr(ast_node).get('type') == 'AST_VAR' or \
        G.get_node_attr(ast_node).get('type') == 'AST_NAME':
        handle_result = internal_manager.dispatch_node(ast_node, extra=extra)
        if handle_result.name:
            returned_dict[handle_result.name] = handle_result.obj_nodes
    else:
        for child in G.get_ordered_ast_child_nodes(ast_node):
            d = peek_variables(G, child, extra)
            for name, nodes in d.items():
                if name in returned_dict:
                    returned_dict[name].extend(d[name])
                else:
                    returned_dict[name] = d[name]
        for name, nodes in returned_dict.items():
            returned_dict[name] = list(set(nodes))
    return returned_dict

def val_to_str(value, default=wildcard):
    if type(value) in [float, int]:
        return '%g' % value
    else:
        if value is None or value == wildcard:
            return default
        return str(value)

def val_to_float(value, default=wildcard):
    if value is None or value == wildcard or value == undefined:
        return default
    try:
        return float(value)
    except ValueError:
        return float('nan')

def cmp(a, b):
    return (a > b) - (a < b)

def js_cmp(v1, v2):
    if type(v1) == type(v2):
        if v1 == undefined and v2 == undefined:
            return 0
        else:
            return cmp(v1, v2)
    else:
        # s1 = val_to_str(v1)
        # s2 = val_to_str(v2)
        n1 = val_to_float(v1)
        n2 = val_to_float(v2)
        return cmp(n1, n2)

def is_int(x):
    try: # check if x is an integer
        _ = int(x)
    except (ValueError, TypeError):
        return False
    return True

def convert_prop_names_to_wildcard(G: Graph, obj, exclude_length=False,
    exclude_proto=True):
    wildcard_name_node = G.add_prop_name_node(wildcard, obj)
    for e1 in G.get_out_edges(obj, edge_type='OBJ_TO_PROP'):
        name_node = e1[1]
        if G.get_node_attr(name_node).get('name') == wildcard:
            continue
        if exclude_length and \
            G.get_node_attr(name_node).get('name') == 'length':
            continue
        if exclude_proto and \
            G.get_node_attr(name_node).get('name') == '__proto__':
            continue
        for e2 in G.get_out_edges(name_node, edge_type='NAME_TO_OBJ'):
            _, obj, _, data = e2
            G.add_edge(wildcard_name_node, obj, data)
        G.remove_all_edges_between(e1[0], e1[1])    

def copy_objs_for_branch(G: Graph, handle_result: NodeHandleResult, branch,
    ast_node=None, deep=True) -> NodeHandleResult:
    returned_objs = list()
    for obj in handle_result.obj_nodes:
        copied_obj = None
        for e in G.get_in_edges(obj, edge_type='NAME_TO_OBJ'):
            name_node, _, _, data = e
            eb = data.get('branch')
            if name_node in handle_result.name_nodes and (eb is None or
                (eb.point == branch.point and eb.branch != branch.branch)):
                if copied_obj is None: # the object should be copied only once
                    copied_obj = G.copy_obj(obj, ast_node, deep=deep)
                    returned_objs.append(copied_obj)
                # assign the name node to the copied object and mark the
                # previous edge as deleted (D)
                edge_attr_a = dict(data)
                edge_attr_a['branch'] = BranchTag(branch, mark='A')
                edge_attr_d = dict(data)
                edge_attr_d['branch'] = BranchTag(branch, mark='D')
                G.add_edge(name_node, copied_obj, edge_attr_a)
                G.add_edge(name_node, obj, edge_attr_d)
        if copied_obj is None: # if the object is not copied, return it
            returned_objs.append(obj)

    return NodeHandleResult(obj_nodes=returned_objs, name=handle_result.name,
        name_node=handle_result.name_nodes)

def copy_objs_for_parameters(G: Graph, handle_result: NodeHandleResult,
    ast_node=None, number_of_copies=1, delete_original=True) -> List[List]:
    # deprecated
    returned_objs = list()
    for obj in handle_result.obj_nodes:
        copied_objs = []
        for i in range(number_of_copies):
            copied_objs.append(G.copy_obj(obj, ast_node))
        for e in G.get_in_edges(obj, edge_type='NAME_TO_OBJ'):
            name_node, obj_node, k, data = e
            if name_node in handle_result.name_nodes:
                if delete_original:
                    G.graph.remove_edge(name_node, obj_node, k)
                for copied_obj in copied_objs:
                    G.add_edge(name_node, copied_obj, data)
        returned_objs.append(copied_objs)

    return returned_objs

def to_python_array(G: Graph, array_obj, value=False):
    elements = [[]]
    data = [[]]
    for name_node in G.get_prop_name_nodes(array_obj):
        name = G.get_node_attr(name_node).get('name')
        if name == 'length' or name == '__proto__':
            continue
        try:
            i = int(name)
            while i >= len(elements):
                elements.append([])
                data.append([])
        except (ValueError, TypeError):
            continue
        for e in G.get_out_edges(name_node, edge_type='NAME_TO_OBJ'):
            if value:
                elements[i].append(val_to_str(G.get_node_attr(e[1])
                    .get('code')))
            else:
                elements[i].append(e[1])
            data[i].append(e[3])
    return elements, data

def to_og_array(G: Graph, array, data, ast_node=None):
    added_array = G.add_obj_node(ast_node=ast_node, js_type='array')
    for i, elem in enumerate(array):
        name_node = G.add_prop_name_node(name=str(i), parent_obj=added_array)
        for j, obj in enumerate(elem):
            G.add_edge(name_node, obj,
                {'type:TYPE': 'NAME_TO_OBJ', **data[i][j]})
    G.add_obj_as_prop(prop_name='length', ast_node=ast_node, js_type='number',
        value=len(array), parent_obj=added_array)
    return added_array

def add_contributes_to(G: Graph, sources: Iterable, target,
    chain_tainted=True):
    assert not isinstance(sources, (str, bytes))
    tainted = False
    for s in sources:
        # source_id = str(s)
        # if G.get_node_attr(s).get('tainted'):
        #     source_id += ' tainted'
        # print(f'{source_id} CONTRIBUTES TO {target}')
        G.add_edge(s, target, {'type:TYPE': 'CONTRIBUTES_TO'})
        tainted = tainted or G.get_node_attr(s).get('tainted', False)
    if chain_tainted and tainted:
        G.set_node_attr(target, ('tainted', True))

def get_df_callback(G, ast_node=None):
    if ast_node is None:
        cpg_node = G.cur_stmt
    else:
        cpg_node = G.find_nearest_upper_CPG_node(ast_node)
    return lambda result: build_df_by_def_use(G, cpg_node, result.used_objs)

def build_df_by_def_use(G, cur_stmt, used_objs):
    """
    Build data flows for objects used in current statement.
    The flow will be from the object's definition to current statement (current node).
    """
    if not used_objs or cur_stmt is None:
        return
    cur_lineno = G.get_node_attr(cur_stmt).get('lineno:int')
    # If an used object is a wildcard object, add its parent object as
    # used object too, until it is not a wildcard object.
    used_objs = list(used_objs)
    used_obj_set = set(used_objs)
    for obj in used_objs:
        node_attrs = G.get_node_attr(obj)
        if node_attrs.get('type') == 'object' and node_attrs.get('code') == wildcard:
            for e1 in G.get_in_edges(obj, edge_type='NAME_TO_OBJ'):
                for e2 in G.get_in_edges(e1[0], edge_type='OBJ_TO_PROP'):
                    if e2[0] not in used_obj_set:
                        used_objs.append(e2[0])
                        used_obj_set.add(e2[0])
                        # logger.debug("{}-----{}-----{}".format(obj, e1[0], e2[0]))
    for obj in used_obj_set:
        def_ast_node = G.get_obj_def_ast_node(obj)
        # print("?", cur_stmt, used_objs, def_ast_node)
        if def_ast_node is None: continue
        def_cpg_node = G.find_nearest_upper_CPG_node(def_ast_node)
        if def_cpg_node is None: continue
        if def_cpg_node == cur_stmt: continue
        def_lineno = G.get_node_attr(def_cpg_node).get('lineno:int')
        loggers.main_logger.info(sty.fg.li_magenta + sty.ef.inverse + "OBJ REACHES" + sty.rs.all +
        " {} -> {} (Line {} -> Line {}), by OBJ {}".format(def_cpg_node,
        cur_stmt, def_lineno, cur_lineno, obj))
        G.add_edge(def_cpg_node, cur_stmt, {'type:TYPE': 'OBJ_REACHES', 'obj': obj})

def check_condition(G: Graph, ast_node, extra: ExtraInfo):
    '''
    Check if a condition is true or false.
    
    Args:
        G (Graph): Graph.
        ast_node: AST node of the condition expression.
        extra (ExtraInfo): Extra info.

    Returns:
        float, bool: A number (range [0, 1]) indicates how possible the
            condition is true. If both left side and right side are
            single possibility, it returns 0 for false, and 1 for true.
            A boolean value if all results are not deterministic.
    '''
    node_type = G.get_node_attr(ast_node).get('type')
    op_type = G.get_node_attr(ast_node).get('flags:string[]')
    flag = True
    deter_flag = True
    if node_type == 'AST_EXPR_LIST':
        child = G.get_ordered_ast_child_nodes(ast_node)[0]
        return check_condition(G, child, extra)
    elif node_type == 'AST_UNARY_OP' and op_type == 'UNARY_BOOL_NOT':
        child = G.get_ordered_ast_child_nodes(ast_node)[0]
        p, d = check_condition(G, child, extra)
        if p is not None:
            return 1 - p, d
        else:
            return None, d
    if node_type == 'AST_BINARY_OP':
        left, right = G.get_ordered_ast_child_nodes(ast_node)[:2]
        if op_type == 'BINARY_BOOL_OR':
            lp, ld = check_condition(G, left, extra)
            # print('binary bool or', lp, ld)
            rp, rd = check_condition(G, right, extra)
            # print('binary bool or', lp, ld, rp, rd)
            if lp is not None and rp is not None:
                return lp + rp - lp * rp, ld and rd
            else:
                return None, False
        elif op_type == 'BINARY_BOOL_AND':
            lp, ld = check_condition(G, left, extra)
            # print('binary bool and', lp, ld)
            rp, rd = check_condition(G, right, extra)
            # print('binary bool and', lp, ld, rp, rd)
            if lp is not None and rp is not None:
                return lp * rp, ld and rd
            else:
                return None, False
        else:
            from src.plugins.manager_instance import internal_manager
            handled_left = internal_manager.dispatch_node(left, extra)
            handled_right = internal_manager.dispatch_node(right, extra)
            build_df_by_def_use(G, ast_node, handled_left.obj_nodes)
            build_df_by_def_use(G, ast_node, handled_right.obj_nodes)
            left_values = to_values(G, handled_left, ast_node, for_prop=True)[0]
            right_values = to_values(G, handled_right, ast_node, for_prop=True)[0]
            # print(f'Comparing {handled_left.name}: {left_values} and '
            #     f'{handled_right.name}: {right_values}')

            true_num = 0
            total_num = len(left_values) * len(right_values)
            if total_num == 0:
                return None, False # Value is unknown, cannot check
            if op_type == 'BINARY_IS_EQUAL':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) != (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if js_cmp(v1, v2) == 0:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_IDENTICAL':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) != (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if v1 == v2:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_NOT_EQUAL':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) != (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if js_cmp(v1, v2) != 0:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_NOT_IDENTICAL':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) != (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if v1 != v2:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_SMALLER':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) or (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if js_cmp(v1, v2) < 0:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_GREATER':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) or (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if js_cmp(v1, v2) > 0:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_SMALLER_OR_EQUAL':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) or (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if js_cmp(v1, v2) <= 0:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            elif op_type == 'BINARY_IS_GREATER_OR_EQUAL':
                for v1 in left_values:
                    for v2 in right_values:
                        if (v1 != undefined) or (v2 != undefined):
                            true_num += 0.5
                            deter_flag = False
                        elif v1 != wildcard and v2 != wildcard:
                            if js_cmp(v1, v2) >= 0:
                                true_num += 1
                        else:
                            true_num += 0.5
                            deter_flag = False
            else:
                flag = False
    else:
        flag = False
    if not flag:
        from ..manager_instance import internal_manager
        handled = internal_manager.dispatch_node(ast_node, extra)
        build_df_by_def_use(G, ast_node, handled.obj_nodes)
        true_num = 0
        total_num = len(list(filter(lambda x: x != G.undefined_obj, handled.obj_nodes))) + len(handled.values)
        if total_num == 0:
            return None, False # Value is unknown, cannot check
        for value in handled.values:
            if value == wildcard:
                true_num += 0.5
                deter_flag = False
            elif value == 0:
                pass
            else:
                true_num += 1
        for obj in handled.obj_nodes:
            if obj in [G.undefined_obj, G.null_obj, G.false_obj]:
                true_num += 0.1
                pass
            elif obj in [G.infinity_obj, G.negative_infinity_obj, G.nan_obj,
                G.true_obj]:
                true_num += 1
            else:
                value = G.get_node_attr(obj).get('code')
                typ = G.get_node_attr(obj).get('type')
                if typ == 'number':
                    if value == wildcard:
                        true_num += 0.5
                        deter_flag = False
                    elif val_to_float(value) != 0:
                        true_num += 1
                elif typ == 'string':
                    if value == wildcard:
                        true_num += 0.5
                        deter_flag = False
                    elif value:
                        true_num += 1
                elif typ == 'function':
                    # how should we determine when it's a function?
                    true_num += 0.5
                    deter_flag = False
                else:
                    if value == wildcard:
                        true_num += 0.5
                        deter_flag = False
                    else:
                        true_num += 1
        for value in handled.values:
            if value:
                true_num += 1
    if 0 == total_num:
        return None, False
    return true_num / total_num, deter_flag

def is_wildcard_obj(G, obj):
    attrs = G.get_node_attr(obj)
    return (attrs.get('type') in ['object', 'array'] and
            attrs.get('code') == wildcard) \
        or (attrs.get('type') in ['number', 'string'] and
            attrs.get('code')== wildcard)

def get_random_hex(length=6):
    return secrets.token_hex(length // 2)

def has_else(G, if_ast_node):
    '''
    Check if an if statement has 'else'.
    '''
    # Check by finding if the last if element's condition is NULL
    elems = G.get_ordered_ast_child_nodes(if_ast_node)
    if elems:
        last_elem = elems[-1]
        cond = G.get_ordered_ast_child_nodes(last_elem)[0]
        if G.get_node_attr(cond).get('type') == 'NULL':
            return True
    return False

def merge(G, stmt, num_of_branches, parent_branch):
    '''
    Merge two or more branches.
    
    Args:
        G: graph
        stmt: AST node ID of the if/switch statement.
        num_of_branches (int): number of branches.
        parent_branch (BranchTag): parent branch tag (if this branch is
            inside another branch statement).
     '''
    loggers.main_logger.debug(f'Merging branches in {stmt}')
    name_nodes = G.get_node_by_attr('labels:label', 'Name')
    for u in name_nodes:
        for v in G.get_child_nodes(u, 'NAME_TO_OBJ'):
            created = [False] * num_of_branches
            deleted = [False] * num_of_branches
            for key, edge_attr in G.graph[u][v].items():
                branch_tag = edge_attr.get('branch')
                if branch_tag and branch_tag.point == stmt:
                    if branch_tag.mark == 'A':
                        created[int(branch_tag.branch)] = True
                    if branch_tag.mark == 'D':
                        deleted[int(branch_tag.branch)] = True

            # We flatten Addition edges if they exist in any branch, because
            # the possibilities will continue to exist in parent branches.
            # We ignore those edges without tags related to current
            # statement.
            flag_created = any(created)
            # We always delete Deletion edges because they are useless in
            # parent branches.
            # If they exist in all current branches, the Addition edge in the
            # parent branch will be deleted (or maked by a Deletion edge).
            flag_deleted = deleted and all(deleted)

            # we'll delete edges, so we save them in a list
            # otherwise the graph is changed and Python will raise an error
            edges = list(G.graph[u][v].items())

            # deleted all branch edges (both Addition and Deletion)
            for key, edge_attr in edges:
                branch_tag = edge_attr.get('branch', BranchTag())
                if branch_tag.point == stmt:
                    G.graph.remove_edge(u, v, key)

            # flatten Addition edges
            if flag_created:
                # logger.debug(f'add edge {u}->{v}, branch={stmt}')
                if parent_branch:
                    # add one addition edge with parent if/switch's (upper level's) tags
                    # logger.debug(f"create edge {u}->{v}, branch={BranchTag(parent_branch, mark='A')}")
                    G.add_edge(u, v, {'type:TYPE': 'NAME_TO_OBJ', 'branch': BranchTag(parent_branch, mark='A')})
                else:
                    # logger.debug(f'create edge {u}->{v}')
                    G.add_edge(u, v, {'type:TYPE': 'NAME_TO_OBJ'})

            # cancel out Deletion edges
            if flag_deleted:
                if parent_branch:
                    # find if there is any addition in parent if/switch (upper level)
                    flag = False
                    for key, edge_attr in list(G.graph[u][v].items()):
                        branch_tag = edge_attr.get('branch', BranchTag())
                        if branch_tag == BranchTag(parent_branch, mark='A'):
                            # logger.debug(f'delete edge {u}->{v}')
                            G.graph.remove_edge(u, v, key)
                            flag = True
                    # if there is not
                    if not flag:
                        # add one deletion edge with parent if/switch's (upper level's) tags
                        # logger.debug(f"create edge {u}->{v}, branch={BranchTag(parent_branch, mark='D')}")
                        G.add_edge(u, v, {'type:TYPE': 'NAME_TO_OBJ', 'branch': BranchTag(parent_branch, mark='D')})
                else:
                    # find if there is an addition in upper level
                    for key, edge_attr in list(G.graph[u][v].items()):
                        if 'branch' not in edge_attr:
                            # logger.debug(f'delete edge {u}->{v}')
                            G.graph.remove_edge(u, v, key)
