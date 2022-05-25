from src.core.graph import Graph
from src.core.utils import NodeHandleResult, BranchTag, BranchTagContainer, ExtraInfo, get_random_hex
from src.core.utils import wildcard
from .handlers.functions import handle_require, call_function
from src.core.helpers import val_to_str, is_int
from src.core.helpers import convert_prop_names_to_wildcard
from src.core.helpers import copy_objs_for_branch, copy_objs_for_parameters
from src.core.helpers import to_python_array, to_og_array
from src.core.helpers import to_values, to_obj_nodes, add_contributes_to, val_to_float
from src.core.options import options
import sty
import re, json
from src.core.logger import loggers
from itertools import chain, product
from math import isnan
import math
from typing import Tuple


logger = loggers.main_logger


def setup_js_builtins(G: Graph):
    setup_object_and_function(G)
    setup_string(G)
    setup_number(G)
    setup_array(G)
    setup_boolean(G)
    setup_symbol(G)
    setup_errors(G)
    setup_global_functions(G)
    setup_global_objs(G)
    setup_json(G)
    setup_regexp(G)
    setup_math(G)
    setup_promise(G)
    G.add_blank_func_to_scope('Date', scope=G.BASE_SCOPE, python_func=blank_func)
    G.add_obj_to_name('__opgWildcard', value=wildcard, scope=G.BASE_SCOPE)


def setup_string(G: Graph):
    string_cons = G.add_blank_func_to_scope('String', scope=G.BASE_SCOPE, python_func=this_returning_func)
    G.builtin_constructors.append(string_cons)
    G.string_cons = string_cons
    string_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=string_cons)[0]
    G.set_node_attr(string_prototype, ('code', 'String.prototype'))
    G.string_prototype = string_prototype
    # built-in functions for regexp
    G.add_blank_func_as_prop('match', string_prototype, None)
    G.add_blank_func_as_prop('matchAll', string_prototype, None)
    G.add_blank_func_as_prop('replace', string_prototype, string_p_replace)
    G.add_blank_func_as_prop('search', string_prototype, string_p_match)
    G.add_blank_func_as_prop('split', string_prototype, string_p_split)
    G.add_blank_func_as_prop('substr', string_prototype, string_p_substr)
    G.add_blank_func_as_prop('substring', string_prototype, string_p_substring)
    G.add_blank_func_as_prop('reverse', string_prototype, string_p_reverse)
    G.add_blank_func_as_prop('toLowerCase', string_prototype, string_p_to_lower_case)
    G.add_blank_func_as_prop('toUpperCase', string_prototype, string_p_to_upper_case)
    G.add_blank_func_as_prop('trim', string_prototype, string_p_trim)
    G.add_blank_func_as_prop('trimEnd', string_prototype, string_p_trim_end)
    G.add_blank_func_as_prop('trimStart', string_prototype, string_p_trim_start)
    G.add_blank_func_as_prop('charAt', string_prototype, string_p_char_at)
    G.add_blank_func_as_prop('slice', string_prototype, string_returning_func)


def setup_number(G: Graph):
    number_cons = G.add_blank_func_to_scope('Number', scope=G.BASE_SCOPE, python_func=number_constructor)
    G.builtin_constructors.append(number_cons)
    G.number_cons = number_cons
    number_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=number_cons)[0]
    G.set_node_attr(number_prototype, ('code', 'Number.prototype'))
    G.number_prototype = number_prototype
    # Number.prototype.__proto__ = Object.prototype
    G.add_obj_as_prop(prop_name='__proto__', parent_obj=number_prototype, tobe_added_obj=G.object_prototype)


def setup_array(G: Graph):
    array_cons = G.add_blank_func_to_scope('Array', G.BASE_SCOPE, array_constructor)
    G.builtin_constructors.append(array_cons)
    G.array_cons = array_cons
    array_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=array_cons)[0]
    G.set_node_attr(array_prototype, ('code', 'Array.prototype'))
    G.array_prototype = array_prototype
    # Array.prototype.__proto__ = Object.prototype
    G.add_obj_as_prop(prop_name='__proto__', parent_obj=array_prototype, tobe_added_obj=G.object_prototype)

    G.add_blank_func_as_prop('isArray', array_cons, array_is_array)

    # built-in functions
    G.add_blank_func_as_prop('push', array_prototype, array_p_push)
    G.add_blank_func_as_prop('pop', array_prototype, array_p_pop)
    G.add_blank_func_as_prop('unshift', array_prototype, array_p_push)
    G.add_blank_func_as_prop('shift', array_prototype, array_p_shift) # broken
    G.add_blank_func_as_prop('join', array_prototype, array_p_join_3)
    G.add_blank_func_as_prop('forEach', array_prototype, array_p_for_each_value)
    G.add_blank_func_as_prop('keys', array_prototype, array_p_keys)
    G.add_blank_func_as_prop('values', array_prototype, array_p_values)
    G.add_blank_func_as_prop('entries', array_prototype, array_p_entries)
    G.add_blank_func_as_prop('splice', array_prototype, array_p_splice)
    G.add_blank_func_as_prop('slice', array_prototype, array_p_slice)
    G.add_blank_func_as_prop('filter', array_prototype, this_returning_func)
    G.add_blank_func_as_prop('map', array_prototype, array_p_map)
    G.add_blank_func_as_prop('reduce', array_prototype, array_p_reduce)
    G.add_blank_func_as_prop('concat', array_prototype, array_p_concat)


def setup_boolean(G: Graph):
    boolean_cons = G.add_blank_func_to_scope('Boolean', scope=G.BASE_SCOPE, python_func=this_returning_func)
    G.builtin_constructors.append(boolean_cons)
    G.boolean_cons = boolean_cons
    boolean_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=boolean_cons)[0]
    G.set_node_attr(boolean_prototype, ('code', 'Boolean.prototype'))
    G.boolean_prototype = boolean_prototype
    # Boolean.prototype.__proto__ = Object.prototype
    G.add_obj_as_prop(prop_name='__proto__', parent_obj=boolean_prototype, tobe_added_obj=G.object_prototype)


def setup_symbol(G: Graph):
    symbol_cons = G.add_blank_func_to_scope('Symbol', scope=G.BASE_SCOPE, python_func=this_returning_func)
    G.builtin_constructors.append(symbol_cons)
    symbol_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=symbol_cons)[0]
    G.set_node_attr(symbol_prototype, ('code', 'Symbol.prototype'))
    # Symbol.prototype.__proto__ = Object.prototype
    G.add_obj_as_prop(prop_name='__proto__', parent_obj=symbol_prototype, tobe_added_obj=G.object_prototype)


def setup_errors(G: Graph):
    error_cons = G.add_blank_func_to_scope('Error', scope=G.BASE_SCOPE, python_func=this_returning_func)
    G.builtin_constructors.append(error_cons)
    # # Error.prototype.__proto__ = Object.prototype
    # error_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=error_cons)[0]
    # G.add_obj_as_prop(prop_name='__proto__', parent_obj=error_prototype, tobe_added_obj=G.object_prototype)
    # for i in ['EvalError', 'InternalError', 'RangeError', 'ReferenceError', 'SyntaxError', 'TypeError', 'URIError']:
    #     # EvalError.prototype.__proto__ = Error
    #     cons = G.add_blank_func_to_scope(i, scope=G.BASE_SCOPE)
    #     prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=cons)[0]
    #     G.add_obj_as_prop(prop_name='__proto__', parent_obj=prototype, tobe_added_obj=error_prototype)


def setup_object_and_function(G: Graph):
    # add Object (function)
    object_cons = G.add_blank_func_to_scope('Object', scope=G.BASE_SCOPE, python_func=object_constructor)
    G.builtin_constructors.append(object_cons)
    G.object_cons = object_cons
    # get Object.prototype
    object_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=object_cons)[0]
    G.set_node_attr(object_prototype, ('code', 'Object.prototype'))
    # add Object.prototype.__proto__
    G.add_obj_as_prop(prop_name='__proto__', parent_obj=object_prototype, tobe_added_obj=G.null_obj)
    # add Function (function)
    function_cons = G.add_blank_func_to_scope('Function', scope=G.BASE_SCOPE) # TODO: implement this
    G.builtin_constructors.append(function_cons)
    G.function_cons = function_cons
    # get Function.prototype
    function_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=function_cons)[0]
    G.set_node_attr(function_prototype, ('code', 'Function.prototype'))
    # Function.__proto__ = Function.prototype (beacuse Function is a function)
    function__proto__ = G.add_obj_as_prop(prop_name='__proto__', parent_obj=function_cons, tobe_added_obj=function_prototype)
    # Function.prototype.__proto__ = Object.prototype (because Function.prototype is an object)
    function__proto____proto__ = G.add_obj_as_prop(prop_name='__proto__', parent_obj=function_prototype, tobe_added_obj=object_prototype)
    # Object.__proto__ = Function.prototype (beacuse Object is a function)
    G.add_obj_as_prop(prop_name='__proto__', parent_obj=object_cons, tobe_added_obj=function_prototype)
    # set reserved values
    G.function_prototype = function_prototype
    G.object_prototype = object_prototype

    # object built-in functions
    G.add_blank_func_as_prop('keys', object_cons, object_keys)
    G.add_blank_func_as_prop('values', object_cons, object_values)
    G.add_blank_func_as_prop('entries', object_cons, object_entries)
    G.add_blank_func_as_prop('defineProperty', object_cons, blank_func)
    G.add_blank_func_as_prop('defineProperties', object_cons, blank_func)
    G.add_blank_func_as_prop('assign', object_cons, object_assign_real)
    G.add_blank_func_as_prop('create', object_cons, object_create)

    G.add_obj_as_prop('getOwnPropertySymbols', parent_obj=object_cons, tobe_added_obj=G.false_obj)

    G.add_blank_func_as_prop('toString', object_prototype, object_p_to_string)
    G.add_blank_func_as_prop('toLocaleString', object_prototype, object_p_to_string)
    G.add_blank_func_as_prop('valueOf', object_prototype, this_returning_func)
    G.add_blank_func_as_prop('hasOwnProperty', object_prototype, object_p_has_own_property)

    # function built-in functions
    G.add_blank_func_as_prop('call', function_prototype, function_p_call)
    G.add_blank_func_as_prop('apply', function_prototype, function_p_apply)
    G.add_blank_func_as_prop('bind', function_prototype, function_p_bind)


def setup_global_functions(G: Graph):
    parse_int = G.add_blank_func_to_scope('parseInt', G.BASE_SCOPE, parse_number)
    parse_float = G.add_blank_func_to_scope('parseFloat', G.BASE_SCOPE, parse_number)
    decode_uri = G.add_blank_func_to_scope('decodeURI', G.BASE_SCOPE, string_returning_func)
    decode_uri_component = G.add_blank_func_to_scope('decodeURIComponent', G.BASE_SCOPE, string_returning_func)
    encode_uri = G.add_blank_func_to_scope('encodeURI', G.BASE_SCOPE, string_returning_func)
    encode_uri_component = G.add_blank_func_to_scope('encodeURIComponent', G.BASE_SCOPE, string_returning_func)
    escape = G.add_blank_func_to_scope('escape', G.BASE_SCOPE, string_returning_func)
    unescape = G.add_blank_func_to_scope('unescape', G.BASE_SCOPE, string_returning_func)
    set_timeout = G.add_blank_func_to_scope('setTimeout', G.BASE_SCOPE, func_calling_func)
    clear_timeout = G.add_blank_func_to_scope('clearTimeout', G.BASE_SCOPE, blank_func)
    set_interval = G.add_blank_func_to_scope('setInterval', G.BASE_SCOPE, func_calling_func)
    clear_interval = G.add_blank_func_to_scope('clearInterval', G.BASE_SCOPE, blank_func)

    require = G.add_blank_func_to_scope('require', G.BASE_SCOPE, handle_require)
    #jseval = G.add_blank_func_to_scope('eval', G.BASE_SCOPE, opgen.handle_eval)


