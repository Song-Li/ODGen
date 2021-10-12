from .trace_rule import TraceRule
from .vul_func_lists import Sinks
from .logger import loggers
import sty
from src.core.options import options

def get_path_text(G, path, caller=None):
    """
    get the code by ast number
    Args:
        G: the graph
        path: the path with ast nodes
    Return:
        str: a string with text path
    """
    res_path = ""
    # debug only
    cur_path_str1 = ""
    # real output
    cur_path_str2 = ""
    for node in path:
        if node is None:
            return ""
        cur_node_attr = G.get_node_attr(node)
        file_path = G.get_node_file_path(node)
        # we do not output builtin res
        #if '/builtin_packages/' in file_path:
        #   continue

        content = None
        if cur_node_attr.get('type') != 'object' and cur_node_attr.get('lineno:int') is None:
            continue

        cur_path_str2 += "$FilePath${}\n".format(G.get_node_file_path(node))
        try:
            content = G.get_node_file_content(node)
        except Exception as e:
            print(e)

        if cur_node_attr['type'] == 'object' and len(cur_node_attr['code'].strip()) != 0:
            cur_path_str2 += "{}\n".format(cur_node_attr['code'])
            continue


        cur_path_str1 += cur_node_attr['lineno:int'] + '->'
        start_lineno = int(cur_node_attr['lineno:int'])
        end_lineno = int(cur_node_attr['endlineno:int']
                        or start_lineno)

        if content is not None:
            cur_path_str2 += "Line {}\t{}".format(start_lineno,
                    ''.join(content[start_lineno:end_lineno + 1]))

    if caller is not None and 'lineno:int' in G.get_node_attr(caller):
        cur_path_str1 += G.get_node_attr(caller).get('lineno:int')
    G.logger.debug(cur_path_str1)

    res_path += "==========================\n"
    res_path += cur_path_str2
    return res_path

def get_obj_defs(G, obj_nodes=[]):
    """
    input a list of objs and return a list of def asts
    """
    cur_creater = []
    for node in obj_nodes:
        # for each objects, store the creater of the obj and used obj
        ast_node = G.get_obj_def_ast_node(node)
        cur_creater.append(ast_node)
    return cur_creater

def obj_traceback(G, start_node):
    """
    traceback from the target object node, based on obj level dependency
    Args:
        G: the graph
        start_node: the start object node
    Returns:
        pathes(list): the pathes to the target object
        def pathes(list): AST nodes that defines the objects in the pathes
        text pathes(str): the human-friendly text pathes
    """
    text_path = ""
    ast_pathes = []
    obj_pathes = G._dfs_upper_by_edge_type(source=start_node, edge_type="CONTRIBUTES_TO")

    for obj_p in obj_pathes:
        obj_def = get_obj_defs(G, obj_p)
        ast_pathes.append(obj_def)
        text_path += get_path_text(G, obj_def)
    return obj_pathes, ast_pathes, text_path

def extend_ast_list(G, ast_list):
    """
    extend the def based ast list to a longer version
    1, we find all the uses of the objs by OBJ_REACHES
    2, try to sort the uses by timestamp
    """
    used_ast = []
    ast_tainted_objs = []
    # prepare ast objs flow
    pre_ast = None
    for ast in ast_list:
        if not pre_ast:
            pre_ast = ast
            continue
        edges = G.get_edge_attr(pre_ast, ast)
        for idx in edges:
            edge = edges[idx]
            if 'type:TYPE' in edge and edge['type:TYPE'] == 'OBJ_REACHES':
                ast_tainted_objs.append(edge['obj'])
        pre_ast = ast

    """
    print("ast tainted objs", ast_tainted_objs)
    all_flow_pathes = G.get_all_simple_pathes(ast_list[0], ast_list[-1], edge_type='FLOWS_TO')
    print("all flow pathes", all_flow_pathes)
    reachable_nodes = set()
    for edges in sorted(all_flow_pathes):
        print(">>>>")
        print(edges)
        for n in path:
            reachable_nodes.add(n)
    print("reachable nodes", reachable_nodes)
    """

    # find all the OBJ_REACHES of each each ast nodes
    target_asts = []
    for ast in ast_list:
        target_asts.append(ast)
        cur_use_ast_edges = G.get_out_edges(ast, edge_type="OBJ_REACHES")
        cur_use_ast_edges.sort(key=lambda e: e[3]['timestamp'])
        for cur_use_ast_edge in cur_use_ast_edges:
            target_ast = cur_use_ast_edge[1]
            mid_obj = cur_use_ast_edge[3]['obj']
            if target_ast not in target_asts and target_ast not in ast_list:
                try:
                    # sometimes the target ast does not flows to others
                    # filter the ast that can not reach sink
                    if G.has_path(target_ast, ast_list[-1], edge_type='FLOWS_TO'):
                        if mid_obj in ast_tainted_objs:
                            target_asts.append(target_ast)
                except Exception as exc: 
                    pass
    return target_asts

