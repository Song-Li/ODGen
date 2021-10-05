from src.plugins.handler import Handler
from src.core.logger import *
from ..utils import peek_variables, val_to_str, is_int
from . import vars
from ..utils import check_condition, wildcard, is_wildcard_obj, add_contributes_to
from .blocks import simurun_block

class HandleFor(Handler):
    """
    handle the for loop
    """
    def process(self):
        node_id = self.node_id
        extra = self.extra
        G = self.G
        try:
            init, cond, inc, body = G.get_ordered_ast_child_nodes(node_id)[:4]
        except ValueError as e:
            for n in G.get_ordered_ast_child_nodes(node_id):
                loggers.main_logger.error(n, G.get_node_attr(n))
                loggers.error_logger.error(n, G.get_node_attr(n))
                return None
        cond = G.get_ordered_ast_child_nodes(cond)[0]
        # switch scopes
        parent_scope = G.cur_scope
        G.cur_scope = G.add_scope('BLOCK_SCOPE', decl_ast=body,
                      scope_name=G.scope_counter.gets(f'Block{body}'))
        result = self.internal_manager.dispatch_node(init, extra) # init loop variables

        counter = 0
        while True:
            # check increment to determine loop variables
            d = peek_variables(G, ast_node=inc, extra=extra) 
            loggers.main_logger.debug('For loop variables:')
            for name, obj_nodes in d.items():
                loggers.main_logger.debug(sty.ef.i + name + sty.rs.all + ': ' +
                    ', '.join([(sty.fg.green+'{}'+sty.rs.all+' {}').format(obj,
                    val_to_str(G.get_node_attr(obj).get('code'))) for obj in obj_nodes]))

            # check if the condition is met
            check_result, deterministic = check_condition(G, cond, extra)
            loggers.main_logger.debug('Check condition {} result: {} {}'.format(sty.ef.i +
                G.get_node_attr(cond).get('code') + sty.rs.all, check_result,
                deterministic))
            # avoid infinite loop
            if (not deterministic and counter > 3) or check_result == 0 or counter > 100:
                loggers.main_logger.debug('For loop {} finished'.format(node_id))
                break
            simurun_block(G, body, branches=extra.branches) # run the body
            result = self.internal_manager.dispatch_node(inc, extra) # do the inc
            counter += 1
        # switch back the scope
        G.cur_scope = parent_scope

