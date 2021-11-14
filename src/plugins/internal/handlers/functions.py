from src.core.logger import *
from src.core.graph import Graph
from src.core.utils import BranchTagContainer 
from src.core.utils import NodeHandleResult, ExtraInfo
from src.core.esprima import esprima_search, esprima_parse
from src.core.checker import traceback, vul_checking
from src.core.garbage_collection import cleanup_scope
from src.core.options import options
from func_timeout import func_timeout, FunctionTimedOut
import time
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

class HandleASTCall(Handler):

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

    # typeof and detele
    if G.get_node_attr(ast_node).get('flags:string[]') == 'JS_TYPEOF':
        types = defaultdict(lambda: [])
        if handled_args:
            for obj in handled_args[0].obj_nodes:
                if G.get_node_attr(obj).get('type') == 'array':
                    types['object'].append(obj)
                # should we consider wildcard objects' type as 
                # wildcard or fixed "object"?
                elif (G.get_node_attr(obj).get('type') == 'object' and
                    G.get_node_attr(obj).get('code') == wildcard):
                    # types[wildcard].append(obj)
                    types['object'].append(obj)
                    types['string'].append(obj)
                    types['number'].append(obj)
                    types['boolean'].append(obj)
                else:
                    types[G.get_node_attr(obj).get('type')].append(obj)
            for i, val in enumerate(handled_args[0].values):
                if type(val) in ['int', 'float']:
                    types['number'].extend(handled_args[0].value_sources[i])
                elif type(val) == 'str':
                    types['string'].extend(handled_args[0].value_sources[i])
                else:
                    types['object'].extend(handled_args[0].value_sources[i])
        # returned_objs = []
        # used_objs = []
        returned_values = []
        returned_value_sources = []
        for t, sources in types.items():
            # added_obj = G.add_obj_node(ast_node, 'string', t)
            # for s in sources:
            #     add_contributes_to(G, [s], added_obj)
            # returned_objs.append(added_obj)
            # used_objs.extend(sources)
            returned_values.append(t)
            returned_value_sources.append(sources)
        return NodeHandleResult(values=returned_values, 
                                value_sources=returned_value_sources)
    elif G.get_node_attr(ast_node).get('flags:string[]') == 'JS_DELETE':
        if handled_args:
            for name_node in handled_args[0].name_nodes:
                for obj in handled_args[0].obj_nodes:
                    G.remove_all_edges_between(name_node, obj)
        return NodeHandleResult()

    # find function declaration objects
    func_decl_objs = list(filter(lambda x: x != G.undefined_obj and
        x != G.null_obj, handled_callee.obj_nodes))
    func_name = handled_callee.name
    # add blank functions
    if not func_decl_objs:
        if handled_callee.name_nodes:
            for name_node in handled_callee.name_nodes:
                func_decl_obj = G.add_blank_func_with_og_nodes(
                    func_name or '{anonymous}')
                G.add_obj_to_name_node(name_node, tobe_added_obj=func_decl_obj)
                func_decl_objs.append(func_decl_obj)
        else:
            loggers.error_logger.error(f'Function call error: Name node not found for {func_name}!')

    
    is_new = False # if the function call is creating a new object
    if G.get_node_attr(ast_node).get('type') == 'AST_CALL':
        stmt_id = 'Call' + ast_node + '-' + get_random_hex()
    elif G.get_node_attr(ast_node).get('type') == 'AST_METHOD_CALL':
        stmt_id = 'Call' + ast_node + '-' + get_random_hex()
        parent = G.get_ordered_ast_child_nodes(ast_node)[0]
    elif G.get_node_attr(ast_node).get('type') == 'AST_NEW':
        stmt_id = 'New' + ast_node + '-' + get_random_hex()
        is_new = True
    returned_result, created_objs = \
        call_function(G, func_decl_objs, handled_args,
        handled_parent, extra, caller_ast=ast_node, is_new=is_new,
        stmt_id=stmt_id, func_name=func_name)
    if is_new:
        returned_result.obj_nodes = created_objs
    return returned_result


def simurun_function(G, func_ast, branches=None, block_scope=True,
    caller_ast=None):
    """
    Simurun a function by running its body.
    """
    if branches is None or G.single_branch:
        # create an instance of BranchTagContainer every time,
        # don't use default argument
        branches = BranchTagContainer()

    if caller_ast is not None:
        if G.call_counter[caller_ast] >= G.call_limit:
            loggers.main_logger.warning(f'{caller_ast}: Function {func_ast} in call stack '
                    f'{G.call_counter[caller_ast]} times, skip simulating')
            return None, None # don't change this to [], []
                              # we need to distinguish skipped functions
        else:
            G.call_counter[caller_ast] += 1

    func_objs = G.get_func_decl_objs_by_ast_node(func_ast)
    func_obj = func_objs[0] if func_objs else '?'
    func_name = G.get_node_attr(func_obj).get('name') if func_objs else '?'
    loggers.main_logger.info(sty.ef.inverse + sty.fg.green +
        "FUNCTION {} {} STARTS, SCOPE {}, DECL OBJ {}, this OBJs {}, branches {}"
        .format(func_ast, func_name or '{anonymous}',
        G.cur_scope, func_obj, G.cur_objs,
        branches) + sty.rs.all)
    returned_objs, used_objs = [], []
    # update graph register for cur_func
    G.cur_func = G.get_cur_function_decl()

    for child in G.get_child_nodes(func_ast, child_type='AST_STMT_LIST'):
        returned_objs, used_objs = simurun_block(G, child,
            parent_scope=G.cur_scope, branches=branches,
            block_scope=block_scope, decl_var=True)
        break

    if caller_ast is not None:
        G.call_counter[caller_ast] -= 1
    return returned_objs, used_objs

