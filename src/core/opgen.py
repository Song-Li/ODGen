from .graph import Graph
from .utils import * 
from .helpers import * 
from .timeout import timeout, TimeoutError
from func_timeout import func_timeout, FunctionTimedOut
from src.core.pop_funcs import pop_funcs
from ..plugins.manager import PluginManager 
from ..plugins.internal.setup_env import setup_opg
from .checker import traceback, vul_checking
from .multi_run_helper import validate_package, get_entrance_files_of_package 
from .logger import loggers
from .options import options
import os
import shutil
import sys
from tqdm import tqdm

class OPGen:
    """
    This is the major class for the whole opgen
    """

    def __init__(self):
        self.graph = Graph()
        self.options = options
        self.graph.package_name = options.input_file
        setup_graph_env(self.graph)

    def get_graph(self):
        """
        get the current graph
        Returns:
            Graph: the current OPG
        """
        return self.graph

    def check_vuls(self, vul_type, G):
        """
        check different type of vulnerabilities
        Args:
            vul_type: the type of vuls
            G: the graph 
        Returns:
            the test result pathes of the module
        """
        vul_pathes = []

        if vul_type in ['os_command', 'path_traversal', 'code_exec', 'xss']:
            pathes = traceback(G, vul_type)
            vul_pathes = vul_checking(G, pathes[0], vul_type)

        return vul_pathes

    def test_file(self, file_path, vul_type='os_command', G=None, timeout_s=None):
        """
        test a file as a js script
        Args:
            file_path (str): the path to the file
            vul_type (str) [os_command, prototype_pollution, xss]: the type of vul
            G (Graph): the graph we run top of
        Returns:
            list: the test result pathes of the module
        """
        # TODO: add timeout for testing file
        if G is None:
            G = self.graph
        try:
            parse_file(G, file_path)
        except Exception as exc:
            print(exc)
            print(sty.fg.li_red + sty.ef.inverse +
                "[ERROR] AST parsing failed. Have you tried running the './install.sh' shell?\n"
                + "This does not look like a bug. Please follow the README.md to install the tool\n"
                + "And make sure the path to the package is correct."
                + sty.rs.all)
        test_res = self._test_graph(G, vul_type=vul_type)
        return test_res

    def _test_graph(self, G: Graph, vul_type='os_command'):
        """
        for a parsed AST graph, generate OPG and test vul
        Args:
            G (Graph): the Graph
            vul_type (str) [os_command, prototype_pollution, xss, ipt]: the type of vul
        Returns:
            list: the test result pathes of the module
        """
        setup_opg(G)
        G.export_node = True 
        internal_plugins = PluginManager(G, init=True)
        entry_id = '0'

        generate_obj_graph(G, internal_plugins, entry_nodeid=entry_id)

        if vul_type is not None:
            check_res = self.check_vuls(vul_type, G)
            if len(check_res) != 0:
                self.graph.detection_res[vul_type].add(G.package_name)

        if vul_type == 'proto_pollution':
            return self.graph.detection_res[vul_type]
        return check_res

    def test_module(self, module_path, vul_type='os_command', G=None, 
            timeout_s=None, from_nodejs=False):
        """
        test a file as a module
        Args:
            module_path: the path to the module
            vul_type (str) [os_command, prototype_pollution, xss]: the type of vul
            G (Graph): the graph we run top of
        Returns:
            list: the test result pathes of the module
        """
        print("Testing {} {}".format(vul_type, module_path))
        if module_path is None:
            print(sty.fg.li_red + sty.ef.inverse +
                "[ERROR] {} not found".format(module_path)
                + sty.rs.all)
            loggers.error_logger.error("[ERROR] {} not found".format(module_path))
            return []

        if G is None:
            G = self.graph

        test_res = []
        # only consider the finished packages
        output_code_coverage = True 
        module_timedout = True 
        single_mode_tried = False
        while(module_timedout):
            module_timedout = False 
            G = self.get_new_graph(package_name=module_path)

            if (not options.no_prioritized_funcs) or options.entrance_func is not None:
                if options.vul_type == 'proto_pollution':
                    test_res = start_from_func(G, module_path, vul_type=vul_type)
            if len(test_res) != 0:
                break

            #print("Prioritized funcs not working, starting normal run")
            G = self.get_new_graph(package_name=module_path)
            internal_plugins = PluginManager(G, init=True)
            js_call_templete = "var main_func=require('{}');".format(module_path)
            
            try:
                parse_string(G, js_call_templete)
            except:
                return []

            if timeout_s is not None:
                try:
                    test_res = func_timeout(timeout_s, self._test_graph, args=(G, vul_type))
                except FunctionTimedOut:
                    error_msg = "{} timedout after {} seconds".format(module_path, timeout_s)
                    module_timedout = True
                    output_code_coverage = False
                    loggers.error_logger.error(error_msg)
                    #loggers.res_logger.error(error_msg)
            else:
                test_res = self._test_graph(G, vul_type=vul_type)
            
            if module_timedout:
                if single_mode_tried:
                    print("timed out, trying to reduce the max_rep")
                    options.max_rep = int(options.max_rep / 2)
                    print("max_rep has been reduced to {}".format(options.max_rep))
                    if options.max_rep == 0:
                        break
                else:
                    print("timed out, trying to use single branch mode")
                    options.single_branch = True
                    single_mode_tried = True

        if module_timedout:
            error_msg = "{} timedout after {} seconds".format(module_path, timeout_s)
            loggers.res_logger.error(error_msg)

        if output_code_coverage:
            covered_stat = len(self.graph.get_covered_statements())
            total_stat = self.graph.get_total_num_statements()

            if total_stat != 0:
                # should not happen, just in case it is a totally blank package
                loggers.stat_logger.info(f"{covered_stat / total_stat}")

        return test_res

    def test_nodejs_package(self, package_path, vul_type='os_command', G=None, 
            timeout_s=None):
        """
        test a nodejs package
        Args:
            package_path (str): the path to the package
        Returns:
            the result state: 1 for found, 0 for not found, -1 for error
        """
        if not validate_package(package_path):
            print(sty.fg.li_red + sty.ef.inverse +
                "[ERROR] {} not found".format(package_path)
                + sty.rs.all)
            return -1
        if G is None:
            G = self.graph

        entrance_files = get_entrance_files_of_package(package_path)

        loggers.detail_logger.info(f"{G.package_name} started")
        for entrance_file in entrance_files:
            if G.finished:
                break
            test_res = self.test_module(entrance_file, vul_type, G, timeout_s=timeout_s, from_nodejs=True)
            if len(test_res) != 0:
                break
    
    def get_new_graph(self, package_name=None):
        """
        set up a new graph
        """
        self.graph = Graph()
        if not package_name:
            self.graph.package_name = options.input_file
        else:
            self.graph.package_name = package_name
        setup_graph_env(self.graph)
        return self.graph

    def output_args(self):
        loggers.main_logger.info("All args:")
        keys = [i for i in options.instance.__dict__.keys() if i[:1] != '_']
        for key in keys:
            loggers.main_logger.info("{}: {}".format(key, 
                options.instance.__dict__[key]))
    
    def run(self):
        self.output_args()
        if not os.path.exists(options.run_env):
            os.mkdir(options.run_env)

        timeout_s = options.timeout
        if options.install:
            # we have to provide the list if we want to install
            package_list = []
            with open(options.list, 'r') as fp:
                for line in fp.readlines():
                    package_path = line.strip()
                    package_list.append(package_path)
            install_list_of_packages(package_list)
            return 

        if options.run_test:
            # simple solution, should be updated later
            from src.core.test import run_tests 
            run_tests()
            return 

        if options.parallel is not None:
            prepare_split_list()
            num_thread = int(options.parallel)
            tmp_args = sys.argv[:]
            parallel_idx = tmp_args.index("--parallel")
            tmp_args[parallel_idx] = tmp_args[parallel_idx + 1] = ''
            try:
                list_idx = tmp_args.index("-l")
            except:
                list_idx = tmp_args.index("--list")
            for i in range(num_thread):
                cur_list_path = os.path.join(options.run_env, "tmp_split_list", str(i))
                tmp_args[list_idx + 1] = cur_list_path
                cur_cmd = ' '.join(tmp_args)
                os.system(f"screen -S runscreen_{i} -dm {cur_cmd}")
            return 

        if options.babel:
            babel_convert()
        if options.list is not None:
            package_list = []
            with open(options.list, 'r') as fp:
                for line in fp.readlines():
                    package_path = line.strip()
                    package_path = os.path.expanduser(package_path)
                    package_list.append(package_path)

            for package_path in package_list:
                # init a new graph
                self.get_new_graph(package_name=package_path)
                #self.test_module(package_path, options.vul_type, self.graph, timeout_s=timeout_s)
                self.test_nodejs_package(package_path, 
                        options.vul_type, self.graph, timeout_s=timeout_s)

                if len(self.graph.detection_res[options.vul_type]) != 0:
                    loggers.succ_logger.info("{} is detected in {}".format(
                        options.vul_type,
                        package_path))
                else:
                    loggers.res_logger.info("Not detected in {}".format(
                        package_path))


        else:
            if options.module:
                self.test_module(options.input_file, options.vul_type, self.graph, timeout_s=timeout_s)
            elif options.nodejs:
                self.test_nodejs_package(options.input_file, 
                        options.vul_type, G=self.graph, timeout_s=timeout_s)
            else:
                # analyze from JS source code files
                self.test_file(options.input_file, options.vul_type, self.graph, timeout_s=timeout_s)

            if len(self.graph.detection_res[options.vul_type]) != 0:
                print(sty.fg.li_green + sty.ef.inverse +
                    f'{options.vul_type} detected at {options.input_file}'
                    + sty.rs.all)
                loggers.succ_logger.info("{} is detected in {}".format(
                    options.vul_type,
                    options.input_file))
            else:
                loggers.res_logger.info("Not detected in {}".format(
                    options.input_file))

        if len(self.graph.detection_res[options.vul_type]) == 0:
            print(sty.fg.li_red + sty.ef.inverse +
                f'{options.vul_type} not detected. Have you tried the "-ma" argument?\n' + 
                "If it's a Node.js package, you can also try the '--nodejs -a' argument."
                + sty.rs.all)
        print("Graph size: {}, GC removed {} nodes".format(self.graph.get_graph_size(), self.graph.num_removed))
        print("Cleaning up tmp dirs")
        #shutil.rmtree(options.run_env)
        #export to csv
        if options.export is not None:
            if options.export == 'light':
                self.graph.export_to_CSV("./exports/nodes.csv", "./exports/rels.csv", light=True)
            else:
                self.graph.export_to_CSV("./exports/nodes.csv", "./exports/rels.csv", light=False)