def old_extend_ast_list(G, ast_list):
    """
    input a list of DF linked ast nodes, get obj between them and 
    get the use AST of the objs. Then try to sort the AST nodes in cf order
    hmmmm currently we do not have used edges
    then try to link the ast_list together by FLOW_TO edges
    """
    pre_ast = None
    # ast traceback
    ast_tainted_objs = []
    # obj traceback
    obj_tainted_objs = []
    # we use the ast_tainted_objs as a set
    # if an obj in obj_tainted_objs do not belongs to ast_tainted_objs
    # this is not a valid obj_tainted_objs

    stop_timestamp = -1
    # get the stop timestamp
    last_ast = ast_list[-1]
    out_edges = G.get_out_edges(last_ast, edge_type='LOOKUP')
    stop_timestamp = max([e[3]['timestamp'] for e in out_edges])

    # prepare ast_tainted_objs
    for ast in ast_list:
        if not pre_ast:
            pre_ast = ast
            continue
        edges = G.get_edge_attr(pre_ast, ast)
        for idx in edges:
            edge = edges[idx]
            if 'type:TYPE' in edge and edge['type:TYPE'] == 'OBJ_REACHES':
                ast_tainted_objs.append(edge['obj'])
        pre_ast = ast

    #prepare obj_tainted_objs
    ast_0 = ast_list[-2]
    ast_1 = ast_list[-1]
    edges = G.get_edge_attr(ast_0, ast_1)
    end_objs = []
    for idx in edges:
        edge = edges[idx]
        if 'type:TYPE' in edge and edge['type:TYPE'] == 'OBJ_REACHES':
            end_objs.append(edge['obj'])

    for obj in end_objs:
        tmp_objs = obj_traceback(G, obj)[0]

        for oto in tmp_objs:
            valid = True
            for n in oto:
                if n not in ast_tainted_objs:
                    valid = False
                print(n, valid)
            if valid:
                obj_tainted_objs += oto

    print("tainted objs", obj_tainted_objs)

    # tainted_obj should already in order
    # re-sort to make sure

    # pick the longest one
    # tainted_objs.sort(key=lambda x: len(x))
    # tainted_objs = tainted_objs[0]

    tainted_objs = [str(to) for to in obj_tainted_objs]
    stmts = []
    for obj in tainted_objs:
        in_edges = G.get_in_edges(obj, edge_type='LOOKUP')
        in_edges.sort(key=lambda x: x[3]['timestamp'])
        stmts += [e[0] for e in in_edges if e[3]['timestamp'] <= stop_timestamp]
    return stmts

def traceback(G, vul_type, start_node=None):
    """
    traceback from the leak point, the edge is OBJ_REACHES
    Args:
        G: the graph
        vul_type: the type of vulernability, listed below

    Return:
        the paths include the objs,
        the string description of paths,
        the list of callers,
    """
    res_path = ""
    ret_pathes = []
    caller_list = []
    if vul_type == "proto_pollution":
        # in this case, we have to specify the start_node
        if start_node is not None:
            start_cpg = G.find_nearest_upper_CPG_node(start_node)
            pathes = G._dfs_upper_by_edge_type(start_cpg, "OBJ_REACHES")

            for path in pathes:
                ret_pathes.append(path)
                path.reverse()
                res_path += get_path_text(G, path, start_cpg)
            
            return ret_pathes, res_path, caller_list

    sink_funcs = Sinks()
    expoit_func_list = sink_funcs.get_sinks_by_vul_type(vul_type)
    print("Sink functions:", expoit_func_list)

    func_nodes = G.get_node_by_attr('type', 'AST_METHOD_CALL')
    func_nodes += G.get_node_by_attr('type', 'AST_CALL')

    for func_node in func_nodes:
        # we assume only one obj_decl edge
        func_name = G.get_name_from_child(func_node)
        if func_name in expoit_func_list:
            caller = func_node
            caller = G.find_nearest_upper_CPG_node(caller)
            caller_list.append("{} called {}".format(caller, func_name))
            pathes = G._dfs_upper_by_edge_type(caller, "OBJ_REACHES")

            for path in pathes:
                ret_pathes.append(path)
                path.reverse()
                res_path += get_path_text(G, path, caller)
    return ret_pathes, res_path, caller_list

def do_vul_checking(G, rule_list, pathes):
    """
    checking the vuleralbilities in the pathes

    Args:
        G: the graph object
        rule_list: a list of paires, (rule_function, args of rule_functions)
        pathes: the possible pathes
    Returns:
        
    """
    trace_rules = []
    for rule in rule_list:
        trace_rules.append(TraceRule(rule[0], rule[1], G))

    success_pathes = []
    flag = True
    for path in pathes:
        flag = True
        for trace_rule in trace_rules:
            # print(path, trace_rule.key, trace_rule.check(path))
            if not trace_rule.check(path):
                flag = False
                break
        if flag:
            success_pathes.append(path)
    return success_pathes

