from src.core.graph import Graph 
from src.core.utils import ExtraInfo, NodeHandleResult, BranchTagContainer
from src.plugins.handler import Handler
from src.core.helpers import to_values
from src.core.logger import loggers, ATTENTION
import os

class HandleVar(Handler):
    """
    the var type handler including 
    AST_VAR, AST_CONST, AST_NAME
    """
    def process(self):
        side = self.extra.side if self.extra else None
        return handle_var(self.G, 
                self.node_id, side, self.extra)

def handle_var(G: Graph, ast_node, side=None, extra=None):
    cur_node_attr = G.get_node_attr(ast_node)
    var_name = G.get_name_from_child(ast_node)

    # mark var tainted if options.mark_tainted is set
    mark_tainted_flag = False
    if 'namespace' in cur_node_attr:
        namespace = cur_node_attr['namespace'].split(':')
        try:
            namespace = [int(n) for n in namespace]
        except:
            namespace = None

        if namespace is not None:
            for n in G.mark_tainted:
                # for now, we only check position match and text match
                #TODO: we should check file match in the future
                # only get the text and pos info
                n = n[1]
                if var_name == n['text'] and namespace[0] == n['start']['row'] and namespace[1] == n['start']['column'] and \
                        namespace[2] == n['end']['row'] and namespace[3] == n['end']['column']:
                    mark_tainted_flag = True
                    loggers.main_logger.info("Mark {} as tainted by user def".format(var_name))


    if var_name == 'this' and G.cur_objs:
        now_objs = G.cur_objs
        name_node = None
    elif var_name == '__filename':
        return NodeHandleResult(name=var_name, values=[
            G.get_cur_file_path()], ast_node=ast_node)
    elif var_name == '__dirname':
        return NodeHandleResult(name=var_name, values=[os.path.join(
            G.get_cur_file_path(), '..')], ast_node=ast_node)
    else:
        now_objs = []
        branches = extra.branches if extra else BranchTagContainer()

        name_node = G.get_name_node(var_name)
        if name_node is not None:
            now_objs = list(
                set(G.get_objs_by_name_node(name_node, branches=branches)))
        elif side != 'right':
            loggers.main_logger.log(ATTENTION, f'Name node {var_name} not found, create name node')
            if cur_node_attr.get('flags:string[]') == 'JS_DECL_VAR':
                # we use the function scope
                name_node = G.add_name_node(var_name,
                                scope=G.find_ancestor_scope())
            elif cur_node_attr.get('flags:string[]') in [
                'JS_DECL_LET', 'JS_DECL_CONST']:
                # we use the block scope                
                name_node = G.add_name_node(var_name, scope=G.cur_scope)
            else:
                # only if the variable is not defined and doesn't have
                # 'var', 'let' or 'const', we define it in the global scope
                name_node = G.add_name_node(var_name, scope=G.BASE_SCOPE)
        # else:
        #     now_objs = [G.undefined_obj]

    name_nodes = [name_node] if name_node is not None else []

    assert None not in now_objs

    # add from_branches information
    # from_branches = []
    # cur_branches = extra.branches if extra else BranchTagContainer()
    # for obj in now_objs:
    #     from_branches.append(cur_branches.get_matched_tags(
    #         G.get_node_attr(obj).get('for_tags') or []))

    # tricky fix, we don't really link name nodes to the undefined object
    if not now_objs:
        now_objs = [G.undefined_obj]
    loggers.main_logger.info("Var {} handle result -> {}".format(var_name, now_objs))
    for now_obj in now_objs:
        if mark_tainted_flag:
            G.set_node_attr(now_obj, ('tainted', True))
        loggers.main_logger.info(f"\t{now_obj}: {G.get_node_attr(now_obj)}")

    return NodeHandleResult(obj_nodes=now_objs, name=var_name,
        name_nodes=name_nodes, # from_branches=[from_branches],
        ast_node=ast_node)