def get_module_exports(G, file_path):
    toplevel_nodes = G.get_nodes_by_type_and_flag(
        'AST_TOPLEVEL', 'TOPLEVEL_FILE')
    found = False
    for node in toplevel_nodes:
        if G.get_node_attr(node).get('name') == file_path:
            found = True
            # if a file has been required, skip the run and return
            # the saved module.exports
            saved_module_exports = G.get_node_attr(node).get('module_exports')
            if saved_module_exports != None:
                module_exports_objs = saved_module_exports
                loggers.main_logger.log(ATTENTION, 'File has been required, '
                    'return saved module.exports {} for {}'
                    .format(module_exports_objs, file_path))
                break
            else:
                module_exports_objs = file.run_toplevel_file(G, node)
                G.set_node_attr(node,
                    ('module_exports', module_exports_objs))
                break
    if found:
        return module_exports_objs
    else:
        return []

def handle_require(G: Graph, caller_ast, extra, _, module_names):
    logger = loggers.main_logger
    # handle module name
    module_names, src, _ = to_values(G, module_names, caller_ast)
    if not module_names: return NodeHandleResult(obj_nodes=[])

    returned_objs = set()
    for module_name in module_names:
        if False and module_name in modeled_builtin_modules.modeled_modules \
            and G.vul_type != "path_traversal":
            # for some reason, docker seems will run the if statement
            # even the vul type is path traversal
            # disable the built in for fs
            # Python-modeled built-in modules
            # for now mostly fs
            # if it's path_traversal, do not do this
            returned_objs.add(
                modeled_builtin_modules.get_module(G, module_name))
        else:
            # actual JS modules
            # static require (module name is a literal)
            # module's path is in 'name' field
            file_path = G.get_node_attr(caller_ast).get('name')
            module_exports_objs = []
            if module_name and file_path:
                module_exports_objs = \
                    get_module_exports(G, file_path)
            # dynamic require (module name is a variable)
            loggers.main_logger.info('Trying to require package {}.'\
                    .format(module_name))
            if module_name is None or module_name == wildcard:
                logger.error('{} trying to require unknown package.'
                    .format(caller_ast))
                continue
            if not module_exports_objs:
                # check if the file's AST is in the graph
                file_path, _ = \
                    esprima_search(module_name, G.get_cur_file_path(),
                        print_func=logger.info)
                if not file_path: # module not found
                    continue
                elif file_path == 'built-in': # unmodeled built-in module
                    continue
                else:
                    module_exports_objs = \
                        get_module_exports(G, file_path)
            if not module_exports_objs:
                # if the file's AST is not in the graph,
                # generate its AST and run it
                logger.log(ATTENTION, f'Generating AST on demand for module '
                    f'{module_name} at {file_path}...')

                # following code is copied from analyze_files,
                # consider combining in future.
                start_id = str(G.cur_id)
                result = esprima_parse(file_path, ['-n', start_id, '-o', '-'],
                    print_func=logger.info)
                G.import_from_string(result)
                # start from the AST_TOPLEVEL node instead of the File node
                module_exports_objs = \
                        file.run_toplevel_file(G, str(int(start_id) + 1))
                G.set_node_attr(start_id,
                    ('module_exports', module_exports_objs))
            if module_exports_objs:
                returned_objs.update(module_exports_objs)
            else:
                logger.error("Required module {} at {} not found!".format(
                    module_name, file_path))
        
    returned_objs = list(returned_objs)
    # we also need to check that this is not a built-in
    # if built in, do not run exported functions
    if returned_objs and G.run_all and "/builtin_packages/" not in file_path:
        run_exported_functions(G, returned_objs, extra)

    # for a require call, we need to run traceback immediately
    if G.exit_when_found and G.vul_type not in ['proto_pollution', 'ipt']:
        vul_type = G.vul_type
        res_path = traceback(G, vul_type)
        res_path = vul_checking(G, res_path[0], vul_type)
        if len(res_path) != 0:
            G.detection_res[G.vul_type].add(G.package_name)
            G.finished = True
    return NodeHandleResult(obj_nodes=returned_objs,
                            used_objs=list(chain(*src)))