class HandleForEach(Handler):
    """
    handle the for each loop
    """
    def _handle_for_in(self, G, ast_node, extra, logger, handle_node):
        obj, value, key, body = G.get_ordered_ast_child_nodes(ast_node)
        handled_obj = handle_node(obj, extra)
        # switch scopes
        parent_scope = G.cur_scope
        G.cur_scope = \
            G.add_scope('BLOCK_SCOPE', decl_ast=body,
                        scope_name=G.scope_counter.gets(f'Block{body}'))
        has_branches = (len(handled_obj.obj_nodes) > 1)
        for obj in handled_obj.obj_nodes:
            # handle and declare the loop variable
            handled_key = handle_node(key, extra)
            if G.finished or G.time_limit_reached:
                break
            # if the object is an array, only use numeric indices
            numeric_only = (G.get_node_attr(obj).get('type') == 'array')
            # loop through object's property names
            # if it's a wildcard object, include "__proto__"
            prop_names = G.get_prop_names(obj,
                            exclude_proto=not is_wildcard_obj(G, obj),
                            numeric_only=numeric_only,
                            exclude_wildcard=True)
            if is_wildcard_obj(G, obj):
                if G.check_proto_pollution:
                    # wildcard property for wildcard object
                    prop_names = [wildcard]
                    logger.debug(f'{obj} is a wildcard object.')
                else:
                    # wildcard property for wildcard object
                    prop_names.insert(0, wildcard)
                    logger.debug(f'{obj} is a wildcard object.')
            for k in prop_names:
                if str(k).startswith('Obj#'): # object-based keys
                    key_obj = k[4:]
                else:
                    # assign the name to the loop variable as a new 
                    # literal object
                    key_obj = G.add_obj_node(ast_node=ast_node,
                        js_type='string', value=k)
                    add_contributes_to(G, [obj], key_obj)
                logger.debug('For-in loop variables: '
                    f'{sty.ef.i}{handled_key.name}{sty.rs.all}: '
                    f'{sty.fg.green}{key_obj}{sty.rs.all}: {k} from obj {obj}')
                # text-based for-stack
                # G.for_stack.append('for-in {} {} {} in {}'
                #     .format(node_id, handled_key.name, k, obj))
                # full functional for-stack
                # (type, ast node, scope, loop var name, loop var value,
                #                       loop var value list, loop var origin list)
                G.for_stack.append(('for-in', ast_node, G.cur_scope,
                    handled_key.name, k, prop_names, handled_obj.obj_nodes))
                # print(G.for_stack)
                G.assign_obj_nodes_to_name_node(handled_key.name_nodes[0],
                    [key_obj], branches=extra.branches)
                # run the body
                G.last_stmts = [ast_node]
                simurun_block(G, body, branches=extra.branches)
                G.for_stack.pop()
            logger.debug('For-in loop {} finished'.format(ast_node))
        # switch back the scope
        G.cur_scope = parent_scope

    def _handle_for_of(self, G, ast_node, extra, logger, handle_node):
        obj, value, key, body = G.get_ordered_ast_child_nodes(ast_node)
        handled_obj = handle_node(obj, extra)
        # switch scopes
        parent_scope = G.cur_scope
        G.cur_scope = \
            G.add_scope('BLOCK_SCOPE', decl_ast=body,
                        scope_name=G.scope_counter.gets(f'Block{body}'))
        has_branches = (len(handled_obj.obj_nodes) > 1)
        for obj in handled_obj.obj_nodes:
            # handle and declare the loop variable
            handled_value = handle_node(value, extra)
            if G.finished or G.time_limit_reached:
                break
            # if the object is an array, only use numeric indices
            numeric_only = (G.get_node_attr(obj).get('type') == 'array')
            # loop through object's property name nodes
            # if it's a wildcard object, include "__proto__"
            prop_name_nodes = G.get_prop_name_nodes(obj,
                                    exclude_proto=not is_wildcard_obj(G, obj),
                                    numeric_only=numeric_only,
                                    exclude_wildcard=True)
            if is_wildcard_obj(G, obj):
                # wildcard property for wildcard object
                wildcard_prop_name_node = G.get_prop_name_node(wildcard, obj)
                wildcard_prop_obj_nodes = G.get_obj_nodes(
                    wildcard_prop_name_node, branches=extra.branches)
                if not wildcard_prop_obj_nodes or not wildcard_prop_obj_nodes:
                    wildcard_prop_obj_nodes = [G.add_obj_as_prop(wildcard,
                        ast_node, value=wildcard, parent_obj=obj)]
                    wildcard_prop_name_node = G.get_prop_name_node(wildcard, obj)
                prop_name_nodes.insert(0, wildcard_prop_name_node)
                logger.debug(f'{obj} is a wildcard object.')
            prop_obj_nodes = list(map(lambda nn:
                G.get_obj_nodes(nn, branches=extra.branches), prop_name_nodes))
            for name_node, obj_nodes in zip(prop_name_nodes, prop_obj_nodes):
                # obj_nodes = G.get_obj_nodes(name_node, branches=extra.branches)
                k = G.get_node_attr(name_node).get('name')
                logger.debug('For-of loop variables: '
                    f'{sty.ef.i}{handled_value.name}{sty.rs.all}: '
                    f'{sty.fg.green}{k}{sty.rs.all}: {obj_nodes} from obj {obj}')
                # text-based for-stack
                # ----------------------------------------------------------
                # full functional for-stack
                # (type, ast node, scope, loop var name, loop var value,
                #                       loop var value list, loop var origin list)
                G.for_stack.append(('for-of', ast_node, G.cur_scope,
                    handled_value.name, obj_nodes,
                    prop_obj_nodes, handled_obj.obj_nodes))
                # print(G.for_stack)
                G.assign_obj_nodes_to_name_node(handled_value.name_nodes[0],
                    obj_nodes, branches=extra.branches)
                # run the body
                G.last_stmts = [ast_node]
                simurun_block(G, body, branches=extra.branches)
                G.for_stack.pop()
            logger.debug('For-of loop {} finished'.format(ast_node))
        # switch back the scope
        G.cur_scope = parent_scope

    def process(self):
        G = self.G
        node_id = self.node_id
        extra = self.extra
        logger = loggers.main_logger
        handle_node = self.internal_manager.dispatch_node

        if G.get_node_attr(node_id).get('flags:string[]') == 'JS_FOR_IN':
            self._handle_for_in(G, node_id, extra, logger, handle_node)
        elif G.get_node_attr(node_id).get('flags:string[]') == 'JS_FOR_OF':
            self._handle_for_of(G, node_id, extra, logger, handle_node)

class HandleWhile(Handler):
    def process(self):
        node_id = self.node_id
        G = self.G
        extra = self.extra

        try:
            test, body = G.get_ordered_ast_child_nodes(node_id)[:2]
        except ValueError as e:
            for n in G.get_ordered_ast_child_nodes(node_id):
                logger.error(n, G.get_node_attr(n))
        # test = G.get_ordered_ast_child_nodes(test)[0] # wrongly influenced by for?
        # switch scopes
        parent_scope = G.cur_scope
        G.cur_scope = G.add_scope('BLOCK_SCOPE', decl_ast=body,
                      scope_name=G.scope_counter.gets(f'Block{body}'))
        counter = 0
        while True:
            # check if the condition is met
            check_result, deterministic = check_condition(G, test, extra)
            loggers.main_logger.debug('While loop condition {} result: {} {}'.format(
                sty.ef.i + G.get_node_attr(test).get('code') + sty.rs.all,
                check_result, deterministic))
            # avoid infinite loop
            if (not deterministic and counter > 3) or check_result == 0 or \
                counter > 10:
                loggers.main_logger.debug('For loop {} finished'.format(node_id))
                break
            simurun_block(G, body, branches=extra.branches) # run the body
            counter += 1
        # switch back the scope
        G.cur_scope = parent_scope

class HandleBreak(Handler):
    def process(self):
        # TODO: implement it
        pass