def start_from_func(G, module_path, vul_type='proto_pollution'):
    """
    start from a special function
    """
    # start from a special function
    # pre-run the file, set the file stack limit to 2
    from src.plugins.internal.handlers.functions import call_function, run_exported_functions, ast_call_function
    # pretend another file is requiring this module
    js_call_templete = "var main_func=require('{}');".format(module_path)
    parse_string(G, js_call_templete)
    setup_opg(G)
    entry_nodeid = '0'
    internal_plugins = PluginManager(G, init=True)
    NodeHandleResult.print_callback = print_handle_result

    entry_nodeid = str(entry_nodeid)
    loggers.main_logger.info(sty.fg.green + "GENERATE OBJECT GRAPH" + sty.rs.all + ": " + entry_nodeid)
    obj_nodes = G.get_nodes_by_type("AST_FUNC_DECL")
    for node in obj_nodes:
        register_func(G, node[0])

    user_max_file_stack = options.max_file_stack
    user_run_all = options.run_all
    print("Pre-running file")
    #options.max_file_stack = 1
    options.run_all = False
    options.no_exports = True 

    # this process should not take very long
    # let's set a limit for this process
    try:
        func_timeout(options.pre_timeout, internal_plugins.dispatch_node, args=(entry_nodeid, None))
    except FunctionTimedOut:
        print("Pre-run file timedout")

    print("Pre run finished")

    options.max_file_stack = user_max_file_stack
    options.run_all = user_run_all
    options.no_exports = False 
    G.call_stack = []
    G.file_stack = []

    obj_nodes = G.get_nodes_by_type("AST_FUNC_DECL")
    file_nodes = G.get_nodes_by_type("AST_TOPLEVEL")
    closure_nodes = G.get_nodes_by_type("AST_CLOSURE")
    if options.timeout:
        function_timeout_s = options.timeout / 4
    else:
        function_timeout_s = 30
    
    if options.entrance_func is not None:
        target_list = [options.entrance_func]
    else:
        target_list = pop_funcs

    print("Entrance function list: {}".format(target_list))
    detection_res = None
    check_res = []
    for func in target_list:
        if G.finished:
            break
        for file_node in file_nodes:
            if file_node[1].get('name') == options.input_file:
                scope_edges = G.get_in_edges(file_node[0], edge_type="SCOPE_TO_AST")
                for scope_edge in scope_edges:
                    scope_node = scope_edge[0]
                    var_obj_nodes = G.get_objs_by_name(func, scope=scope_node)
                    if len(var_obj_nodes) != 0:
                        print("Running {} by under scope".format(func))
                        try:
                            func_timeout(function_timeout_s, run_exported_functions, args=(G, var_obj_nodes, None))
                            if vul_type == 'os_command' or vul_type == 'path_traversal':
                                pathes = traceback(G, vul_type)
                                check_res = vul_checking(G, pathes[0], vul_type)
                            if len(check_res) != 0:
                                G.detection_res[vul_type].add(G.package_name)
                        except FunctionTimedOut:
                            pass

        # if not found, try another way
        if len(G.detection_res[vul_type]) != 0:
            continue

        all_name_nodes = G.get_nodes_by_type("NAMENODE")
        for name_node in all_name_nodes:
            if name_node[1].get("name") == func:
                cur_obj_nodes = G.get_objs_by_name_node(name_node[0])
                if len(cur_obj_nodes) != 0:
                    print("Running {} by name node".format(func))
                    try:
                        func_timeout(function_timeout_s, run_exported_functions, args=(G, cur_obj_nodes, None))
                        if vul_type == 'os_command' or vul_type == 'path_traversal':
                            pathes = traceback(G, vul_type)
                            check_res = vul_checking(G, pathes[0], vul_type)

                        if len(check_res) != 0:
                            G.detection_res[vul_type].add(G.package_name)
                    except FunctionTimedOut:
                        pass
                    #call_function(G, cur_obj_nodes, mark_fake_args=True)
    # we need to check the vuls

    print(G.detection_res)
    return G.detection_res[vul_type]