def instantiate_obj(G, exp_ast_node, constructor_decl, branches=None):
    '''
    Instantiate an object (create a new object).
    
    Args:
        G (Graph): Graph.
        exp_ast_node: The New expression's AST node.
        constructor_decl: The constructor's function declaration AST
            node.
        branches (optional): Branch information.. Defaults to [].
    
    Returns:
        obj_node: The created object. Note that this function returns a
            single object (not an array of objects).
        returned_obj: list, The return object of the function
    '''
    # create the instantiated object
    # js_type=None: avoid automatically adding prototype
    created_obj = G.add_obj_node(ast_node=exp_ast_node, js_type=None)
    # add edge between obj and obj decl
    G.add_edge(created_obj, constructor_decl, {"type:TYPE": "OBJ_DECL"})
    # build the prototype chain
    G.build_proto(created_obj)

    # update current object (this)
    backup_objs = G.cur_objs
    G.cur_objs = [created_obj]

    returned_objs, _ = simurun_function(G, constructor_decl, branches=branches,
        caller_ast=exp_ast_node)

    G.cur_objs = backup_objs

    # finally add call edge from caller to callee
    # added in call_function, no need to add here
    # if exp_ast_node is not None:
    #     G.add_edge_if_not_exist(exp_ast_node, constructor_decl,
    #                             {"type:TYPE": "CALLS"})

    return created_obj, returned_objs

def evaluate_func(func_obj):
    """
    evalute the function for faster run

    """
    # print("evalute function", func_obj)

