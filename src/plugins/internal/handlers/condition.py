from src.core.graph import Graph
from src.plugins.handler import Handler
from src.core.utils import BranchTag, NodeHandleResult, BranchTagContainer
from src.core.logger import * 
from . import blocks
from ..utils import get_random_hex, check_condition, decl_vars_and_funcs
from ..utils import has_else, merge, get_df_callback
from .blocks import simurun_block

class HandleIf(Handler):
    """
    handle the if ast
    """
    def process(self):
        G = self.G
        node_id = self.node_id
        extra = self.extra
        # lineno = G.get_node_attr(node_id).get('lineno:int')
        stmt_id = "If" + node_id + "-" + get_random_hex()
        if_elems = G.get_ordered_ast_child_nodes(node_id)
        branches = extra.branches
        parent_branch = branches.get_last_choice_tag()
        branch_num_counter = 0
        # if it is sure (deterministic) that "else" needs to run 
        else_is_deterministic = True
        for if_elem in if_elems:
            # for each if statement, we should make sure cfg starts from the 
            # if condition stmt
            G.cfg_stmt = node_id 

            condition, body = G.get_ordered_ast_child_nodes(if_elem)
            if G.get_node_attr(condition).get('type') == 'NULL': # else
                if else_is_deterministic or G.single_branch:
                    blocks.simurun_block(G, body, G.cur_scope, branches)
                else:
                    # not deterministic, create branch
                    branch_tag = BranchTag(
                        point=stmt_id, branch=str(branch_num_counter))
                    branch_num_counter += 1
                    blocks.simurun_block(G, body, G.cur_scope, branches+[branch_tag])
                break
            # check condition
            possibility, deterministic = check_condition(G, condition, extra)
            loggers.main_logger.debug('Check condition {} result: {} {}'.format(sty.ef.i +
                G.get_node_attr(condition).get('code') + sty.rs.all,
                possibility, deterministic))
            if deterministic and possibility == 1:
                # if the condition is surely true
                blocks.simurun_block(G, body, G.cur_scope, branches)
                break
            elif G.single_branch and possibility != 0:
                simurun_block(G, body, G.cur_scope)
            elif not deterministic or possibility is None or 0 < possibility < 1:
                # if the condition is unsure
                else_is_deterministic = False
                branch_tag = \
                    BranchTag(point=stmt_id, branch=str(branch_num_counter))
                branch_num_counter += 1
                blocks.simurun_block(G, body, G.cur_scope, branches+[branch_tag])
        # When there is no "else", we still need to add a hidden else
        if not has_else(G, node_id):
            branch_num_counter += 1
        # We always flatten edges
        if not G.single_branch:
            merge(G, stmt_id, branch_num_counter, parent_branch)
        return NodeHandleResult()

class HandleConditional(Handler):
    def process(self):
        node_id = self.node_id
        G = self.G
        extra = self.extra

        test, consequent, alternate = G.get_ordered_ast_child_nodes(node_id)
        loggers.main_logger.debug(f'Ternary operator: {test} ? {consequent} : {alternate}')
        possibility, deterministic = check_condition(G, test, extra)
        if deterministic and possibility == 1:
            return self.internal_manager.dispatch_node(consequent, extra)
        elif deterministic and possibility == 0:
            return self.internal_manager.dispatch_node(alternate, extra)
        else:
            h1 = self.internal_manager.dispatch_node(consequent, extra)
            h2 = self.internal_manager.dispatch_node(alternate, extra)
            return NodeHandleResult(obj_nodes=h1.obj_nodes+h2.obj_nodes,
                name_nodes=h1.name_nodes+h2.name_nodes, ast_node=node_id,
                values=h1.values+h2.values,
                value_sources=h1.value_sources+h2.value_sources,
                callback=get_df_callback(G))

class HandleIfElem(Handler):
    def process(self):
        # maybe wrong, but lets see
        # TODO: check how to handle if elem
        decl_vars_and_funcs(self.G, self.node_id)