def generate_obj_graph(G, internal_plugins, entry_nodeid='0', OPGen=None):
    """
    generate the object graph of a program
    Args:
        G (Graph): the graph to generate
        internal_plugins（PluginManager): the plugin obj
        entry_nodeid (str) 0: the entry node id,
            by default 0
    """
    NodeHandleResult.print_callback = print_handle_result

    entry_nodeid = str(entry_nodeid)
    loggers.main_logger.info(sty.fg.green + "GENERATE OBJECT GRAPH" + sty.rs.all + ": " + entry_nodeid)
    obj_nodes = G.get_nodes_by_type("AST_FUNC_DECL")
    for node in obj_nodes:
        register_func(G, node[0])
    internal_plugins.dispatch_node(entry_nodeid)

    while True:
        if G.task_queue:
            func1 = G.task_queue.popleft()
            func1(func1, G)
        while True: # always check the micro task queue
            if G.microtask_queue:
                func2 = G.microtask_queue.popleft()
                func2(func2, G)
            else:
                break
        if not G.task_queue: break

    """
    print("normal run finished, try prioritized funcs again")
    if (not options.no_prioritized_funcs) or options.entrance_func is not None:
        if not G.finished:
            start_from_func(G, internal_plugins)
    #add_edges_between_funcs(G)
    """

