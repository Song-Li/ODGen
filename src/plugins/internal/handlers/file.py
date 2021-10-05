from src.core.graph import Graph
from src.core.utils import NodeHandleResult, ExtraInfo, BranchTagContainer
from src.core.logger import *
# file level handling is higher than function level
# we can safely import function level functions
from .functions import simurun_function
from ..utils import decl_function, decl_vars_and_funcs
from src.plugins.handler import Handler
from src.plugins.internal.handlers.class_ import handle_class


class HandleFile(Handler):

    def process(self):
        """
        handle the file node type
        Args:
            G (Graph): the graph
            node_id (str): the node id
        Returns:
            NodeHandleResult: the handle result
        """
        for child in self.G.get_child_nodes(self.node_id):
            self.internal_manager.dispatch_node(child, self.extra)

class HandleToplevel(Handler):
    
    def process(self):
        """
        handle the toplevel node type
        Args:
            G (Graph): the graph
            node_id (str): the node id
        Returns:
            NodeHandleResult: the handle result
        """
        flags = self.G.get_node_attr(self.node_id).get('flags:string[]')
        if flags == 'TOPLEVEL_FILE':
            module_exports_objs = run_toplevel_file(self.G, self.node_id)
            return NodeHandleResult(obj_nodes=module_exports_objs)
        elif flags == 'TOPLEVEL_CLASS':
            handle_class(self.G, self.node_id, self.extra)

def run_toplevel_file(G: Graph, node_id):
    """
    run a top level file 
    return a obj and scope
    """
    # switch current file path
    file_path = None
    if 'name' in G.get_node_attr(node_id):
        file_path = G.get_node_attr(node_id)['name']
    else:
        loggers.main_logger.error("[ERROR] " + node_id + "no file name")

    # loop call
    if file_path in G.file_stack:
        return [] 
    G.file_stack.append(file_path)
    if options.max_file_stack is not None:
        if len(G.file_stack) > options.max_file_stack + 1:
            return []
    print(G.file_stack)
    previous_file_path = G.cur_file_path
    G.cur_file_path = file_path
    if G.entry_file_path is None:
        G.entry_file_path = file_path
    loggers.main_logger.info(sty.fg(173) + sty.ef.inverse + 'FILE {} BEGINS'.format(file_path) + sty.rs.all)

    # add function object and scope
    func_decl_obj = decl_function(G, node_id, func_name=file_path,
        obj_parent_scope=G.BASE_SCOPE, scope_parent_scope=G.BASE_SCOPE)
    func_scope = G.add_scope(scope_type='FILE_SCOPE', decl_ast=node_id,
        scope_name=G.scope_counter.gets(f'File{node_id}'),
        decl_obj=func_decl_obj, func_name=file_path, parent_scope=G.BASE_SCOPE)

    backup_scope = G.cur_scope
    G.cur_scope = func_scope
    backup_stmt = G.cur_stmt

    # add module object to the current file's scope
    added_module_obj = G.add_obj_to_scope("module", node_id)
    # add module.exports
    added_module_exports = G.add_obj_as_prop("exports", node_id,
        parent_obj=added_module_obj)
    # add module.exports as exports
    G.add_obj_to_scope(name="exports", tobe_added_obj=added_module_exports)
    # "this" is set to module.exports by default
    # backup_objs = G.cur_objs
    # G.cur_objs = added_module_exports
    # TODO: this is risky
    G.add_obj_to_scope(name="this", tobe_added_obj=added_module_exports)

    # simurun the file
    simurun_function(G, node_id, block_scope=True)

    # get current module.exports
    # because module.exports may be assigned to another object
    # TODO: test if module is assignable
    module_obj = G.get_objs_by_name('module')[0]
    module_exports_objs = G.get_prop_obj_nodes(parent_obj=module_obj,
        prop_name='exports')

    #final_exported_objs = []
    """
    for obj in module_exports_objs:
        for o in G.get_prop_obj_nodes(obj):
            print('exported', G.get_node_attr(o))
    """
    # switch back scope, object, path and statement AST node id
    G.cur_scope = backup_scope
    # G.cur_objs = backup_objs
    G.cur_file_path = previous_file_path
    G.cur_stmt = backup_stmt

    G.file_stack.pop(-1)
    loggers.main_logger.info("{} exported".format(file_path))
    for nn in G.get_prop_name_nodes(module_exports_objs[0]):
        loggers.main_logger.info("\t{}".format(G.get_node_attr(nn)))

    return module_exports_objs
