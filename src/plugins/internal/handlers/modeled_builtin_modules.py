from src.core.graph import Graph
from src.core.helpers import to_values, to_obj_nodes
from src.core.utils import NodeHandleResult, BranchTag, BranchTagContainer
from . import functions
import sty
import re
import os
from src.core.logger import *


def get_module(G, name):
    if name in modeled_modules:
        if name in G.builtin_modules:
            return G.builtin_modules[name]
        else:
            loggers.main_logger.log(ATTENTION, 'Setting up built-in module {}...'
                .format(name))
            module_exports = modeled_modules[name](G)
            G.builtin_modules[name] = module_exports
            return module_exports
    else:
        return None


def setup_fs(G: Graph):
    module_exports = G.add_obj_node()
    G.add_blank_func_as_prop('readFile', module_exports, read_file)
    G.add_blank_func_as_prop('readFileSync', module_exports, read_file_sync)
    return module_exports


def read_file(G: Graph, caller_ast, extra, _, path=NodeHandleResult(),
    options=None, callback=NodeHandleResult()):
    data = read_file_sync(G, caller_ast, extra, None, path, options)
    opgen.call_function(G, callback.obj_nodes,
        args=[NodeHandleResult(obj_nodes=[G.null_obj]), data],
        extra=extra)
    return NodeHandleResult()


def read_file_sync(G: Graph, caller_ast, extra, _, path=NodeHandleResult(),
    options=None):
    paths = list(filter(lambda x: x is not None, path.values))
    for obj in path.obj_nodes:
        value = G.get_node_attr(obj).get('code')
        if value is not None:
            paths.append(value)
    returned_values = []
    returned_objs = []
    for path in paths:
        abs_path = os.path.normpath(os.path.join(
                            G.get_cur_file_path(), '..', str(path)))
        if not os.path.exists(abs_path):
            loggers.main_logger.debug(f'Read file {path}, file does not exist')
            continue
        try:
            f = open(abs_path, 'r')
            content = f.read()
            f.close()
            returned_values.append(content)
            returned_objs.append(G.add_obj_node(js_type='string', value=content))
            loggers.main_logger.debug(f'Read file {path}, content: ' + re.sub(r'\n|\t', '',
                content))
        except Exception as e:
            loggers.main_logger.error(f'Read file {path} failed: {str(e)}')
    # return NodeHandleResult(values=returned_values) # TODO: move to values
    return NodeHandleResult(obj_nodes=returned_objs)


modeled_modules = {
    'fs': setup_fs
}