def array_p_for_each(G: Graph, caller_ast, extra, array=NodeHandleResult(), callback=NodeHandleResult(), this=None):
    for arr in array.obj_nodes:
        for name_node in G.get_prop_name_nodes(arr):
            name = G.get_node_attr(name_node).get('name')
            if not is_int(name):
                continue
            obj_nodes = G.get_obj_nodes(name_node, branches=extra.branches)
            if str(name).startswith('Obj#'):
                name_obj_node = name[4:]
            else:
                name_obj_node = G.add_obj_node(ast_node=caller_ast,
                    js_type='number', value=float(name))
            obj_nodes_log = ', '.join([f'{obj}: {G.get_node_attr(obj).get("code")}' for obj in obj_nodes])
            logger.debug(f'Array forEach callback arguments: index={name} ({name_obj_node}), obj_nodes={obj_nodes_log}, array={arr}')
            call_function(G, callback.obj_nodes,
                args=[NodeHandleResult(name_nodes=[name_node], name=name,
                        obj_nodes=obj_nodes),
                    NodeHandleResult(obj_nodes=[name_obj_node]),
                    NodeHandleResult(name=array.name, obj_nodes=[arr])],
                this=this, extra=extra, caller_ast=caller_ast)
    return NodeHandleResult(obj_nodes=[G.undefined_obj])


def array_p_for_each_value(G: Graph, caller_ast, extra, array=NodeHandleResult(), callback=NodeHandleResult(), this=None):
    loop_var_names = []
    for cb in callback.obj_nodes:
        try:
            func_ast = G.get_obj_def_ast_node(cb, 'function')
            if func_ast:
                param_list = G.get_child_nodes(func_ast, edge_type='PARENT_OF',
                    child_type='AST_PARAM_LIST')
                params = G.get_ordered_ast_child_nodes(param_list)
                param_name = G.get_name_from_child(params[0])
                if param_name:
                    loop_var_names.append(param_name)
        except IndexError as e:
            print(e)
    loop_var_name = ','.join(loop_var_names)
    for arr in array.obj_nodes:
        name_nodes = G.get_prop_name_nodes(arr)
        for name_node in name_nodes:
            name = G.get_node_attr(name_node).get('name')
            if not is_int(name):
                continue
            obj_nodes = G.get_obj_nodes(name_node, branches=extra.branches)
            if str(name).startswith('Obj#'):
                name_obj_node = name[4:]
                index_arg = NodeHandleResult(obj_nodes=[name_obj_node])
            else:
                index_arg = NodeHandleResult(values=[float(name)])
            obj_nodes_log = ', '.join([f'{obj}: {G.get_node_attr(obj).get("code")}' for obj in obj_nodes])
            logger.debug(f'Array forEach callback arguments: index={name}, obj_nodes={obj_nodes_log}, array={arr}')
            def add_for_stack(G, **kwargs):
                nonlocal name, name_nodes, array
                # full functional for-stack
                # (type, ast node, scope, loop var name, loop var value, loop var value list, loop var origin list)
                G.for_stack.append(('array for each', caller_ast, G.cur_scope, loop_var_name, name, G.get_prop_obj_nodes(arr, numeric_only=True), array.obj_nodes))
            call_function(G, callback.obj_nodes,
                args=[NodeHandleResult(name_nodes=[name_node], name=name,
                    obj_nodes=obj_nodes), index_arg, 
                    NodeHandleResult(name=array.name, obj_nodes=[arr])],
                this=this, extra=extra, caller_ast=caller_ast,
                python_callback=add_for_stack)
            if len(G.for_stack) > 0:
                G.for_stack.pop()
    return NodeHandleResult(obj_nodes=[G.undefined_obj])


def array_p_for_each_static(G: Graph, caller_ast, extra, array: NodeHandleResult, callback=NodeHandleResult(), this=NodeHandleResult()):
    branches = extra.branches
    objs = set()
    for arr in array.obj_nodes:
        elements = G.get_prop_obj_nodes(arr, branches=branches)
        for elem in elements:
            objs.add(elem)
    logger.debug(f'Calling callback functions {callback.obj_nodes} with elements {objs}.')
    for func in callback.obj_nodes:
        func_decl = G.get_obj_def_ast_node(func)
        func_name = G.get_name_from_child(func_decl)
        func_scope = G.add_scope('FUNC_SCOPE', func, f'Function{func_decl}:{caller_ast}', func, caller_ast, func_name)
        call_callback_function(G, caller_ast, func_decl,
            func_scope, args=[NodeHandleResult(obj_nodes=objs)],
            branches=extra.branches)
    return NodeHandleResult()


def array_p_for_each_static_new(G: Graph, caller_ast, extra, array: NodeHandleResult, callback=NodeHandleResult(), this=NodeHandleResult()):
    branches = extra.branches
    objs = []
    names = []
    name_tags = []
    counter = 0
    for arr in array.obj_nodes:
        name_nodes = G.get_prop_name_nodes(arr)
        parent_for_tags = BranchTagContainer(G.get_node_attr(arr)
            .get('for_tags', [])).get_matched_tags(branches, level=1) \
            .set_marks('P')
        for name_node in name_nodes:
            name = G.get_node_attr(name_node).get('name')
            if name != wildcard and not is_int(name):
                continue # check if the index is an integer
            for obj in G.get_obj_nodes(name_node, branches=branches):
                objs.append(obj)
                names.append(name)
                new_tag = BranchTag(point=f'ForEach{caller_ast}',
                                    branch=counter, mark='L')
                obj_tags = G.get_node_attr(obj).get('for_tags', [])
                obj_tags.extend(parent_for_tags + [new_tag])
                G.set_node_attr(obj, ('for_tags', obj_tags))
                name_tags.append(parent_for_tags +  [new_tag])
                counter += 1
    args = [NodeHandleResult(obj_nodes=objs),
            NodeHandleResult(values=names, value_tags=name_tags),
            array]
    logger.debug(f'Calling callback functions {callback.obj_nodes} with elements {objs}.')
    new_extra = ExtraInfo(extra, branches=extra.branches+[BranchTag(point=f'ForEach{caller_ast}')])
    call_function(G, callback.obj_nodes, args=args,
        extra=new_extra, caller_ast=caller_ast, func_name=callback.name)
    return NodeHandleResult()


def array_p_push(G: Graph, caller_ast, extra, arrays: NodeHandleResult, *tobe_added_objs: NodeHandleResult):
    used_objs = set()
    if extra.branches.get_last_choice_tag():
        logger.debug('Copy arrays {} for branch {}, name nodes {}'.format(arrays.obj_nodes, extra.branches.get_last_choice_tag(), arrays.name_nodes))
        arrays = copy_objs_for_branch(G, arrays,
            branch=extra.branches.get_last_choice_tag(), ast_node=caller_ast)
    for arr in arrays.obj_nodes:
        length_objs = G.get_prop_obj_nodes(parent_obj=arr, prop_name='length', branches=extra.branches)
        if len(length_objs) == 0:
            logger.warning('Array {} has no length object nodes'.format(arr))
            length = wildcard
        else:
            if len(length_objs) != 1:
                logger.warning('Array {} has {} length object nodes'.format(arr, len(length_objs)))
            length = G.get_node_attr(length_objs[0]).get('code')
        if length != wildcard:
            try:
                length = int(length)
                for i, objs in enumerate(tobe_added_objs):
                    obj_nodes = to_obj_nodes(G, objs, caller_ast)
                    used_objs.update(obj_nodes)
                    for obj in obj_nodes:
                        G.add_obj_as_prop(prop_name=str(length+i), parent_obj=arr, tobe_added_obj=obj)
                G.set_node_attr(length_objs[0], ('code', length + len(tobe_added_objs)))
            except ValueError:
                logger.error('Array {} length error'.format(arr))
        else:
            convert_prop_names_to_wildcard(G, arr, exclude_length=True) # convert indices to wildcard
            for i, objs in enumerate(tobe_added_objs):
                obj_nodes = to_obj_nodes(G, objs, caller_ast)
                used_objs.update(obj_nodes)
                for obj in obj_nodes:
                    G.add_obj_as_prop(prop_name=wildcard, parent_obj=arr, tobe_added_obj=obj)
    return NodeHandleResult(used_objs=list(used_objs))


def array_p_pop(G: Graph, caller_ast, extra, arrays: NodeHandleResult):
    returned_objs = set()
    if extra.branches.get_last_choice_tag():
        logger.debug('Copy arrays {} for branch {}, name nodes {}'.format(arrays.obj_nodes, extra.branches.get_last_choice_tag(), arrays.name_nodes))
        arrays = copy_objs_for_branch(G, arrays,
            branch=extra.branches.get_last_choice_tag(), ast_node=caller_ast)
    for arr in arrays.obj_nodes:
        length_objs = G.get_prop_obj_nodes(parent_obj=arr, prop_name='length', branches=extra.branches)
        if len(length_objs) == 0:
            logger.warning('Array {} has no length object nodes'.format(arr))
            length = wildcard
        else:
            if len(length_objs) != 1:
                logger.warning('Array {} has {} length object nodes'.format(arr, len(length_objs)))
            length = G.get_node_attr(length_objs[0]).get('code')
        if length != wildcard:
            try:
                length = int(length)
                returned_objs.update(G.get_prop_obj_nodes(parent_obj=arr, prop_name=str(length-1), branches=extra.branches))
                name_node = G.get_prop_name_node(prop_name=str(length-1), parent_obj=arr)
                G.remove_all_edges_between(arr, name_node)
                G.set_node_attr(length_objs[0], ('code', length - 1))
            except ValueError:
                logger.error('Array {} length error'.format(arr))
        else:
            returned_objs.update(G.get_prop_obj_nodes(parent_obj=arr, branches=extra.branches, numeric_only=True))
    return NodeHandleResult(obj_nodes=list(returned_objs))


def array_p_shift(G: Graph, caller_ast, extra, arrays: NodeHandleResult):
    returned_objs = set()
    if extra.branches.get_last_choice_tag():
        logger.debug('Copy arrays {} for branch {}, name nodes {}'.format(arrays.obj_nodes, extra.branches.get_last_choice_tag(), arrays.name_nodes))
        arrays = copy_objs_for_branch(G, arrays,
            branch=extra.branches.get_last_choice_tag(), ast_node=caller_ast)
        # print('new arrays', arrays)
    for arr in arrays.obj_nodes:
        for prop_name_node in G.get_prop_name_nodes(arr):
            name = G.get_node_attr(prop_name_node).get('name')
            try:
                assert name is not None
                # print('name=', name)
                if name == wildcard:
                    returned_objs.update(G.get_obj_nodes(prop_name_node, extra.branches))
                    continue
                i = int(name)
                if i == 0:
                    objs = G.get_obj_nodes(prop_name_node, extra.branches)
                    returned_objs.update(objs)
                    for obj in objs:
                        G.remove_all_edges_between(prop_name_node, obj)
                    G.remove_all_edges_between(arr, prop_name_node)
                else:
                    # print(prop_name_node, i, '->', i-1)
                    G.set_node_attr(prop_name_node, ('name', str(i - 1)))
            except ValueError:
                pass
                # logger.error('Array {} length error'.format(arr))
    return NodeHandleResult(obj_nodes=list(returned_objs))