def vul_checking(G, pathes, vul_type):
    """
    picking the pathes which satisfy the xss
    Args:
        G: the Graph
        pathes: the possible pathes
    return:
        a list of xss pathes
    """
    sink_funcs = Sinks()
    sanitation_funcs = sink_funcs.get_sinks_by_vul_type('sanitation',
            add_sinks=False)
    xss_rule_lists = [
            [('has_user_input', None), ('not_start_with_func', ['sink_hqbpillvul_http_write']), ('not_exist_func', ['parseInt']), ('end_with_func', sink_funcs.get_sinks_by_vul_type('xss'))],
            ]
    os_command_rule_lists = [
            [('has_user_input', None), ('not_start_within_file', ['child_process.js']), ('not_exist_func', ['parseInt'])]
            #[('start_with_var', ['source_hqbpillvul_url']), ('not_start_within_file', ['child_process.js']), ('not_exist_func', sanitation_funcs)]
            ]

    code_exec_lists = [
            [('has_user_input', None), ('not_start_within_file', ['eval.js']), ('not_exist_func', ['parseInt'])],
            # include os command here
            [('has_user_input', None), ('not_start_within_file', ['child_process.js']), ('not_exist_func', ['parseInt'])]
            ]
    proto_pollution = [
            [('has_user_input', None), ('not_exist_func', sanitation_funcs)]
            ]
    path_traversal = [
            [('start_with_var', ['OPGen_TAINTED_VAR_url']),
                ('not_exist_func', sanitation_funcs), 
                ('end_with_func', sink_funcs.get_sinks_by_vul_type('path_traversal')),
                ('exist_func', ['sink_hqbpillvul_fs_read'])
            ],
            [('start_with_var', ['OPGen_TAINTED_VAR_url']),
                ('not_exist_func', sanitation_funcs), 
                ('end_with_func', ['sink_hqbpillvul_http_sendFile'])
            ]
            ]
    """
    [('has_user_input', None),
        ('not_exist_func', sanitation_funcs), 
        ('end_with_func', ['sink_hqbpillvul_http_sendFile'])
    ],
    [('has_user_input', None),
        ('not_exist_func', sanitation_funcs), 
        ('end_with_func', sink_funcs.get_sinks_by_vul_type('path_traversal')),
        ('exist_func', ['sink_hqbpillvul_fs_read'])
    ]
    """

    vul_type_map = {
            "xss": xss_rule_lists,
            "os_command": os_command_rule_lists,
            "code_exec": code_exec_lists,
            "proto_pollution": proto_pollution,
            "path_traversal": path_traversal,
            }

    output_rules = [
            [('not_start_within_file', ['child_process.js'])]
            ]


    rule_lists = vul_type_map[vul_type]
    success_pathes = []
    print('vul_checking', vul_type)
    for path in pathes:
        res_text_path = get_path_text(G, path, path[0])
        loggers.main_logger.info(res_text_path)

    for rule_list in rule_lists:
        success_pathes += do_vul_checking(G, rule_list, pathes)
    print_success_pathes(G, success_pathes, color='green')

    if options.print_all_pathes:
        output_pathes = []
        for rule_list in output_rules:
            output_path = do_vul_checking(G, rule_list, pathes)
            for op in output_path:
                if op not in success_pathes and op not in output_pathes:
                    output_pathes.append(op)

        print_success_pathes(G, output_pathes, color='yellow')
    return success_pathes

def print_success_pathes(G, success_pathes, color=None):
    # for now, the success_pathes should be obj-edf edges
    if options.more_output:
        used_pathes = [old_extend_ast_list(G, sp) for sp in success_pathes]
    else:
        used_pathes = success_pathes
    color_map = {
            'green': sty.fg.li_green,
            'red': sty.fg.li_red,
            'blue': sty.fg.li_blue,
            'yellow': sty.fg.li_yellow
            }
    if color in color_map:
        sty_color = color_map[color]
    else:
        sty_color = color

    if len(success_pathes):
        loggers.print_logger.info(f"{sty_color}|Checker| success: {success_pathes} color: {color}{sty.rs.all}")

    path_id = 0
    for path in used_pathes:
        if len(path) == 0:
            continue
        res_text_path = get_path_text(G, path, path[0])
        loggers.tmp_res_logger.info("|checker| success id${}$color:{}$: ".format(path_id, color))
        loggers.tmp_res_logger.info(res_text_path)
        loggers.print_logger.info(f"{sty_color}Attack Path: ")
        loggers.print_logger.info(f'{res_text_path} {sty.rs.all}')

        path_id += 1
        
        """
    if options.more_output:
        used_pathes = [old_extend_ast_list(G, sp) for sp in success_pathes]
    else:
        used_pathes = success_pathes
    color_map = {
            'green': sty.fg.li_green,
            'red': sty.fg.li_red,
            'blue': sty.fg.li_blue,
            'yellow': sty.fg.li_yellow
            }
    if color in color_map:
        sty_color = color_map[color]
    else:
        sty_color = color
    print(sty_color + "|Checker| success: ", success_pathes ,"color: ", color)
    path_id = 0
    for path in used_pathes:
        if len(path) == 0:
            continue
        res_text_path = get_path_text(G, path, path[0])
        loggers.tmp_res_logger.info("|checker| success id${}$color:{}$: ".format(path_id, color))
        loggers.tmp_res_logger.info(res_text_path)
        path_id += 1
        print("Attack Path: ")
        print(res_text_path)
    print(sty.rs.all)

        """