def install_list_of_packages(package_list):
    """
    install a list of packages into environment/packages/
    """
    from tools.package_downloader import download_package
    package_root_path = os.path.join(options.run_env, "packages")
    package_root_path = os.path.abspath(package_root_path)
    if not os.path.exists(package_root_path):
        os.mkdir(package_root_path)
    print("Installing packages")
    version_number = None
    for package in tqdm(package_list):
        if '@' in package and package[0] != '@':
            version_number = package.split('@')[1]
            package = package.split('@')[0]

        download_package(package, version_number, target_path=package_root_path)

def setup_graph_env(G: Graph):
    """
    setup the graph environment based on the user input

    Args:
        G (Graph): the Graph to setup
        options (options): the user input options
    """
    from src.plugins.manager_instance import internal_manager
    internal_manager.update_graph(G)

    if options.print:
        G.print = True
    G.run_all = options.run_all or options.list 
    if G.run_all is None:
        G.run_all = False
    #options.module or options.nodejs or options.list
    G.function_time_limit = options.function_timeout
    
    G.exit_when_found = options.exit
    G.single_branch = options.single_branch
    G.vul_type = options.vul_type
    G.func_entry_point = options.entry_func
    G.no_file_based = options.no_file_based
    G.check_proto_pollution = (options.prototype_pollution or 
                               options.vul_type == 'proto_pollution')
    G.check_ipt = (options.vul_type == 'ipt')

    # let's set exported func timeout to be 0.5 timeout
    # make sure we run at least 2 exported funcs
    #if options.timeout:
    #    options.exported_func_timeout = int(options.timeout * 0.5)

    G.call_limit = options.call_limit
    G.detection_res[options.vul_type] = set()
    if hasattr(options, 'mark_tainted'):
        G.mark_tainted = options.mark_tainted