def array_p_splice(G: Graph, caller_ast, extra, arrays: NodeHandleResult, starts: NodeHandleResult=NodeHandleResult(values=[wildcard]), delete_counts=NodeHandleResult(values=[wildcard]), *items: NodeHandleResult):
    used_objs = set()
    start_values, start_sources, _ = to_values(G, starts)
    dc_values, dc_sources, _ = to_values(G, delete_counts)
    returned_arrays = []
    for arr in arrays.obj_nodes:
        copies = []
        delete = True
        for i, start in enumerate(start_values):
            for j, dc in enumerate(dc_values):
                if start != wildcard:
                    try:
                        start = int(start)
                        dc = int(dc) if dc != wildcard else None
                        elements, data = to_python_array(G, arr)
                        left_part_e = elements[:start]
                        left_part_d = data[:start]
                        if dc != wildcard:
                            returned_part_e = elements[start:start+dc]
                            returned_part_d = data[start:start+dc]
                            right_part_e = elements[start+dc:]
                            right_part_d = data[start+dc:]
                        else:
                            returned_part_e = elements[start:]
                            returned_part_d = data[start:]
                            right_part_e = []
                            right_part_d = []
                        inserted_part_e = []
                        inserted_part_d = []
                        for item in items:
                            item_obj_nodes = to_obj_nodes(G, item, caller_ast)
                            inserted_part_e.append(item_obj_nodes)
                            l = len(item_obj_nodes)
                            inserted_part_d.append([
                                {'branch': BranchTagContainer(extra.branches)
                                .get_last_choice_tag()}] * l)
                            used_objs.update(item_obj_nodes)
                        new_arr = to_og_array(G,
                            left_part_e + inserted_part_e + right_part_e,
                            left_part_d + inserted_part_d + right_part_d,
                            caller_ast)
                        returned_arr = to_og_array(G, returned_part_e,
                            returned_part_d, caller_ast)
                        for s in start_sources[i]:
                            add_contributes_to(G, [s], new_arr)
                            add_contributes_to(G, [s], returned_arr)
                        for s in dc_sources[j]:
                            add_contributes_to(G, [s], new_arr)
                            add_contributes_to(G, [s], returned_arr)
                        for item in items:
                            item_obj_nodes = to_obj_nodes(G, item, caller_ast)
                            # for obj in item_obj_nodes:
                            #     add_contributes_to(G, [obj], new_arr)
                            used_objs.update(item_obj_nodes)
                        add_contributes_to(G, [arr], new_arr)
                        add_contributes_to(G, [arr], returned_arr)
                        copies.append(new_arr)
                        returned_arrays.append(returned_arr)
                    except ValueError:
                        start = wildcard
                        dc = wildcard
                if start == wildcard:
                    returned_arr = G.add_obj_node(ast_node=caller_ast, js_type='array')
                    add_contributes_to(G, [arr], returned_arr)
                    for obj in G.get_prop_obj_nodes(arr, numeric_only=True):
                        G.add_obj_as_prop(prop_name=wildcard, parent_obj=returned_arr,
                            tobe_added_obj=obj)
                    if items:
                        new_arr = G.copy_obj(arr, caller_ast)
                        convert_prop_names_to_wildcard(G, new_arr, exclude_length=True)
                        add_contributes_to(G, [arr], new_arr)
                        for item in items:
                            for obj in item.obj_nodes:
                                G.add_obj_as_prop(prop_name=wildcard,
                                    parent_obj=new_arr, tobe_added_obj=obj)
                        copies.append(new_arr)
                    else:
                        delete = False
        for e in G.get_in_edges(arr, edge_type='NAME_TO_OBJ'):
            name_node, _, k, data = e
            if name_node in arrays.name_nodes:
                if delete and copies:
                    G.graph.remove_edge(name_node, arr, k)
                for obj in copies:
                    G.add_edge(name_node, obj, data)
    used_objs.update(arrays.obj_nodes + list(filter(lambda x: x != wildcard,
        chain(*start_sources, *dc_sources))))
    return NodeHandleResult(obj_nodes=returned_arrays, used_objs=list(used_objs))


def array_p_slice(G: Graph, caller_ast, extra, arrays: NodeHandleResult, starts=NodeHandleResult(values=[wildcard]), ends=NodeHandleResult(values=[wildcard])):
    start_values, start_sources, _ = to_values(G, starts)
    end_values, end_sources, _ = to_values(G, ends)
    returned_arrays = []
    used_objs = set()
    for arr in arrays.obj_nodes:
        if G.get_node_attr(arr).get('code') == wildcard:
            return_arr = G.add_obj_node(caller_ast, 'array', wildcard)
            returned_arrays.append(return_arr)
            add_contributes_to(G, [arr], return_arr)
            continue
        for i, start in enumerate(start_values):
            for j, end in enumerate(end_values):
                if start != wildcard:
                    try:
                        start = int(start)
                        end = int(end) if end != wildcard else None
                        a, d = to_python_array(G, arr)
                        a = a[start:end]
                        d = d[start:end]
                        return_arr = to_og_array(G, a, d, caller_ast)
                    except ValueError:
                        start = wildcard
                if start == wildcard:
                    return_arr = G.copy_obj(arr, caller_ast)
                for s in start_sources[i]:
                    add_contributes_to(G, [s], return_arr)
                for s in end_sources[j]:
                    add_contributes_to(G, [s], return_arr)
                add_contributes_to(G, [arr], return_arr)
                returned_arrays.append(return_arr)
    used_objs.update(chain(*start_sources, *end_sources, arrays.obj_nodes))
    return NodeHandleResult(obj_nodes=returned_arrays, used_objs=list(used_objs))


def array_p_join(G: Graph, caller_ast, extra, arrays: NodeHandleResult, seps=NodeHandleResult(values=[','])):
    returned_objs = []
    used_objs = set()
    sep_values, sep_sources, _ = to_values(G, seps)
    for arr in arrays.obj_nodes:
        for i, sep in enumerate(sep_values):
            if sep == wildcard:
                sep = ','
            a = to_python_array(G, arr, value=True)[0]
            if wildcard in chain(*a) or G.get_node_attr(arr).get('code') == wildcard:
                # if any element's value in the array is unknown
                # the result is set to unknown
                # this is to prevent explosion of the number of different
                # values in the results
                s = wildcard
            else:
                s = sep.join(['/'.join(elem) for elem in a])
            new_literal = G.add_obj_node(caller_ast, 'string', value=s)
            returned_objs.append(new_literal)
            elem_objs = G.get_prop_obj_nodes(arr, branches=extra.branches,
                numeric_only=True)
            for obj in elem_objs:
                add_contributes_to(G, [obj], new_literal)
            for s in sep_sources[i]:
                add_contributes_to(G, [s], new_literal)
            add_contributes_to(G, [arr], new_literal)
            used_objs.update(elem_objs)
            used_objs.update(sep_sources[i])
            used_objs.add(arr)
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=list(used_objs))


def array_p_join_2(G: Graph, caller_ast, extra, arrays: NodeHandleResult, seps=NodeHandleResult(values=[','])):
    returned_objs = []
    used_objs = set()
    sep_values, sep_sources, _ = to_values(G, seps)
    op_index = 0
    for arr in arrays.obj_nodes:
        for i, sep in enumerate(sep_values):
            if sep == wildcard:
                sep = ','
            s = ''
            result_str_obj = G.add_obj_node(caller_ast, 'string')
            wildcard_elems = []
            array_elems = []
            for index_name_node in G.get_prop_name_nodes(arr):
                index = G.get_node_attr(index_name_node).get('name')
                _index = None
                try:
                    _index = int(index)
                except (ValueError, TypeError) as e:
                    pass
                if _index is None:
                    wildcard_elems.extend(G.get_objs_by_name_node(index_name_node))
                else:
                    while len(array_elems) <= _index:
                        array_elems.append([])
                    array_elems[_index].extend(G.get_objs_by_name_node(index_name_node))
            array_elems.append(wildcard_elems)
            random = get_random_hex()
            for j, content in enumerate(array_elems):
                if j != 0:
                    s += sep
                    add_contributes_to(G, sep_sources[i], result_str_obj, 'string_concat', op_index, random)
                    op_index += 1
                s += '/'.join([str(val_to_str(G.get_node_attr(obj).get('code'))) for obj in content])
                add_contributes_to(G, array_elems[j], result_str_obj, 'string_concat', op_index, random)
                used_objs.update(array_elems[j])
                op_index += 1
            if len(array_elems) == 0:
            # if G.get_node_attr(arr).get('code') == wildcard:
                s = wildcard
                add_contributes_to(G, sep_sources[i], result_str_obj, 'array_join', 1)
            G.set_node_attr(result_str_obj, ('code', s))
            add_contributes_to(G, [arr], result_str_obj, 'array_join', 0)
            returned_objs.append(result_str_obj)
            used_objs.add(arr)
            used_objs.update(sep_sources[i])
            op_index += 1
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=list(used_objs))


def array_p_join_3(G: Graph, caller_ast, extra, arrays: NodeHandleResult, seps=NodeHandleResult(values=[','])):
    returned_objs = []
    used_objs = set()
    set_obj_nodes = to_obj_nodes(G, seps, ast_node=caller_ast)
    for arr in arrays.obj_nodes:
        for i, sep_obj in enumerate(set_obj_nodes):
            sep = val_to_str(G.get_node_attr(sep_obj).get('code'))
            if sep == wildcard:
                sep = ','
            s = ''
            wildcard_elems = []
            array_elems = []
            for index_name_node in G.get_prop_name_nodes(arr):
                index = G.get_node_attr(index_name_node).get('name')
                _index = None
                try:
                    _index = int(index)
                except (ValueError, TypeError) as e:
                    pass
                if _index is None or _index < 0:
                    wildcard_elems.extend(G.get_objs_by_name_node(index_name_node))
                else:
                    while len(array_elems) <= _index:
                        array_elems.append([])
                    array_elems[_index].extend(G.get_objs_by_name_node(index_name_node))
            # print('array_elems:', array_elems)
            # print('wildcard_elems:', wildcard_elems)
            array_elems.append(wildcard_elems)
            def dfs(j=0, s="", sources=[]):
                nonlocal G, array_elems, returned_objs
                if j >= len(array_elems):
                    result_str_obj = G.add_obj_node(caller_ast, 'string', s)
                    returned_objs.append(result_str_obj)
                    add_contributes_to(G, sources, result_str_obj, 'string_concat')
                    add_contributes_to(G, [arr], result_str_obj, 'array_join', 0)
                    return
                _sources = list(sources)
                _s = str(s)
                if j != 0:
                    _s += sep
                    _sources = _sources + [sep_obj]
                # the length of current array elems may be 0
                if len(array_elems[j]) == 0:
                    dfs(j + 1, _s, _sources)

                for obj in array_elems[j]:
                    _value = val_to_str(G.get_node_attr(obj).get('code'))
                    if _value == wildcard or s == wildcard:
                        dfs(j + 1, wildcard, _sources + [obj])
                    else:
                        dfs(j + 1, _s + _value, _sources + [obj])
            
            # if G.get_node_attr(arr).get('code') == wildcard:
            if len(array_elems) == 0:
                result_str_obj = G.add_obj_node(caller_ast, 'string', wildcard)
                add_contributes_to(G, sep_obj, result_str_obj, 'array_join', 1)
            else:
                # let's try to avoid dfs when -s is added
                if options.single_branch:
                    merged = chain(*array_elems)
                    merged_str = ""
                    for obj in merged:
                        _value = val_to_str(G.get_node_attr(obj).get('code'))
                        if _value == wildcard or merged_str == wildcard:
                            merged_str = wildcard 
                        else:
                            merged_str += _value
                    result_str_obj = G.add_obj_node(caller_ast, 'string', merged_str)
                    returned_objs.append(result_str_obj)
                    add_contributes_to(G, merged, result_str_obj, 'string_concat')
                    add_contributes_to(G, [arr], result_str_obj, 'array_join', 0)
                else:
                    dfs()
                used_objs.update(chain(*array_elems))

            used_objs.add(sep_obj)
        used_objs.add(arr)
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=list(used_objs))