def run_exported_functions(G, module_exports_objs, extra):
    if G.no_file_based and len(G.file_stack) > 1: # ignore file-based
        return
    if options.no_exports:
        return 

    exported_objs = list(module_exports_objs)
    # object names (or expressions to get the objects)
    exported_obj_names = ['module.exports'] * len(exported_objs)
    # Roots are the first functions that needs to be call to reach the
    # current function, used to build control flow paths from it to the
    # source function that can reach the sink function.
    roots = [None] * len(exported_objs)
    # EXIT nodes of the previous function in CF paths described above
    prev_exit_nodes = [None] * len(exported_objs)

    tried = set(exported_objs) # objects that have been tried

    def _find_props(parent_obj, parent_obj_name):
        '''
        Find properties under an object.
        '''
        nonlocal G, tried
        proto_objs = \
            G.get_prop_obj_nodes(parent_obj=parent_obj, prop_name='__proto__')
        result_objs = []
        result_obj_names = []
        for name_node in G.get_prop_name_nodes(parent_obj):
            name = G.get_node_attr(name_node).get('name') or '?'
            if name in ['__proto__', 'prototype', 'constructor']: continue
            obj_nodes = G.get_obj_nodes(name_node)
            for obj in obj_nodes:
                if obj in tried: continue
                result_objs.append(obj)
                result_obj_names.append(f'{parent_obj_name}.{name}')
        for proto_obj in proto_objs:
            if proto_obj not in G.builtin_prototypes:
                for name_node in G.get_prop_name_nodes(proto_obj):
                    name = G.get_node_attr(name_node).get('name') or '?'
                    if name in ['__proto__', 'prototype', 'constructor']:
                        continue
                    obj_nodes = G.get_obj_nodes(name_node)
                    for obj in obj_nodes:
                        if obj in tried: continue
                        result_objs.append((parent_obj, obj))
                        # result_obj_names.append(f'{cur_obj_name}.{name}')
                        result_obj_names.append(
                            f'{parent_obj_name}.__proto__.{name}')
            # Promises
            if proto_obj == G.promise_prototype:
                executors = G.get_node_attr(parent_obj).get('executors')
                if executors:
                    for executor in executors:
                        if executor in tried: continue
                        result_objs.append((parent_obj, executor))
                        result_obj_names.append(
                            f'{parent_obj_name}.then()')
        return result_objs, result_obj_names

    while(len(exported_objs) != 0): # BFS
        obj = exported_objs.pop(0) # head object

        # if an exported module is executed, add it to the total number of statements
        cur_func_ast = G.get_obj_def_ast_node(obj, aim_type='function')
        G.add_excuted_module_to_statements(cur_func_ast)

        cur_obj_name = exported_obj_names.pop(0) # head object name
        prev_exit_node = prev_exit_nodes.pop(0) # previous EXIT node of head
        cur_root = roots.pop(0) # root of head
        parent_obj = None
        if type(obj) == type((1,2)): # if head is a tuple, extract parent obj
            parent_obj = obj[0]
            obj = obj[1]

        # ignore built-in functions
        if 'pythonfunc' in G.get_node_attr(obj):
            continue
        # limit entry function by name (if set by command line arguments)
        if G.func_entry_point is not None and not (
            G.get_node_attr(obj).get('type') == 'function' and (
            G.get_node_attr(obj).get('name') == G.func_entry_point
            or cur_obj_name == G.func_entry_point)):
            continue

        _objs, _names = _find_props(obj, cur_obj_name)
        exported_objs.extend(_objs)
        exported_obj_names.extend(_names)
        prev_exit_nodes.extend([prev_exit_node] * len(_objs))
        roots.extend([cur_root] * len(_objs))
        tried.update(_objs)

        # save current IPT & PP sets before running the function
        #old_ipt_use = set(G.ipt_use)
        # ↓ not used becase now we use offline detection
        # old_pp = set(G.proto_pollution)

        if obj in G.require_obj_stack:
            continue
        G.require_obj_stack.append(obj)
        newed_objs = None
        newed_obj_names = None
        if G.get_node_attr(obj).get("init_run") is not None:
            continue
        if G.get_node_attr(obj).get('type') != 'function':
            continue
        loggers.main_logger.info('Run exported function {} {}'.format(obj, cur_obj_name))
        G.cur_source_name = cur_obj_name
        # func_timeout may cause threading problems
        G.time_limit_reached = False
        G.func_start_time = time.time()
        returned_result = None
        # G.cur_fake_args = set() # don't clear the fake arg set
        if parent_obj is None:
            # if the function is not a method, try it as a constructor
            # (both instantiated object and return values will be returned)
            if options.exported_func_timeout is not None:
                try:
                    returned_result, newed_objs = func_timeout(
                            options.exported_func_timeout, 
                            call_function,
                            args=(G, [obj], [], NodeHandleResult, 
                                extra, None, True, "Unknown", 
                                None, True, None))
                except FunctionTimedOut as err:
                    print(err)
            else:
                returned_result, newed_objs = call_function(G, [obj],
                    extra=extra, is_new=True, mark_fake_args=True)

        else:
            # if the function is a method, run it with "this" set to its
            # parent object
            if options.exported_func_timeout is not None:
                try:
                    with timeout(seconds=options.exported_func_timeout, error_message="exported func timeout"):
                        returned_result, newed_objs = call_function(G, [obj],
                            this=NodeHandleResult(obj_nodes=[parent_obj]),
                            extra=extra, mark_fake_args=True)
                except TimeoutError as err:
                    print(err)
            else:
                returned_result, newed_objs = call_function(G, [obj],
                    this=NodeHandleResult(obj_nodes=[parent_obj]),
                    extra=extra, mark_fake_args=True)
        G.set_node_attr(obj, ('init_run', "True"))

        # bound functions (bind)
        target_func = G.get_node_attr(obj).get('target_func')
        if target_func is not None:
            obj = target_func

        cur_func_ast = G.get_obj_def_ast_node(obj, aim_type='function')
        cur_entry_node = G.get_successors(cur_func_ast, edge_type='ENTRY')[0]
        cur_exit_node = G.get_successors(cur_func_ast, edge_type='EXIT')[0]
        if prev_exit_node is not None:
            G.add_edge_if_not_exist(
                prev_exit_node, cur_entry_node, {"type:TYPE": "FLOWS_TO"})

        # include instantiated objects
        if newed_objs is None:
            newed_objs = [obj]
            newed_obj_names = [cur_obj_name]
        else:
            newed_obj_names = [f'(new {cur_obj_name}())'] * len(newed_objs)
        exported_objs.extend(newed_objs)
        exported_obj_names.extend(newed_obj_names)
        prev_exit_nodes.extend([cur_exit_node] * len(newed_objs))
        roots.extend([cur_root or cur_func_ast] * len(newed_objs))

        # also include returned objects
        if returned_result is not None:
            exported_objs.extend(returned_result.obj_nodes)
            exported_obj_names.extend(
                [f'{cur_obj_name}()'] * len(returned_result.obj_nodes))
            prev_exit_nodes.extend(
                [cur_exit_node] * len(returned_result.obj_nodes))
            roots.extend(
                [cur_root or cur_func_ast] * len(returned_result.obj_nodes))

        # prepare some strings for vulnerability log
        func_ast = G.get_obj_def_ast_node(obj, aim_type='function')
        param_list = G.get_child_nodes(func_ast, edge_type='PARENT_OF',
            child_type='AST_PARAM_LIST')
        params = G.get_ordered_ast_child_nodes(param_list)
        arg_names = filter(lambda x: x is not None,
            (G.get_name_from_child(param) for param in params))
        args = ','.join(arg_names)

        # detect vulnerabilities
        vul_type = G.vul_type

        if G.exit_when_found and vul_type not in ['proto_pollution', 'ipt']:
            res_path = traceback(G, vul_type)
            res_path = vul_checking(G, res_path[0], vul_type)
            if len(res_path) != 0:
                with open('vul_func_names.csv', 'a') as fp:
                    loggers.main_logger.info(f'{vul_type} successfully found in '
                               f'{G.entry_file_path} at {cur_obj_name}({args})')
                    fp.write(f'{vul_type},"{G.entry_file_path}","{cur_obj_name}","{args}"\n')
                # G.success_detect = True
                G.detection_res[G.vul_type].add(G.package_name)
                if G.exit_when_found and G.detection_res[G.vul_type]:
                    G.finished = True
                    break

        if G.check_ipt:
            if G.ipt_use:# - old_ipt_use: # if there are new results
                with open('vul_func_names.csv', 'a') as fp:
                    loggers.main_logger.log(ATTENTION, f'int_prop_tampering found in {G.entry_file_path} at {cur_obj_name}({args})')
                    fp.write(f'int_prop_tampering,"{G.entry_file_path}","{cur_obj_name}","{args}"\n')
                # G.success_detect = True
                G.detection_res[G.vul_type].add(G.package_name)
                if G.exit_when_found and G.detection_res[G.vul_type]:
                    G.finished = True
                    break