def babel_convert():
    """
    use babel to convert the input files to ES5
    for now, we use system commands
    """
    try:
        shutil.rmtree(options.run_env)
    except:
        # sames the run_env does not exsit
        pass
    babel_location = "./node_modules/@babel/cli/bin/babel.js" 
    babel_cp_dir = os.path.join(options.run_env, 'babel_cp')
    babel_env_dir = os.path.join(options.run_env, 'babel_env')
    babel_config_dir = "./.babelrc"

    relative_path = os.path.relpath(options.input_file, options.babel)
    options.input_file = os.path.join(babel_env_dir, relative_path)
    os.system(f"mkdir {options.run_env} {babel_cp_dir} {babel_env_dir}")
    os.system(f"cp -rf {options.babel}/* ./{babel_cp_dir}/")
    # Handle the TS files and put result into cur dir
    os.system(f"{babel_location} {babel_cp_dir} --out-dir {babel_cp_dir} --extensions .ts --config-file {babel_config_dir}")
    # Handle the JS files
    os.system(f"{babel_location} {babel_cp_dir} --out-dir {babel_env_dir} --config-file {babel_config_dir}")
    # copy other files like package.json
    os.system(f"cp -rn {babel_cp_dir}/* {babel_env_dir}/")
    print("New entray point {}".format(options.input_file))

def prepare_split_list():
    """
    split the list into multiple sub lists
    """
    # if the parallel is true, we will start a list of screens
    # each of the screen will include another run
    num_thread = int(options.parallel)
    # make a tmp dir to store the 
    tmp_list_dir = "tmp_split_list"
    os.system("mkdir {}".format(os.path.join(options.run_env, tmp_list_dir)))
    package_list = None
    with open(options.list, 'r') as fp:
        package_list = fp.readlines()

    num_packages = len(package_list) 
    chunk_size = math.floor(num_packages / num_thread)
    sub_package_lists = [[] for i in range(num_thread)]
    file_pointer = 0
    for package in package_list:
        sub_package_lists[file_pointer % num_thread].append(package)
        file_pointer += 1

    cnt = 0
    for sub_packages in sub_package_lists:
        with open(os.path.join(options.run_env, tmp_list_dir, str(cnt)), 'w') as fp:
            fp.writelines(sub_packages)
        cnt += 1
    