def array_p_reduce(G: Graph, caller_ast, extra, arrays: NodeHandleResult, callback: NodeHandleResult,
    initial_values=None):
    returned_objs = []
    returned_values = []
    returned_value_sources = []
    for arr in arrays.obj_nodes:
        # wildcard_elems = G.get_prop_obj_nodes(arr, wildcard, extra.branches)
        length_objs = G.get_prop_obj_nodes(arr, 'length')
        if len(length_objs) != 1:
            length = wildcard
        else:
            try:
                length = int(G.get_node_attr(length_objs[0]).get('code'))
            except (ValueError, TypeError) as e:
                logger.error(f'Error: Cannot find length of array {arr}: {e}')
                length = wildcard
        if initial_values is None:
            accumulator = NodeHandleResult(obj_nodes=G.get_prop_obj_nodes(arr, '0', extra.branches))
            start = 1
        else:
            accumulator = initial_values
            start = 0
        returns = None
        if length != wildcard:
            for i in range(start, length):
                returns = call_function(G, callback.obj_nodes,
                    args=[accumulator, NodeHandleResult(
                        obj_nodes=G.get_prop_obj_nodes(arr, str(i), extra.branches)),
                        NodeHandleResult(values=[i], value_sources=[[arr]]),
                        NodeHandleResult(obj_nodes=[arr])],
                    extra=extra, caller_ast=caller_ast)[0]
                accumulator = returns
        else:
            for name_node in G.get_prop_name_nodes(arr):
                name = G.get_node_attr(name_node).get('name')
                if name in ['length', '__proto__', 'constructor']:
                    continue
                if start == 1 and str(name) == '0':
                    continue
                returns = call_function(G, callback.obj_nodes,
                    args=[accumulator, NodeHandleResult(
                        obj_nodes=G.get_objs_by_name_node(name_node, extra.branches)),
                        NodeHandleResult(values=[name], value_sources=[[arr]]),
                        NodeHandleResult(obj_nodes=[arr])],
                    extra=extra, caller_ast=caller_ast)[0]
                accumulator = returns
        if returns is not None:
            returned_objs.extend(returns.obj_nodes)
            returned_values.extend(returns.values)
            returned_value_sources.extend(returns.value_sources)
    return NodeHandleResult(obj_nodes=returned_objs, values=returned_values, value_sources=returned_value_sources)
        

def array_p_map(G: Graph, caller_ast, extra, arrays: NodeHandleResult, callback: NodeHandleResult,
    this_args=None):
    if this_args is None:
        this_args = NodeHandleResult(obj_nodes=[G.undefined_obj])
    returned_arrs = []
    for arr in arrays.obj_nodes:
        new_arr = G.add_obj_node(caller_ast, 'array')
        for name_node in G.get_prop_name_nodes(arr):
            name = G.get_node_attr(name_node).get('name')
            if name in ['__proto__', 'constructor']:
                continue
            if name == 'length':
                for o in G.get_objs_by_name_node(name_node, extra.branches):
                    G.add_obj_as_prop(name, parent_obj=new_arr, tobe_added_obj=o)
                continue
            returned = call_function(G, callback.obj_nodes,
                args=[NodeHandleResult(obj_nodes=G.get_objs_by_name_node(name_node, extra.branches)),
                    NodeHandleResult(value=[name], value_sources=[[arr]]),
                    NodeHandleResult(obj_nodes=[arr])],
                this=this_args,
                extra=extra, caller_ast=caller_ast)[0]
            new_elem_objs = to_obj_nodes(G, returned, caller_ast)
            for o in new_elem_objs:
                G.add_obj_as_prop(name, parent_obj=new_arr, tobe_added_obj=o)
                # we don't add element-level CONTRIBUTES_TO here
        returned_arrs.append(new_arr)
        add_contributes_to(G, [arr], new_arr)
    return NodeHandleResult(obj_nodes=returned_arrs, used_objs=arrays.obj_nodes)
                


def array_constructor(G: Graph, caller_ast, extra, _, length=NodeHandleResult(values=[0]), *args):
    lengths, length_sources, _ = to_values(G, length)
    returned_objs = []
    used_objs = list(set(chain(*length_sources)))
    for i, l in enumerate(lengths):
        logger.debug('create an array length {}'.format(l))
        l = val_to_float(l)
        if l == wildcard or isnan(l):
            arr = G.add_obj_node(caller_ast, 'array', wildcard)
            G.add_obj_as_prop('length', caller_ast, 'number', value=wildcard,
                parent_obj=arr)
            G.add_obj_as_prop(wildcard, caller_ast, 'object', value=wildcard,
                parent_obj=arr)
        else:
            length = int(l)
            arr = G.add_obj_node(caller_ast, 'array')
            G.add_obj_as_prop('length', caller_ast, 'number', value=l,
                parent_obj=arr)
            for j in range(length):
                G.add_prop_name_node(str(j), arr)
        add_contributes_to(G, length_sources[i], arr)
        returned_objs.append(arr)
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=used_objs)


def array_p_concat(G: Graph, caller_ast, extra, *arrays: NodeHandleResult):
    returned_objs = []
    parrays = []
    used_objs = set()
    for arr in arrays:
        possibilities = []
        objs = to_obj_nodes(G, arr, caller_ast)
        used_objs.update(objs)
        for obj in objs:
            possibilities.append(to_python_array(G, obj, value=False))
        parrays.append(possibilities)

    def dfs(i=0, b_elem=[], b_edge=[]):
        nonlocal G, parrays
        if i >= len(parrays):
            returned_objs.append(to_og_array(G, b_elem, b_edge, caller_ast))
            return
        for possibility in parrays[i]:
            dfs(i+1, b_elem + possibility[0], b_edge + possibility[1])
    dfs()
    
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=list(used_objs))


def object_keys(G: Graph, caller_ast, extra, _, arg: NodeHandleResult, for_array=False):
    returned_objs = []
    for obj in arg.obj_nodes:
        arr = G.add_obj_node(caller_ast, 'array')
        i = 0
        for name_node in G.get_prop_name_nodes(obj):
            name = G.get_node_attr(name_node).get('name')
            # print(name_node, name, for_array)
            assert name is not None
            if not for_array and name == wildcard:
                continue
            if name == '__proto__':
                continue
            if for_array and not str(name).isdigit():
                continue # Array only returns numeric keys/corresponding values
            string = G.add_obj_node(caller_ast, 'string', str(name))
            add_contributes_to(G, [obj], string)
            G.add_obj_as_prop(str(i), parent_obj=arr, tobe_added_obj=string)
            i += 1
        # wildcard object
        if G.get_node_attr(obj).get('type') in ['array', 'object'] and \
            G.get_node_attr(obj).get('code') == wildcard:
            # print('**wildcard**')
            string = G.add_obj_node(caller_ast, 'string', wildcard)
            add_contributes_to(G, [obj], string)
            G.add_obj_as_prop(str(i), parent_obj=arr, tobe_added_obj=string)
        returned_objs.append(arr)
    return NodeHandleResult(obj_nodes=returned_objs)


def object_values(G: Graph, caller_ast, extra, _, arg: NodeHandleResult, for_array=False):
    returned_objs = []
    for obj in arg.obj_nodes:
        arr = G.add_obj_node(caller_ast, 'array')
        for i, name_node in enumerate(G.get_prop_name_nodes(obj)):
            name = G.get_node_attr(name_node).get('name')
            assert name is not None
            if not for_array and name == wildcard:
                continue
            if name == '__proto__':
                continue
            if for_array and not str(name).isdigit():
                continue # Array only returns numeric keys/corresponding values
            prop_objs = G.get_objs_by_name_node(name_node)
            for prop_obj in prop_objs:
                G.add_obj_as_prop(str(i), parent_obj=arr, tobe_added_obj=prop_obj)
        # wildcard object
        if G.get_node_attr(obj).get('type') in ['array', 'object'] and \
            G.get_node_attr(obj).get('code') == wildcard:
            wildcard_prop_objs = G.get_prop_obj_nodes(obj, wildcard, extra.branches)
            if not wildcard_prop_objs: # if the wildcard property does not exist
                added_obj = [G.add_obj_as_prop(wildcard, caller_ast,
                                        value=wildcard, parent_obj=obj)]
                add_contributes_to(G, [obj], added_obj)
                wildcard_prop_objs = [added_obj]
            returned_objs.extend(wildcard_prop_objs)
        returned_objs.append(arr)
    return NodeHandleResult(obj_nodes=returned_objs)


def object_entries(G: Graph, caller_ast, extra, _, arg: NodeHandleResult, for_array=False):
    returned_objs = []
    for obj in arg.obj_nodes:
        arr = G.add_obj_node(caller_ast, 'array')
        for i, name_node in enumerate(G.get_prop_name_nodes(obj)):
            child_arr = G.add_obj_node(caller_ast, 'array')
            # key
            name = G.get_node_attr(name_node).get('name')
            if not for_array and name == wildcard:
                continue
            if name == '__proto__':
                continue
            if for_array and not str(name).isdigit():
                continue # Array only returns numeric keys/corresponding values
            string = G.add_obj_node(caller_ast, 'string', name)
            G.add_obj_as_prop('0', parent_obj=child_arr, tobe_added_obj=string)
            # value
            prop_objs = G.get_objs_by_name_node(name_node)
            for prop_obj in prop_objs:
                G.add_obj_as_prop('1', parent_obj=child_arr, tobe_added_obj=prop_obj)
            G.add_obj_as_prop(str(i), parent_obj=arr, tobe_added_obj=child_arr)
        # wildcard object
        if G.get_node_attr(obj).get('type') in ['array', 'object'] and \
            G.get_node_attr(obj).get('code') == wildcard:
            child_arr = G.add_obj_node(caller_ast, 'array')
            wildcard_prop_objs = G.get_prop_obj_nodes(obj, wildcard, extra.branches)
            if not wildcard_prop_objs: # if the wildcard property does not exist
                added_obj = [G.add_obj_as_prop(wildcard, caller_ast,
                                        value=wildcard, parent_obj=obj)]
                add_contributes_to(G, [obj], added_obj)
                wildcard_prop_objs = [added_obj]
            string = G.add_obj_node(caller_ast, 'string', wildcard)
            G.add_obj_as_prop('0', parent_obj=child_arr, tobe_added_obj=string)
            for prop_obj in wildcard_prop_objs:
                G.add_obj_as_prop('1', parent_obj=child_arr, tobe_added_obj=prop_obj)
            G.add_obj_as_prop(str(i+1), parent_obj=arr, tobe_added_obj=child_arr)
        returned_objs.append(arr)
    return NodeHandleResult(obj_nodes=returned_objs)