def call_function(G, func_objs, args=[], this=NodeHandleResult(), extra=None,
    caller_ast=None, is_new=False, stmt_id='Unknown', func_name=None,
    mark_fake_args=False, python_callback=None):
    '''
    Directly call a function.
    
    Args:
        G (Graph): Graph.
        func_objs: List of function declaration objects.
        args (List[NodeHandleResult]): List of handled arguments.
        this (NodeHandleResult): Handled override "this" object.
        extra (ExtraInfo, optional): Extra information. Defaults to
            empty ExtraInfo.
        caller_ast (optional): The caller's AST node. Defaults to None.
        is_new (bool, optional): If the caller is a "new" statement.
            Defaults to False.
        stmt_id (str, optional): Caller's statement ID, for branching
            use only. Defaults to 'Unknown'.
        func_name (str, optional): The function's name, for adding blank
            functions only. Defaults to '{anonymous}'.
    
    Returns:
        NodeHandleResult, List: Call result (including returned objects
            and used objects), and list of created objects.
    '''

    if G.finished:
        return NodeHandleResult(), []

    logger = loggers.main_logger
    func_return_handle_res = None

    # No function objects found, return immediately
    if not func_objs:
        logger.error(f'No definition found for function {func_name}')
        return NodeHandleResult(), []

    if extra is None:
        extra = ExtraInfo()

    # process arguments
    callback_functions = set() # only for unmodeled built-in functions
    for arg in args:
        # add callback functions
        for obj in arg.obj_nodes:
            if G.get_node_attr(obj).get('type') == 'function':
                callback_functions.add(obj)
    callback_functions = list(callback_functions)


    # if the function declaration has multiple possibilities,
    # and need to merge afterwards
    has_branches = (len(func_objs) > 1 and not G.single_branch)

    # process function name
    if not func_name:
        if func_objs:
            func_name = G.get_node_attr(func_objs[0]).get('name')
    if not func_name:
        func_name = '{anonymous}'

    skip_func_list = []
    if options.skip_func is not None:
        skip_func_list = options.skip_func.split(',')
    if func_name in skip_func_list:
        return NodeHandleResult(), []

    call_stack_item = '{}'.format(func_name)
    if G.call_stack.count(call_stack_item) > 20:
        return NodeHandleResult(), []

    #print(G.call_stack)
    if options.max_rep is not None:
        for c in G.call_stack:
            if G.call_stack.count(c) > int(options.max_rep):
                return NodeHandleResult(), []

    G.call_stack.append(call_stack_item)
    #print(G.call_stack)

    if stmt_id == 'Unknown' and caller_ast is not None:
        stmt_id = caller_ast

    # initiate return values
    returned_objs = set()
    used_objs = set()
    created_objs = []
    returned_values = [] # for python function only
    returned_value_sources = [] # for python function only
    exit_nodes = set() # build control flows

    # initiate fake return objects (only create once)
    fake_returned_obj = None
    fake_created_obj = None

    # if any function is run in this call
    any_func_run = False
    # if any function is skipped in this call
    any_func_skipped = False
    
    # manage branches
    branches = extra.branches
    parent_branch = branches.get_last_choice_tag()

    # for each possible function declaration
    for i, func_obj in enumerate(func_objs):
        # copy "this" and "args" references
        # because we may edit them later
        # and we want to keep original "this" and "args"
        _this = this
        _args = list(args) if args is not None else None
        # bound functions (bind)
        func_obj_attrs = G.get_node_attr(func_obj)
        if func_obj_attrs.get('target_func'):
            _this = func_obj_attrs.get('bound_this')
            logger.log(ATTENTION, 'Bound function found ({}->{}), this={}'.format(func_obj_attrs.get('target_func'), func_obj, _this.obj_nodes))
            if func_obj_attrs.get('bound_args') is not None:
                _args = func_obj_attrs.get('bound_args')
            func_obj = func_obj_attrs.get('target_func')
        if not _this and func_obj_attrs.get('parent_scope_this'):
            _this = NodeHandleResult(
                obj_nodes=func_obj_attrs.get('parent_scope_this'))
        
        # pass arguments' used objects to the function call
        # for arg in _args:
        #     used_objs.update(arg.used_objs)

        if func_obj in G.internal_objs.values():
            logger.warning('Error: Trying to run an internal obj {} {}'
                ', skipped'.format(func_obj, G.inv_internal_objs[func_obj]))
            continue
        any_func_run = True

        # if branches exist, add a new branch tag to the list
        if has_branches and not G.single_branch:
            next_branches = branches+[BranchTag(point=stmt_id, branch=i)]
        else:
            next_branches = branches

        branch_returned_objs = []
        branch_created_obj = None
        branch_used_objs = []
        func_ast = G.get_obj_def_ast_node(func_obj, aim_type='function')
        # check if python function exists
        python_func = G.get_node_attr(func_obj).get('pythonfunc')
        if python_func: # special Python function
            if is_new:
                if func_obj in G.builtin_constructors:
                    logger.log(ATTENTION, f'Running Python function {func_obj} {python_func}...')
                    try:
                        h = python_func(G, caller_ast, ExtraInfo(extra,
                            branches=next_branches), _this, *_args)
                        created_objs.extend(h.obj_nodes)
                        branch_used_objs = h.used_objs
                    except TypeError as e:
                        logger.error(tb.format_exc())
                else:
                    logger.error(f'Error: try to new Python function {func_obj} {python_func}...')
                    continue
            else:
                logger.log(ATTENTION, f'Running Python function {func_obj} {python_func}...')
                try:
                    logger.info(_args)
                    h = python_func(G, caller_ast,
                        ExtraInfo(extra, branches=next_branches), _this, *_args)
                    branch_returned_objs = h.obj_nodes
                    # the obj_nodes may be node list
                    if type(branch_returned_objs) != list:
                        branch_returned_objs = [branch_returned_objs]
                    branch_used_objs = h.used_objs
                    returned_values.extend(h.values)
                    returned_value_sources.extend(h.value_sources)
                except TypeError as e:
                    logger.error(tb.format_exc())
        else: # JS function in AST
            # if AST cannot be found, create AST
            if func_ast is None or G.get_node_attr(func_ast).get('type') \
            not in ['AST_FUNC_DECL', 'AST_CLOSURE', 'AST_METHOD']:
                G.add_blank_func_with_og_nodes(func_name, func_obj)
                func_ast = G.get_obj_def_ast_node(func_obj, aim_type='function')
            # add to coverage
            func_ast_attr = G.get_node_attr(func_ast)
            if 'labels:label' in func_ast_attr and \
                    func_ast_attr['labels:label'] == 'Artificial_AST':
                pass
            else:
                G.covered_func.add(func_ast)

            # add function scope (see comments in decl_function)
            parent_scope = G.get_node_attr(func_obj).get('parent_scope')
            func_scope = G.add_scope('FUNC_SCOPE', func_ast,
                f'Function{func_ast}:{caller_ast}', func_obj,
                caller_ast, func_name, parent_scope=parent_scope)
            # make arguments available in the function
            param_list = G.get_child_nodes(func_ast, edge_type='PARENT_OF',
                child_type='AST_PARAM_LIST')
            params = G.get_ordered_ast_child_nodes(param_list)
            # add "arguments" array
            arguments_obj = G.add_obj_to_scope(name='arguments',
                    js_type='array', scope=func_scope, ast_node=func_ast)
            j = 0
            while j < len(params) or j < len(_args) or j < 3:
                if j < len(_args):
                    arg_obj_nodes = to_obj_nodes(G, _args[j], caller_ast)
                    # add argument to "arguments"
                    for obj in arg_obj_nodes:
                        G.add_obj_as_prop(prop_name=str(j),
                            parent_obj=arguments_obj, tobe_added_obj=obj)
                    # add argument to the parameter
                    if j < len(params):
                        param = params[j]
                        param_name = G.get_name_from_child(param)
                        if G.get_node_attr(param).get('flags:string[]') \
                            == 'PARAM_VARIADIC':
                            arr = G.add_obj_to_scope(param_name,
                                caller_ast or param, 'array', scope=func_scope)
                            length = 0
                            while j < len(_args):
                                logger.debug(f'add arg {param_name}[{length}]'
                                    f' <- {arg_obj_nodes}, scope {func_scope}')
                                for obj in arg_obj_nodes:
                                    G.add_obj_as_prop(str(length),
                                        parent_obj=arr, tobe_added_obj=obj)
                                j += 1
                                length += 1
                            G.add_obj_as_prop('length', js_type='number',
                                value=length, parent_obj=arr)
                        else:
                            logger.debug(f'add arg {param_name} <- '
                                f'{arg_obj_nodes}, scope {func_scope}')
                            for obj in arg_obj_nodes:
                                G.add_obj_to_scope(name=param_name,
                                    scope=func_scope, tobe_added_obj=obj)
                    else:
                        # this is used to print logs only
                        logger.debug(f'add arg arguments[{j}] <- '
                            f'{arg_obj_nodes}, scope {func_scope}')
                elif j < len(params) and mark_fake_args:
                    param = params[j]
                    param_name = G.get_name_from_child(param)
                    # add dummy arguments
                    param_name = G.get_name_from_child(param)
                    if G.get_node_attr(param).get('flags:string[]') \
                        == 'PARAM_VARIADIC':
                        # rest parameter (variable length arguments)
                        added_obj = G.add_obj_to_scope(name=param_name,
                            scope=func_scope, ast_node=caller_ast or param,
                            js_type='array')
                        elem = G.add_obj_as_prop(wildcard, caller_ast or param,
                            value=wildcard, parent_obj=added_obj)
                        if mark_fake_args:
                            G.set_node_attr(elem, ('tainted', True))
                            G.set_node_attr(elem, ('fake_arg', True))
                            logger.debug("{} marked as tainted [2]".format(elem))
                    else:
                        added_obj = G.add_obj_to_scope(name=param_name,
                            scope=func_scope, ast_node=caller_ast or param,
                            # give __proto__ when checking prototype pollution
                            js_type='object' if G.check_proto_pollution
                            else None, value=wildcard)
                    if mark_fake_args:
                        G.set_node_attr(added_obj, ('tainted', True))
                        G.set_node_attr(added_obj, ('fake_arg', True))
                        logger.debug("{} marked as tainted [3]".format(added_obj))
                    G.add_obj_as_prop(prop_name=str(j),
                        parent_obj=arguments_obj, tobe_added_obj=added_obj)

                    logger.debug(f'add arg {param_name} <- new obj {added_obj}, '
                            f'scope {func_scope}, ast node {param}')
                elif j < 3:
                    # in case the function only use "arguments"
                    # but no parameters in its declaration
                    added_obj = G.add_obj_node(ast_node=caller_ast,
                        # give __proto__ when checking prototype pollution
                        js_type='object' if G.check_proto_pollution
                        else None, value=wildcard)
                    if mark_fake_args:
                        G.set_node_attr(added_obj, ('tainted', True))
                        G.set_node_attr(added_obj, ('fake_arg', True))
                        logger.debug("{} marked as tainted [4]".format(added_obj))
                    G.add_obj_as_prop(prop_name=str(j),
                        parent_obj=arguments_obj, tobe_added_obj=added_obj)
                    logger.debug(f'add arguments[{j}] <- new obj {added_obj}, '
                                f'scope {func_scope}, ast node {caller_ast}')
                else:
                    break
                j += 1
            arguments_length_obj = G.add_obj_as_prop(prop_name='length',
                 parent_obj=arguments_obj, value=j, js_type='number')

            # if the function is defined in a for loop, restore the branches
            # this design is obsolete
            # for_tags = \
            #     BranchTagContainer(G.get_node_attr(func_obj).get('for_tags',
            #     BranchTagContainer())).get_creating_for_tags()
            # if for_tags:
            #     for_tags = [BranchTag(i, mark=None) for i in for_tags]
            #     next_branches.extend(for_tags)
            # logger.debug(f'next branch tags: {next_branches}')

            # switch scopes ("new" will swtich scopes and object by itself)
            backup_scope = G.cur_scope
            G.cur_scope = func_scope
            backup_stmt = G.cur_stmt
            # call the Python callback function
            if python_callback is not None:
                python_callback(G)
            # run simulation -- create the object, or call the function
            if is_new:
                branch_created_obj, branch_returned_objs = instantiate_obj(G,
                    caller_ast, func_ast, branches=next_branches)
            else:
                backup_objs = G.cur_objs
                if _this:
                    G.cur_objs = _this.obj_nodes
                else:
                    G.cur_objs = [G.BASE_OBJ]
                branch_returned_objs, branch_used_objs = simurun_function(
                    G, func_ast, branches=next_branches, caller_ast=caller_ast)
                
                G.cur_objs = backup_objs
            
            func_return_handle_res = G.function_returns[G.find_ancestor_scope()][0]
            # switch back scopes
            G.cur_scope = backup_scope
            G.cur_stmt = backup_stmt

            # delete "arguments" (avoid parent explosion)
            for name_node in G.get_prop_name_nodes(arguments_obj):
                for obj_node in G.get_child_nodes(name_node, edge_type='NAME_TO_OBJ'):
                    G.remove_all_edges_between(name_node, obj_node)
                G.remove_all_edges_between(arguments_obj, name_node)

            # if it's an unmodeled built-in function
            if G.get_node_attr(func_ast).get('labels:label') \
                == 'Artificial_AST':
                # logger.info(sty.fg.green + sty.ef.inverse + func_ast + ' is unmodeled built-in function.' + sty.rs.all)
                if branch_used_objs is None: # in case it's skipped
                    branch_used_objs = []
                if branch_returned_objs is None: # in case it's skipped
                    branch_returned_objs = []
                # add arguments as used objects
                for h in _args:
                    branch_used_objs.extend(h.obj_nodes)
                if this is not None:
                    # performance is too low
                    # for o in G.get_ancestors_in(func_obj, edge_types=[
                    #     'NAME_TO_OBJ', 'OBJ_TO_PROP'],
                    #     candidates=this.obj_nodes, step=2):
                    #     branch_used_objs.append(o)
                    branch_used_objs.extend(this.obj_nodes)
                # add a blank object as return object
                if fake_returned_obj is None:
                    fake_returned_obj = \
                        G.add_obj_node(caller_ast, "object", wildcard)
                branch_returned_objs.append(fake_returned_obj)
                for obj in branch_used_objs:
                    add_contributes_to(G, [obj], fake_returned_obj)
                # add a blank object as created object
                if is_new and branch_created_obj is None:
                    if fake_created_obj is None:
                        fake_created_obj = \
                            G.add_obj_node(caller_ast, "object", wildcard)
                    branch_created_obj = fake_created_obj
                    for obj in branch_used_objs:
                        add_contributes_to(G, [obj], fake_created_obj)

                # call all callback functions
                if callback_functions:
                    logger.debug(sty.fg.green + sty.ef.inverse +
                        'callback functions = {}'.format(callback_functions)
                        + sty.rs.all)
                    
                    if _this is not None:
                        obj_attrs = [G.get_node_attr(obj) for obj in _this.obj_nodes]
                        mark_fake_args = any(['tainted' in attr for attr in obj_attrs])
                    else:
                        mark_fake_args = False

                    if len(callback_functions) != 0:
                        # if the name is OPGen_markTaintCall, mark the args as tainted
                        if "OPGen_markTaintCall" == func_name:
                            mark_fake_args = True

                    call_function(G, callback_functions, caller_ast=caller_ast,
                        extra=extra, stmt_id=stmt_id, mark_fake_args=mark_fake_args)
        
        if branch_returned_objs is None or branch_used_objs is None: # workaround for skipping instantiating objects
            any_func_skipped = True
        else:
            assert type(branch_returned_objs) is list
            assert type(branch_used_objs) is list
            returned_objs.update(branch_returned_objs)
            used_objs.update(branch_used_objs)
        assert type(branch_created_obj) is not list
        if branch_created_obj is not None:
            created_objs.append(branch_created_obj)

        # add control flows
        if caller_ast is not None and func_ast is not None and \
                G.get_node_attr(func_ast).get('type') in [
                                'AST_FUNC_DECL', 'AST_CLOSURE', 'AST_METHOD']:
            caller_cpg = G.find_nearest_upper_CPG_node(caller_ast)
            logger.info(sty.fg.li_magenta + sty.ef.inverse + "CALLS" + 
                sty.rs.all + " {} -> {} (Line {} -> Line {}) {}".format(
                    caller_cpg, func_ast,
                    G.get_node_attr(caller_cpg).get('lineno:int'),
                    G.get_node_attr(func_ast).get('lineno:int') or '?',
                    func_name))
            # add a call edge from the expression to the function definition
            # G.add_edge_if_not_exist(
            #     caller_ast, func_ast, {"type:TYPE": "CALLS"})
            # add a call edge from the calling function to the callee
            # (called function)
            G.add_edge_if_not_exist(
                find_function(G, caller_ast), func_ast, {"type:TYPE": "CALLS"})
            # then add a control flow edge from the statement to the
            # function's ENTRY node
            entry_node = G.get_successors(func_ast, edge_type='ENTRY')[0]
            G.add_edge_if_not_exist(
                caller_cpg, entry_node, {"type:TYPE": "FLOWS_TO"})
            # collect exit nodes
            exit_node = G.get_successors(func_ast, edge_type='EXIT')[0]
            exit_nodes.add(exit_node)

    if has_branches and not G.single_branch and any_func_run:
        merge(G, stmt_id, len(func_objs), parent_branch)

    if not any_func_run:
        logger.error('Error: No function was run during this function call')

    G.call_stack.pop()
    # print(len(G.call_stack), G.call_stack)

    # G.last_stmts = exit_nodes
    if caller_ast is not None:
        caller_cpg = G.find_nearest_upper_CPG_node(caller_ast)
        for exit_node in exit_nodes:
            G.add_edge(exit_node, caller_cpg, {'type:TYPE': 'FLOWS_TO'})
        G.last_stmts = [caller_cpg]
    else:
        G.last_stmts = []
    
    name_tainted = False
    parent_is_proto = False
    if func_return_handle_res is not None:
        for hr in func_return_handle_res:
            name_tainted = name_tainted or hr.name_tainted
            parent_is_proto = parent_is_proto or hr.parent_is_proto

    return NodeHandleResult(obj_nodes=list(returned_objs),
            used_objs=list(used_objs),
            values=returned_values, value_sources=returned_value_sources,
            name_tainted=name_tainted, parent_is_proto=parent_is_proto,
            terminated=any_func_skipped
        ), created_objs

def find_function(G: Graph, ast_node):
    '''
    Find the upper blocks and functions of the caller. Because
    CALLS edges are built between functions (instead of call
    expression or statement), we need to find which functions the call
    expression is in.
    '''        
    node_type = G.get_node_attr(ast_node).get('type')
    if node_type in [
        'AST_FUNC_DECL', 'AST_CLOSURE', 'AST_METHOD', 'AST_TOPLEVEL']:
        return ast_node
    else:
        for e in G.get_in_edges(ast_node, edge_type='PARENT_OF'):
            return find_function(G, e[0])
        for e in G.get_in_edges(ast_node, edge_type='ENTRY'):
            return find_function(G, e[0])
        for e in G.get_in_edges(ast_node, edge_type='EXIT'):
            return find_function(G, e[0])
    return None