def object_assign(G: Graph, caller_ast, extra, _, *objects):
    obj_nodes = set()
    for obj in objects:
        obj_nodes.update(obj.obj_nodes)
    return NodeHandleResult(
        obj_nodes=list(obj_nodes), used_objs=list(obj_nodes))

def object_assign_real(G: Graph, caller_ast, extra, _, target, *sources):
    target_objs = to_obj_nodes(G, target, caller_ast)
    used_objs = set()
    for target_obj in target_objs:
        for source in sources:
            for source_obj in to_obj_nodes(G, source, caller_ast):
                used_objs.add(source_obj)
                for name_node in G.get_prop_name_nodes(source_obj):
                    prop_name = G.get_node_attr(name_node).get('name')
                    prop_obj_nodes = G.get_obj_nodes(name_node, extra.branches if extra else None)
                    target_name_node = G.get_prop_name_node(prop_name, target_obj)
                    if target_name_node is None:
                        target_name_node = G.add_prop_name_node(prop_name, target_obj)
                    G.assign_obj_nodes_to_name_node(target_name_node, prop_obj_nodes,
                            branches=extra.branches if extra else BranchTagContainer())
    return NodeHandleResult(obj_nodes=target_objs, used_objs=list(used_objs))

def array_p_keys(G: Graph, caller_ast, extra, this: NodeHandleResult, for_array=False):
    return object_keys(G, caller_ast, extra, None, this, for_array=True)


def array_p_values(G: Graph, caller_ast, extra, this: NodeHandleResult, for_array=False):
    return object_values(G, caller_ast, extra, None, this, for_array=True)


def array_p_entries(G: Graph, caller_ast, extra, this: NodeHandleResult, for_array=False):
    return object_entries(G, caller_ast, extra, None, this, for_array=True)


def array_is_array(G: Graph, caller_ast, extra, _, arrs: NodeHandleResult, *args):
    returned_objs = []
    returned_values = []
    for arr in arrs.obj_nodes:
        # if G.get_node_attr(arr).get('code') == wildcard:
        #     if wildcard not in returned_values:
        #         returned_values.append(wildcard)
        if G.get_node_attr(arr).get('type') == 'array':
            if G.true_obj not in returned_objs:
                returned_objs.append(G.true_obj)
        else:
            if G.false_obj not in returned_objs:
                returned_objs.append(G.false_obj)
    return NodeHandleResult(values=returned_values, obj_nodes=returned_objs)


def object_p_to_string(G: Graph, caller_ast, extra, this: NodeHandleResult, 
        *args):
    returned_objs = []
    for obj in this.obj_nodes:
        # value = G.get_node_attr(obj).get('code')
        string = G.add_obj_node(caller_ast, 'string', '[object Object]')
        add_contributes_to(G, [obj], string)
        returned_objs.append(string)
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=this.obj_nodes)


def object_create(G: Graph, caller_ast, extra, _, proto=NodeHandleResult(), *args):
    returned_objs = []
    for p in proto.obj_nodes:
        new_obj = G.add_obj_node(caller_ast, None)
        G.add_obj_as_prop(prop_name='__proto__', parent_obj=new_obj, tobe_added_obj=p)
        returned_objs.append(new_obj)
    return NodeHandleResult(obj_nodes=returned_objs)


def object_is(G: Graph, caller_ast, extra, _, value1: NodeHandleResult, value2: NodeHandleResult):
    if set(value1.obj_nodes) == set(value2.obj_nodes) and \
            set(value1.values) == set(value2.values):
        return NodeHandleResult(obj_nodes=[G.true_obj])
    else:
        return NodeHandleResult(obj_nodes=[G.false_obj])


# def object_get_own_property_symbols(G: Graph, caller_ast, extra, _, *args):
#     return NodeHandleResult(obj_nodes=[G.false_obj])


def object_p_has_own_property(G: Graph, caller_ast, extra, this, *args):
    used_objs = this.obj_nodes
    used_objs.extend(chain(*[r.obj_nodes for r in args]))
    return NodeHandleResult(values=[wildcard], used_objs=used_objs)


def object_p_has_own_property_f(G: Graph, caller_ast, extra, this, pn=NodeHandleResult()):
    pass


def function_p_call(G: Graph, caller_ast, extra, func: NodeHandleResult, this=NodeHandleResult(), *args):
    r, _ = call_function(
        G, func.obj_nodes, list(args), this, extra, caller_ast,
        stmt_id=f'Call{caller_ast}')
    return r 


def function_p_apply(G: Graph, caller_ast, extra, func: NodeHandleResult, this=NodeHandleResult(), arg_array=None):
    args = []
    if arg_array is not None:
        for array in arg_array.obj_nodes: # for every possible argument array
            i = 0 # argument counter
            while True:
                objs = G.get_prop_obj_nodes(parent_obj=array, prop_name=str(i),
                    branches=extra.branches)
                if objs:
                    # if the counter exceeds the length of the args array,
                    # expand it
                    if i >= len(args):
                        args.append([])
                    # extend possible objects with objects in the array
                    args[i].extend(objs)
                else: # the array is finished (index is larger than its length)
                    break
                i += 1
                if i > 32767:
                    break
    args = [NodeHandleResult(obj_nodes=i) for i in args]
    return function_p_call(G, caller_ast, extra, func, this, *args)


def function_p_bind(G: Graph, caller_ast, extra, func: NodeHandleResult, this=NodeHandleResult(), *args):
    returned_objs = []
    for f in func.obj_nodes:
        ast_node = G.get_obj_def_ast_node(f)
        new_func = G.add_obj_node(ast_node, 'function')
        G.set_node_attr(new_func, ('target_func', f))
        G.set_node_attr(new_func, ('bound_this', this))
        if args:
            G.set_node_attr(new_func, ('bound_args', args))
        returned_objs.append(new_func)
        logger.info('Bind function {} to {}, this={}, AST node {}'.format(f, new_func, this.obj_nodes, ast_node))
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=func.obj_nodes)


def parse_number(G: Graph, caller_ast, extra, _, s=NodeHandleResult(), rad=None):
    returned_objs = []
    for obj in s.obj_nodes:
        new_literal = G.add_obj_node(caller_ast, 'number')
        returned_objs.append(new_literal)
        add_contributes_to(G, [obj], new_literal)
    used_objs = list(set(s.obj_nodes + s.used_objs))
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=used_objs)


def blank_func(G: Graph, caller_ast, extra, _, *args):
    used_objs = []
    if _ is not None:    
        used_objs.extend(_.obj_nodes)
        used_objs.extend(chain(*[r.obj_nodes for r in args]))
    return NodeHandleResult(used_objs=used_objs)


def func_calling_func(G: Graph, caller_ast, extra, _, *args):
    dummy_return_obj = G.add_obj_node(caller_ast, value=wildcard)
    used_objs = set()
    for arg in args:
        filtered_objs = list(filter(lambda obj:
            G.get_node_attr(obj).get('type') == 'function', arg.obj_nodes))
        results, _ = call_function(G, filtered_objs, extra=extra)
        used_objs.update(results.obj_nodes)
    add_contributes_to(G, used_objs, dummy_return_obj)
    return NodeHandleResult(obj_nodes=[dummy_return_obj], used_objs=list(used_objs))


def this_returning_func(G: Graph, caller_ast, extra, this=None, *args):
    if this is None:
        if args:
            return args[0]
        else:
            return NodeHandleResult()
    else:
        return this


def string_returning_func(G: Graph, caller_ast, extra, _, *args):
    returned_string = G.add_obj_node(caller_ast, 'string', wildcard)
    used_objs = set()
    for arg in args:
        used_objs.update(arg.obj_nodes)
        # used_objs.update(arg.used_objs)
        for obj in arg.obj_nodes:
            add_contributes_to(G, [obj], returned_string)
    return NodeHandleResult(obj_nodes=[returned_string], used_objs=list(used_objs))


def boolean_returning_func(G: Graph, caller_ast, extra, _, *args):
    used_objs = set()
    for arg in args:
        used_objs.update(arg.obj_nodes)
        # used_objs.update(arg.used_objs)
    return NodeHandleResult(obj_nodes=[G.true_obj, G.false_obj], used_objs=list(used_objs))


def object_constructor(G: Graph, caller_ast, extra, _, *args):
    returned_obj = G.add_obj_node(caller_ast)
    used_objs = chain(*[arg.obj_nodes for arg in args])
    add_contributes_to(G, used_objs, returned_obj)
    return NodeHandleResult(obj_nodes=[returned_obj], used_objs=list(used_objs))


def number_constructor(G: Graph, caller_ast, extra, _, *args):
    returned_obj = G.add_obj_node(caller_ast, None)
    G.add_obj_as_prop('__proto__', parent_obj=returned_obj, tobe_added_obj=G.number_prototype)
    G.add_obj_as_prop('constructor', parent_obj=returned_obj, tobe_added_obj=G.number_cons)
    used_objs = chain(*[arg.obj_nodes for arg in args])
    add_contributes_to(G, used_objs, returned_obj)
    return NodeHandleResult(obj_nodes=[returned_obj], used_objs=list(used_objs))


def setup_global_objs(G: Graph):
    console_obj = G.add_obj_to_scope(name='console', scope=G.BASE_SCOPE)
    G.add_blank_func_as_prop('log', console_obj, console_log)
    G.add_blank_func_as_prop('error', console_obj, console_log)

    process_obj = G.add_obj_to_scope(name='process', scope=G.BASE_SCOPE, js_type='object', value=wildcard)
    G.add_obj_as_prop(prop_name='argv', parent_obj=process_obj, js_type='array', value=wildcard)
    version_obj = G.add_obj_as_prop(prop_name='versions', parent_obj=process_obj, js_type='object', value=wildcard)
    G.add_obj_as_prop(prop_name='modules', parent_obj=version_obj, js_type='string', value=wildcard)
    G.add_obj_as_prop(prop_name='platform', parent_obj=process_obj, js_type='string', value=wildcard)
    G.add_obj_as_prop(prop_name='arch', parent_obj=process_obj, js_type='string', value=wildcard)


def console_log(G: Graph, caller_ast, extra, _, *args):
    used_objs = set()
    for i, arg in enumerate(args):
        used_objs.update(arg.obj_nodes)
        # used_objs.update(arg.used_objs)
        values = list(map(str, arg.values))
        for obj in arg.obj_nodes:
            if G.get_node_attr(obj).get('type') == 'array':
                value = to_python_array(G, obj, value=True)[0]
            else:
                value = G.get_node_attr(obj).get('code')
            values.append(f'{obj}: {val_to_str(value)}')
        logger.debug(f'Argument {i} values: ' + ', '.join(values))
    return NodeHandleResult(obj_nodes=[G.undefined_obj], used_objs=list(used_objs))


def setup_json(G: Graph):
    console_obj = G.add_obj_to_scope(name='JSON', scope=G.BASE_SCOPE)
    G.add_blank_func_as_prop('parse', console_obj, json_parse)
    G.add_blank_func_as_prop('stringify', console_obj, string_returning_func)

def analyze_json_python(G, json_str, extra=None, caller_ast=None):
    json_str = str(json_str)
    if json_str is None:
        return None
    try:
        py_obj = json.loads(json_str)
        logger.debug('Python JSON parse result: ' + str(py_obj))
    except json.decoder.JSONDecodeError:
        return None
    return G.generate_obj_graph_for_python_obj(py_obj, ast_node=caller_ast)

def json_parse(G: Graph, caller_ast, extra, _, text=None, reviver=None):
    json_strings, sources, _ = to_values(G, text, caller_ast)
    returned_objs = []
    used_objs = set()
    for i, json_string in enumerate(json_strings):
        obj = analyze_json_python(G, json_string,
            extra=extra, caller_ast=caller_ast)
        if obj is None:
            obj = G.add_obj_node(ast_node=caller_ast, js_type=None, value=wildcard)
        for s in sources[i]:
            add_contributes_to(G, [s], obj)
            used_objs.add(s)
        returned_objs.append(obj)
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=list(used_objs))


def setup_regexp(G: Graph):
    regexp_cons = G.add_blank_func_to_scope('RegExp', scope=G.BASE_SCOPE,
        python_func=regexp_constructor)
    G.builtin_constructors.append(regexp_cons)
    regexp_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=regexp_cons)[0]
    G.regexp_prototype = regexp_prototype
    # built-in functions
    G.add_blank_func_as_prop('exec', regexp_prototype, None)
    G.add_blank_func_as_prop('test', regexp_prototype, None)


def regexp_constructor(G: Graph, caller_ast, extra, _, pattern=NodeHandleResult(),
    flags=NodeHandleResult()):
    returned_objs = []
    if pattern.obj_nodes:
        flag_objs = flags.obj_nodes if flags else []
        for p in pattern.obj_nodes:
            for f in flag_objs:
                pv = G.get_node_attr(p).get('code')
                fv = G.get_node_attr(f).get('code')
                if pv is None or fv is None or pv == wildcard or fv == wildcard:
                    code = wildcard
                else:
                    code = f'/{pv}/{fv}'
                added_obj = G.add_obj_node(ast_node=caller_ast, js_type=None,
                    value=code)
                G.add_obj_as_prop(prop_name='__proto__', parent_obj=added_obj,
                    tobe_added_obj=G.regexp_prototype)
                returned_objs.append(added_obj)
    return NodeHandleResult(obj_nodes=returned_objs,
        used_objs=pattern.obj_nodes+flags.obj_nodes)


def string_p_replace(G: Graph, caller_ast, extra, strs=NodeHandleResult(),
    substrs=NodeHandleResult(), new_sub_strs=NodeHandleResult()):
    returned_objs = []
    unknown_return_obj = None # we only add one unknown object
    for s in to_obj_nodes(G, strs, caller_ast):
        for substr in to_obj_nodes(G, substrs, caller_ast):
            for new_sub_str in to_obj_nodes(G, new_sub_strs, caller_ast):
                sv = G.get_node_attr(s).get('code')
                ssv = G.get_node_attr(substr).get('code')
                if G.get_node_attr(new_sub_str).get('type') == 'function':
                    callback = new_sub_str
                    if sv is None or ssv is None or sv == wildcard or ssv == wildcard:
                        if unknown_return_obj is None:
                            unknown_return_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=wildcard)
                        added_obj = unknown_return_obj
                        add_contributes_to(G, [s], unknown_return_obj)
                        add_contributes_to(G, [substr], unknown_return_obj)
                        add_contributes_to(G, [new_sub_str], unknown_return_obj)
                    elif G.get_prop_obj_nodes(substr, prop_name='__proto__') and  \
                            G.get_prop_obj_nodes(substr, prop_name='__proto__')[0] == G.regexp_prototype:
                        sv = str(sv)
                        ssv = str(ssv)
                        r, glob, sticky = convert_to_python_re(ssv)
                        none_flag = False
                        def python_cb(m):
                            nonlocal none_flag
                            args = [NodeHandleResult(values=[m.group(0)])] + [
                                NodeHandleResult(values=[g]) for g in m.groups()
                            ]
                            cb_result, _ = \
                                call_function(G, [callback],
                                args=args, extra=extra, caller_ast=caller_ast)
                            cb_returned_values, _, _ = to_values(G, cb_result)
                            cb_returned_values = \
                                list(filter(lambda x: x != wildcard, cb_returned_values))
                            # multiple possibility is ignored here
                            if len(cb_returned_values) > 1:
                                logger.warning(f'Replace result has multiple possibilities: {cb_returned_values}')
                            elif len(cb_returned_values) == 0:
                                none_flag = True
                                return None
                            return cb_returned_values[0]
                        if r is None:
                            output = wildcard
                        else:
                            if glob:
                                output = r.sub(python_cb, sv)
                            else:
                                output, _ = r.subn(python_cb, sv, count=1)
                        if none_flag:
                            output = wildcard
                        logger.debug('string replace {} in {} -> {}'.format(ssv, sv, output))
                        added_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=output)
                        add_contributes_to(G, [s], added_obj)
                        add_contributes_to(G, [substr], added_obj)
                        add_contributes_to(G, [new_sub_str], added_obj)
                        returned_objs.append(added_obj)
                    else:
                        sv = str(sv)
                        ssv = str(ssv)
                        returned_values = []
                        start = sv.find(ssv)
                        if start == -1:
                            break
                        match_s = sv[start:start+len(ssv)]
                        left_s = sv[:start]
                        right_s = sv[start+len(ssv):]
                        cb_result, _ = \
                            call_function(G, [callback],
                            args=[NodeHandleResult(values=[match_s])],
                            extra=extra, caller_ast=caller_ast)
                        cb_returned_values, _, _ = to_values(G, cb_result)
                        for s1 in cb_returned_values:
                            returned_values.append(left_s + s1 + right_s)
                            # the part on the left of the match + substituted matched part + the part on the right of the match
                        for s2 in returned_values:
                            logger.debug('string replace {} in {} -> {}'.format(ssv, sv, s2))
                            added_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=s2)
                            add_contributes_to(G, [s], added_obj)
                            add_contributes_to(G, [substr], added_obj)
                            add_contributes_to(G, [new_sub_str], added_obj)
                            returned_objs.append(added_obj)
                else:
                    nssv = G.get_node_attr(new_sub_str).get('code')
                    if sv is None or ssv is None or nssv is None or sv == wildcard or ssv == wildcard or nssv == wildcard:
                        if unknown_return_obj is None:
                            unknown_return_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=wildcard)
                        added_obj = unknown_return_obj
                        add_contributes_to(G, [s], unknown_return_obj)
                        add_contributes_to(G, [substr], unknown_return_obj)
                        add_contributes_to(G, [new_sub_str], unknown_return_obj)
                    else:
                        sv = str(sv)
                        ssv = str(ssv)
                        nssv = str(nssv)
                        prop_obj_nodes = G.get_prop_obj_nodes(substr, prop_name='__proto__')
                        if len(prop_obj_nodes) > 0 and prop_obj_nodes[0] == G.regexp_prototype:
                            r, glob, sticky = convert_to_python_re(ssv)
                            if r is None:
                                output = wildcard
                            else:
                                if glob:
                                    output = r.sub(nssv, sv)
                                else:
                                    output, _ = r.subn(nssv, sv, count=1)
                        else:
                            output = sv.replace(ssv, nssv)
                        logger.debug('string replace {} in {} -> {}'.format(ssv, sv, output))
                        added_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=output)
                        add_contributes_to(G, [s], added_obj)
                        add_contributes_to(G, [substr], added_obj)
                        add_contributes_to(G, [new_sub_str], added_obj)
                    returned_objs.append(added_obj)
    return NodeHandleResult(obj_nodes=returned_objs,
        used_objs=list(set(strs.obj_nodes + substrs.obj_nodes + new_sub_strs.obj_nodes
        + strs.used_objs + substrs.used_objs + new_sub_strs.used_objs)))


def string_p_replace_value(G: Graph, caller_ast, extra, strs=NodeHandleResult(),
    substrs=NodeHandleResult(), new_sub_strs=NodeHandleResult()):
    returned_objs = []
    unknown_return_obj = None # we only add one unknown object
    for sv, str_sources, _ in zip(to_values(G, strs)):
        for substr in to_obj_nodes(G, substrs, caller_ast):
            for new_sub_str in to_obj_nodes(G, new_sub_strs, caller_ast):
                ssv = G.get_node_attr(substr).get('code')
                proto = G.get_prop_obj_nodes(substr, prop_name='__proto__')
                if G.get_node_attr(new_sub_str).get('type') == 'function':
                    callback = new_sub_str
                    if sv is None or ssv is None or sv == wildcard or ssv == wildcard:
                        if unknown_return_obj is None:
                            unknown_return_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=wildcard)
                        added_obj = unknown_return_obj
                        add_contributes_to(G, str_sources, added_obj)
                        add_contributes_to(G, [substr], added_obj)
                        add_contributes_to(G, [new_sub_str], added_obj)
                    elif proto and proto[0] == G.regexp_prototype:
                        sv = str(sv)
                        ssv = str(ssv)
                        r, glob, sticky = convert_to_python_re(ssv)
                        none_flag = False
                        def python_cb(m):
                            nonlocal none_flag
                            args = [NodeHandleResult(values=[m.group(0)])] + [
                                NodeHandleResult(values=[g]) for g in m.groups()
                            ]
                            cb_result, _ = \
                                opgen.call_function(G, [callback],
                                args=args, extra=extra, caller_ast=caller_ast)
                            cb_returned_values, _, _ = to_values(G, cb_result)
                            cb_returned_values = \
                                list(filter(lambda x: x != wildcard, cb_returned_values))
                            # multiple possibility is ignored here
                            if len(cb_returned_values) > 1:
                                logger.warning(f'Replace result has multiple possibilities: {cb_returned_values}')
                            elif len(cb_returned_values) == 0:
                                none_flag = True
                                return None
                            return cb_returned_values[0]
                        if r is None:
                            output = wildcard
                        else:
                            if glob:
                                output = r.sub(python_cb, sv)
                            else:
                                output, _ = r.subn(python_cb, sv, count=1)
                        if none_flag:
                            output = wildcard
                        logger.debug('string replace {} in {} -> {}'.format(ssv, sv, output))
                        added_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=output)
                        add_contributes_to(G, str_sources, added_obj)
                        add_contributes_to(G, [substr], added_obj)
                        add_contributes_to(G, [new_sub_str], added_obj)
                        returned_objs.append(added_obj)
                    else:
                        sv = str(sv)
                        ssv = str(ssv)
                        returned_values = []
                        start = sv.find(ssv)
                        if start == -1:
                            break
                        match_s = sv[start:start+len(ssv)]
                        left_s = sv[:start]
                        right_s = sv[start+len(ssv):]
                        cb_result, _ = \
                            opgen.call_function(G, [callback],
                            args=[NodeHandleResult(values=[match_s])],
                            extra=extra, caller_ast=caller_ast)
                        cb_returned_values, _, _ = to_values(G, cb_result)
                        for s1 in cb_returned_values:
                            returned_values.append(left_s + s1 + right_s)
                            # the part on the left of the match + substituted matched part + the part on the right of the match
                        for s2 in returned_values:
                            logger.debug('string replace {} in {} -> {}'.format(ssv, sv, s2))
                            added_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=s2)
                            add_contributes_to(G, str_sources, added_obj)
                            add_contributes_to(G, [substr], added_obj)
                            add_contributes_to(G, [new_sub_str], added_obj)
                            returned_objs.append(added_obj)
                else:
                    nssv = G.get_node_attr(new_sub_str).get('code')
                    sv = str(sv)
                    ssv = str(ssv)
                    nssv = str(nssv)
                    if sv is None or ssv is None or nssv is None or sv == wildcard or ssv == wildcard or nssv == wildcard:
                        if unknown_return_obj is None:
                            unknown_return_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=wildcard)
                        added_obj = unknown_return_obj
                        add_contributes_to(G, str_sources, added_obj)
                        add_contributes_to(G, [substr], added_obj)
                        add_contributes_to(G, [new_sub_str], added_obj)
                    else:
                        proto = G.get_prop_obj_nodes(substr, prop_name='__proto__')
                        if proto and [0] == G.regexp_prototype:
                            r, glob, sticky = convert_to_python_re(ssv)
                            if r is None:
                                output = wildcard
                            else:
                                if glob:
                                    output = r.sub(nssv, sv)
                                else:
                                    output, _ = r.subn(nssv, sv, count=1)
                        else:
                            output = sv.replace(ssv, nssv)
                        logger.debug('string replace {} in {} -> {}'.format(ssv, sv, output))
                        added_obj = G.add_obj_node(ast_node=caller_ast, js_type='string', value=output)
                        add_contributes_to(G, str_sources, added_obj)
                        add_contributes_to(G, [substr], added_obj)
                        add_contributes_to(G, [new_sub_str], added_obj)
                    returned_objs.append(added_obj)
    return NodeHandleResult(obj_nodes=returned_objs,
        used_objs=list(set(strs.obj_nodes + substrs.obj_nodes + new_sub_strs.obj_nodes
        + strs.used_objs + substrs.used_objs + new_sub_strs.used_objs)))

def string_p_match(G: Graph, caller_ast, extra, strs=NodeHandleResult(), regexps=None):
    if regexps is None or not regexps.obj_nodes:
        added_array = G.add_obj_node(ast_node=caller_ast, js_type='array')
        G.add_obj_as_prop(ast_node=caller_ast, js_type='string', value='', parent_obj=added_array)
        return NodeHandleResult(obj_nodes=[added_array])
    returned_objs = []
    for s in to_obj_nodes(G, strs, caller_ast):
        for regexp in to_obj_nodes(G, regexps, caller_ast):
            sv = G.get_node_attr(s).get('code')
            rv = G.get_node_attr(regexp).get('code')
            if sv is None or sv == wildcard or rv == wildcard:
                added_array = G.add_obj_node(ast_node=caller_ast, js_type='array')
                added_obj = G.add_obj_as_prop(ast_node=caller_ast,
                    prop_name='0', js_type='string', parent_obj=added_array)
                add_contributes_to(G, [s], added_obj)
                add_contributes_to(G, [regexp], added_obj)
                add_contributes_to(G, [s], added_array)
                add_contributes_to(G, [regexp], added_array)
            else:
                sv = str(sv)
                added_array = G.null_obj
                r, glob, sticky = convert_to_python_re(rv)
                if r is None:
                    continue
                if glob:
                    result = r.findall(sv)
                    if result:
                        added_array = G.add_obj_node(ast_node=caller_ast, js_type='array')
                        for i, u in result:
                            added_obj = G.add_obj_as_prop(ast_node=caller_ast, prop_name=i,
                                js_type='string', value=u, parent_obj=added_array)
                            add_contributes_to(G, [s], added_obj)
                            add_contributes_to(G, [regexp], added_obj)
                        add_contributes_to(G, [s], added_array)
                        add_contributes_to(G, [regexp], added_array)
                else:
                    match = re.compile(r).search(sv)
                    if match:
                        added_array = G.add_obj_node(ast_node=caller_ast, js_type='array')
                        for i, u in [match[0]] + match.groups():
                            added_obj = G.add_obj_as_prop(ast_node=caller_ast, prop_name=i,
                                js_type='string', value=u, parent_obj=added_array)
                            add_contributes_to(G, [s], added_obj)
                            add_contributes_to(G, [regexp], added_obj)
                        G.add_obj_as_prop(ast_node=caller_ast, prop_name='index',
                            js_type='number', value=match.start(), parent_obj=added_array)
                        G.add_obj_as_prop(ast_node=caller_ast, prop_name='input',
                            js_type='string', value=sv, parent_obj=added_array)
                        # TODO: groups
                        G.add_obj_as_prop(ast_node=caller_ast, prop_name='groups',
                            parent_obj=added_array, tobe_added_obj=G.undefined_obj)
                        add_contributes_to(G, [s], added_array)
                        add_contributes_to(G, [regexp], added_array)
            returned_objs.append(added_array)
    return NodeHandleResult(obj_nodes=returned_objs,
        used_objs=list(set(strs.obj_nodes + strs.used_objs + regexps.obj_nodes + regexps.used_objs)))

def string_p_split(G: Graph, caller_ast, extra, strs, separators=NodeHandleResult(values=[''])):
    values, s1, _ = to_values(G, strs, caller_ast)
    sep, s2, _ = to_values(G, separators, caller_ast)
    returned_objs = []
    used_objs = set()
    for i, s in enumerate(values):
        for j, p in enumerate(sep):
            arr = G.add_obj_node(ast_node=caller_ast, js_type='array')
            if s == wildcard or p == wildcard:
                logger.debug('string split {} -> ?'.format(s))
                G.set_node_attr(arr, ('code', wildcard))
                v = G.add_obj_as_prop(prop_name=wildcard, ast_node=caller_ast,
                    js_type='string', value=wildcard, parent_obj=arr)
                for ss in s1[i]:
                    add_contributes_to(G, [ss], v)
                    add_contributes_to(G, [ss], arr)
                for ss in s2[j]:
                    add_contributes_to(G, [ss], v)
                    add_contributes_to(G, [ss], arr)
            else:
                # Python does not support empty separator
                result = s.split(p) if p != '' else list(s)
                logger.debug('string split {} -> {}'.format(s, result))
                for k, d in enumerate(result):
                    v = G.add_obj_as_prop(prop_name=str(k), value=d,
                        ast_node=caller_ast, js_type='string', parent_obj=arr)
                    for ss in s1[i]:
                        add_contributes_to(G, [ss], v)
                        add_contributes_to(G, [ss], arr)
                    for ss in s2[j]:
                        add_contributes_to(G, [ss], v)
                        add_contributes_to(G, [ss], arr)
            returned_objs.append(arr)
            used_objs.update(s1[i])
            used_objs.update(s2[j])
    return NodeHandleResult(obj_nodes=returned_objs, used_objs=list(used_objs))


def string_p_reverse(G: Graph, caller_ast, extra, strs):
    values, sources, _ = to_values(G, strs, caller_ast)
    returned_values = []
    for s in values:
        if s != wildcard:
            returned_values.append(str(s)[::-1])
        else:
            returned_values.append(wildcard)
    used_objs = list(filter(lambda x: x != wildcard, chain(*sources)))
    return NodeHandleResult(values=returned_values, value_sources=sources,
        used_objs=used_objs)


def string_p_substring(G: Graph, caller_ast, extra, strs,
    indices_start=NodeHandleResult(values=[0]),
    indices_end=NodeHandleResult(values=[wildcard])):
    values, source1, _ = to_values(G, strs, caller_ast)
    i_starts, source2, _ = to_values(G, indices_start, caller_ast)
    i_ends, source3, _ = to_values(G, indices_end, caller_ast)
    returned_values = []
    returned_sources = []
    used_objs = set()
    for i, s in enumerate(values):
        for j, i_start in enumerate(i_starts):
            for k, i_end in enumerate(i_ends):
                flag = False
                if s != wildcard:
                    if i_start != wildcard:
                        try:
                            if i_end != wildcard:
                                returned_values.append(str(s)[int(i_start):int(i_end)])
                            else:
                                returned_values.append(str(s)[int(i_start):])
                            flag = True
                        except ValueError:
                            logger.warning('string.prototype.substring error, '
                                'values {} {} {}'.format(s, i_start, i_end))
                if not flag:
                    returned_values.append(wildcard)
                returned_sources.append(source1[i] + source2[j] + source3[k])
    logger.debug('string substring RETURNED VALUES: {}'.format(returned_values))
    return NodeHandleResult(values=returned_values,
        value_sources=returned_sources, used_objs=list(used_objs))


def string_p_substr(G: Graph, caller_ast, extra, strs,
    indices_start=NodeHandleResult(values=[0]),
    indices_end=NodeHandleResult(values=[wildcard])):
    values, source1, _ = to_values(G, strs, caller_ast)
    i_starts, source2, _ = to_values(G, indices_start, caller_ast)
    lengths, source3, _ = to_values(G, indices_end, caller_ast)
    returned_values = []
    returned_sources = []
    used_objs = set()
    for i, s in enumerate(values):
        for j, i_start in enumerate(i_starts):
            for k, length in enumerate(lengths):
                flag = False
                if s != wildcard:
                    if i_start != wildcard:
                        try:
                            if length != wildcard:
                                returned_values.append(str(s)
                                    [int(i_start):int(i_start)+int(length)])
                            else:
                                returned_values.append(str(s)[int(i_start):])
                            flag = True
                        except ValueError:
                            logger.warning('string.prototype.substr error, '
                                'values {} {} {}'.format(s, i_start, length))
                if not flag:
                    returned_values.append(wildcard)
                returned_sources.append(source1[i] + source2[j] + source3[k])
                used_objs.update(source1[i])
                used_objs.update(source2[j])
                used_objs.update(source3[k])
    logger.debug('string substr RETURNED VALUES: {}'.format(returned_values))
    return NodeHandleResult(values=returned_values,
        value_sources=returned_sources, used_objs=list(used_objs))


def string_p_to_lower_case(G: Graph, caller_ast, extra, strs):
    values, sources, _ = to_values(G, strs, caller_ast)
    returned_values = []
    for s in values:
        if s != wildcard:
            returned_values.append(str(s).lower())
        else:
            returned_values.append(wildcard)
    used_objs = list(filter(lambda x: x != wildcard, chain(*sources)))
    logger.debug('string toLowerCase RETURNED VALUES: {}'.format(returned_values))
    return NodeHandleResult(values=returned_values, value_sources=sources,
        used_objs=used_objs)


def string_p_to_upper_case(G: Graph, caller_ast, extra, strs):
    values, sources, _ = to_values(G, strs, caller_ast)
    returned_values = []
    for s in values:
        if s != wildcard:
            returned_values.append(str(s).upper())
        else:
            returned_values.append(wildcard)
    used_objs = list(filter(lambda x: x != wildcard, chain(*sources)))
    logger.debug('string toUpperCase RETURNED VALUES: {}'.format(returned_values))
    return NodeHandleResult(values=returned_values, value_sources=sources,
        used_objs=used_objs)


def string_p_trim(G: Graph, caller_ast, extra, strs, *args):
    values, sources, _ = to_values(G, strs, caller_ast)
    returned_values = []
    for s in values:
        if values != wildcard:
            returned_values.append(str(s).strip())
        else:
            returned_values.append(wildcard)
    used_objs = list(filter(lambda x: x != wildcard, chain(*sources)))
    return NodeHandleResult(values=returned_values, value_sources=sources,
        used_objs=used_objs)


def string_p_trim_end(G: Graph, caller_ast, extra, strs, *args):
    values, sources, _ = to_values(G, strs, caller_ast)
    returned_values = []
    for s in values:
        if s != wildcard:
            returned_values.append(str(s).rstrip())
        else:
            returned_values.append(wildcard)
    used_objs = list(filter(lambda x: x != wildcard, chain(*sources)))
    return NodeHandleResult(values=returned_values, value_sources=sources,
        used_objs=used_objs)


def string_p_trim_start(G: Graph, caller_ast, extra, strs, *args):
    values, sources, _ = to_values(G, strs, caller_ast)
    returned_values = []
    for s in values:
        if s != wildcard:
            returned_values.append(str(s).lstrip())
        else:
            returned_values.append(wildcard)
    used_objs = list(filter(lambda x: x != wildcard, chain(*sources)))
    return NodeHandleResult(values=returned_values, value_sources=sources,
        used_objs=used_objs)


def string_p_char_at(G: Graph, caller_ast, extra, strs,
        indices=NodeHandleResult(values=[0])):
    values, sources1, _ = to_values(G, strs, caller_ast)
    indexs, sources2, _ = to_values(G, indices, caller_ast)
    returned_values = []
    returned_sources = []
    used_objs = set()
    for i, s in enumerate(values):
        for j, index in enumerate(indexs):
            if s != wildcard and index != wildcard:
                try:
                    ii = int(index)
                    if ii >= 0 and ii < len(str(s)):
                        returned_values.append(str(s)[ii])
                    else:
                        returned_values.append('')
                except ValueError:
                    returned_values.append(wildcard)
            else:
                returned_values.append(wildcard)
            returned_sources.append(sources1[i] + sources2[j])
            used_objs.update(sources1[i])
            used_objs.update(sources2[j])
    return NodeHandleResult(values=returned_values,
        value_sources=returned_sources, used_objs=list(used_objs))


def split_regexp(code) -> Tuple[str, str]:
    assert code is not None
    if code == wildcard:
        return wildcard, wildcard
    match = re.match(r'^/(.*)/(\w*)$', code)
    if match:
        return match.groups()
    else:
        return wildcard, wildcard


def convert_to_python_re(code) -> Tuple[re.Pattern, bool, bool]:
    pattern, flags = split_regexp(code)
    glob, sticky = False, False
    if pattern != wildcard:
        f = 0
        if flags:
            # ignore these errors if your editor shows
            if 'g' in flags:
                glob = True
            if 'i' in flags:
                f |= re.IGNORECASE
            if 'm' in flags:
                f |= re.MULTILINE
            if 's' in flags:
                f |= re.DOTALL
            if 'u' in flags:
                f |= re.UNICODE
            if 'y' in flags:
                sticky = True
        try:
            return re.compile(pattern, f), glob, sticky
        except re.error:
            return None, None, None
    else:
        return None, None, None


def setup_math(G: Graph):
    math_obj = G.add_obj_to_scope('Math', scope=G.BASE_SCOPE)
    G.add_blank_func_as_prop('max', math_obj, math_max)
    G.add_blank_func_as_prop('min', math_obj, math_min)
    G.add_blank_func_as_prop('sqrt', math_obj, math_sqrt)


def math_max(G: Graph, caller_ast, extra, _, *args: NodeHandleResult):
    returned_values = []
    returned_sources = []
    sources_stack = []
    def recurse(i, prev):
        nonlocal args, returned_values, sources_stack
        if i >= len(args):
            returned_values.append(prev)
            returned_sources.append(list(chain(*sources_stack)))
            return
        values, sources, _ = to_values(G, args[i], for_prop=True)
        for j, v in enumerate(values):
            new = None
            v = val_to_float(v)
            if prev is None:
                new = v
            elif v == wildcard:
                new = wildcard
            elif isnan(v) or (type(prev) == float and v > prev):
                new = v
            else:
                new = prev
            sources_stack.append(sources[j])
            recurse(i + 1, new)
            sources_stack.pop()
    if not args:
        return NodeHandleResult(values=[float("-inf")])
    else:
        recurse(0, None)
        logger.debug(f'returned values: {returned_values}')
        used_objs = list(chain(*returned_sources))
        return NodeHandleResult(values=returned_values, 
                                value_sources=returned_sources,
                                used_objs=used_objs)


def math_min(G: Graph, caller_ast, extra, _, *args: NodeHandleResult):
    returned_values = []
    returned_sources = []
    sources_stack = []
    def recurse(i, prev):
        nonlocal args, returned_values, sources_stack
        if i >= len(args):
            returned_values.append(prev)
            returned_sources.append(list(chain(*sources_stack)))
            return
        values, sources, _ = to_values(G, args[i], for_prop=True)
        for j, v in enumerate(values):
            new = None
            v = val_to_float(v)
            if prev is None:
                new = v
            elif v == wildcard:
                new = wildcard
            elif isnan(v) or (type(prev) == float and v < prev):
                new = v
            else:
                new = prev
            sources_stack.append(sources[j])
            recurse(i + 1, new)
            sources_stack.pop()
    if not args:
        return NodeHandleResult(values=[float("inf")])
    else:
        recurse(0, None)
        logger.debug(f'returned values: {returned_values}')
        used_objs = list(chain(*returned_sources))
        return NodeHandleResult(values=returned_values, 
                                value_sources=returned_sources,
                                used_objs=used_objs)


def math_sqrt(G: Graph, caller_ast, extra, _, *args: NodeHandleResult):
    xs, sources, _ = to_values(G, args[0], for_prop=True)
    returned_values = []
    returned_sources = []
    for i, x in enumerate(xs):
        if x == wildcard:
            returned_values.append(wildcard)
            returned_sources.append(sources[i])
            continue
        try:
            x = float(x)
        except (ValueError, TypeError) as e:
            x = float('nan')
        returned_values.append(math.sqrt(x))
        returned_sources.append(sources[i])
    used_objs = list(chain(*sources))
    return NodeHandleResult(values=returned_values, value_sources=returned_sources,
        used_objs=used_objs)
    

def setup_promise(G: Graph):
    promise_cons = G.add_blank_func_to_scope('Promise', scope=G.BASE_SCOPE, python_func=promise_constructor)
    promise_prototype = G.get_prop_obj_nodes(prop_name='prototype', parent_obj=promise_cons)[0]
    G.promise_cons = promise_cons
    G.builtin_constructors.append(promise_cons)
    G.promise_prototype = promise_prototype
    G.add_blank_func_as_prop('then', promise_prototype, promise_p_then)
    G.add_blank_func_as_prop('catch', promise_prototype, promise_p_catch)
    G.add_blank_func_as_prop('finally', promise_prototype, promise_p_finally)
    G.add_blank_func_as_prop('resolve', promise_cons, promise_resolve)

def promise_constructor(G: Graph, caller_ast, extra, _, executor=NodeHandleResult()):
    promise = G.add_obj_node(caller_ast, None, None)
    executors = to_obj_nodes(G, executor, caller_ast)
    G.set_node_attr(promise, ('executors', executors))
    G.add_obj_as_prop('__proto__', parent_obj=promise, tobe_added_obj=G.promise_prototype)
    G.add_obj_as_prop('constructor', parent_obj=promise, tobe_added_obj=G.promise_cons)
    def resolve(G, caller_ast, extra, this, value=NodeHandleResult(obj_nodes=[G.undefined_obj])):
        nonlocal promise
        G.set_node_attr(promise, ('fulfilled_with', value))
        return NodeHandleResult()
    def reject(G, caller_ast, extra, this, value=NodeHandleResult(obj_nodes=[G.undefined_obj])):
        nonlocal promise
        G.set_node_attr(promise, ('rejected_with', value))
        return NodeHandleResult()
    resolve_obj = G.add_blank_func_with_og_nodes('resolve', python_func=resolve)
    reject_obj = G.add_blank_func_with_og_nodes('reject', python_func=reject)
    call_function(G, executors,
        args=[NodeHandleResult(obj_nodes=[resolve_obj]), NodeHandleResult(obj_nodes=[reject_obj])],
        extra=extra, caller_ast=caller_ast)
    return NodeHandleResult(obj_nodes=[promise], used_objs=executors)

def promise_p_then(G: Graph, caller_ast, extra, this, on_fulfilled=NodeHandleResult(), on_rejected=NodeHandleResult()):
    new_promise = G.add_obj_node(caller_ast, None, None)
    old_promises = this.obj_nodes
    def check_promise_status(self, G):
        nonlocal old_promises, on_fulfilled, on_rejected, extra
        for promise in old_promises:
            flag = False
            fulfilled_with = G.get_node_attr(promise).get('fulfilled_with')
            if fulfilled_with is not None: # the promise is possibly fulfilled
                result, _ = call_function(G, on_fulfilled.obj_nodes,
                    args=[fulfilled_with], caller_ast=caller_ast)
                G.set_node_attr(new_promise, ('fulfilled_with', result))
                flag = True
            rejected_with = G.get_node_attr(promise).get('rejected_with')
            if rejected_with is not None: # the promise is possibly rejected
                result, _ = call_function(G, on_rejected.obj_nodes,
                    args=[rejected_with], caller_ast=caller_ast)
                G.set_node_attr(new_promise, ('rejected_with', result))
                flag = True
            # if flag: # the promise is neither fulfilled or rejected
            #     G.microtask_queue.remove(self)
    G.microtask_queue.append(check_promise_status)
    return NodeHandleResult(obj_nodes=[new_promise], used_objs=old_promises)

def promise_p_catch(G: Graph, caller_ast, extra, this, on_rejected=NodeHandleResult()):
    new_promise = G.add_obj_node(caller_ast, None, None)
    old_promises = this.obj_nodes
    def check_promise_status(self, G):
        nonlocal old_promises, on_rejected, extra
        for promise in old_promises:
            flag = False
            fulfilled_with = G.get_node_attr(promise).get('fulfilled_with')
            if fulfilled_with is not None: # the promise is possibly fulfilled
                G.set_node_attr(new_promise, ('fulfilled_with', fulfilled_with))
                flag = True
            rejected_with = G.get_node_attr(promise).get('rejected_with')
            if rejected_with is not None: # the promise is possibly rejected
                result, _ = call_function(G, on_rejected.obj_nodes,
                    args=[rejected_with], caller_ast=caller_ast)
                G.set_node_attr(new_promise, ('rejected_with', result))
                flag = True
            # if flag: # the promise is neither fulfilled or rejected
            #     G.microtask_queue.remove(self)
    G.microtask_queue.append(check_promise_status)
    return NodeHandleResult(obj_nodes=[new_promise], used_objs=old_promises)


def promise_p_finally(G: Graph, caller_ast, extra, this, on_finally=NodeHandleResult()):
    return promise_p_then(G, caller_ast, extra, this, on_finally, on_finally)


def promise_resolve(G: Graph, caller_ast, extra, this, value=NodeHandleResult()):
    promise = G.add_obj_node(caller_ast, None, None)
    G.set_node_attr(promise, ('executors', []))
    G.add_obj_as_prop('__proto__', parent_obj=promise, tobe_added_obj=G.promise_prototype)
    G.add_obj_as_prop('constructor', parent_obj=promise, tobe_added_obj=G.promise_cons)
    G.set_node_attr(promise, ('fulfilled_with', value))
    return NodeHandleResult(obj_nodes=[promise], used_objs=to_obj_nodes(G, value, caller_ast))
