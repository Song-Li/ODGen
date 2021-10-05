from src.plugins.handler import Handler
from src.core.options import options
from src.core.utils import NodeHandleResult, ExtraInfo
from src.core.helpers import to_values
from src.plugins.internal.utils import wildcard, undefined
from ..utils import is_wildcard_obj
from src.core.logger import loggers, sty
from ..utils import get_df_callback,add_contributes_to, to_obj_nodes
from itertools import chain
from src.plugins.internal.modeled_js_builtins_list import modeled_builtin_lists
from typing import Tuple

class HandleProp(Handler):
    """
    handle property
    """
    def process(self):
        side = self.extra.side if self.extra else None
        return handle_prop(self.G, 
                self.node_id, side, self.extra)[0]

def handle_prop(G, ast_node, side=None, extra=ExtraInfo()) \
    -> Tuple[NodeHandleResult, NodeHandleResult]:
    '''
    Handle property.
    
    Args:
        G (Graph): graph.
        ast_node ([type]): the MemberExpression (AST_PROP) AST node.
        extra (ExtraInfo, optional): Extra information. Defaults to {}.
    
    Returns:
        handled property, handled parent
    '''
    # recursively handle both parts
    from src.plugins.manager_instance import internal_manager
    logger = loggers.main_logger

    if extra is None:
        extra = ExtraInfo()

    parent, prop = G.get_ordered_ast_child_nodes(ast_node)[:2]
    handled_parent = internal_manager.dispatch_node(parent, extra)
    handled_prop = internal_manager.dispatch_node(prop, extra)
    if G.finished:
        return NodeHandleResult(), handled_parent
    
    parent_code = G.get_node_attr(parent).get('code')
    parent_name = handled_parent.name or parent_code or 'Unknown'
    parent_objs = to_obj_nodes(G, handled_parent)
    parent_name_nodes = handled_parent.name_nodes

    branches = extra.branches
    # side = extra.side # Do not use extra.side, may have been removed
    prop_name_nodes, prop_obj_nodes = set(), set()

    # prepare property names
    prop_names, prop_name_sources, prop_name_tags = \
                            to_values(G, handled_prop, for_prop=True)
    name_tainted = False
    key_objs = handled_prop.obj_nodes 
    # if G.check_proto_pollution or G.check_ipt:
    if True: # always true because timeout is solved
        for source in chain(*prop_name_sources):
            if G.get_node_attr(source).get('tainted'):
                name_tainted = True
                break


    parent_is_proto = False
    # if G.check_proto_pollution or G.check_ipt:
    if True: # always true because timeout is solved
        for obj in handled_parent.obj_nodes:
            if obj in G.builtin_prototypes:
                parent_is_proto = True
                break

    # create parent object if it doesn't exist
    parent_objs = list(filter(lambda x: x != G.undefined_obj, parent_objs))
    if not parent_objs:
        loggers.main_logger.debug(
            "PARENT OBJ {} NOT DEFINED, creating object nodes".
            format(parent_name))
        # we assume this happens when it's a built-in var name
        if parent_name_nodes:
            parent_objs = []
            for name_node in parent_name_nodes:
                obj = G.add_obj_to_name_node(name_node, ast_node,
                    js_type='object',
                    # if (G.check_proto_pollution or G.check_ipt) else None,
                    # always use 'object' because timeout is solved
                    value=wildcard)
                parent_objs.append(obj)
        else:
            obj = G.add_obj_to_scope(parent_name, ast_node,
                js_type='object',
                # if (G.check_proto_pollution or G.check_ipt) else None,
                # always use 'object' because timeout is solved
                scope=G.BASE_SCOPE, value=wildcard)
            parent_objs = [obj]
        # else:
        #     logger.debug("PARENT OBJ {} NOT DEFINED, return undefined".
        #         format(parent_name))
        #     return NodeHandleResult()

    multi_assign = False
    tampered_prop = False

    parent_is_tainted = len(list(filter(lambda x: \
            G.get_node_attr(x).get('tainted') is True, parent_objs))) != 0

    parent_is_prop_tainted = len(list(filter(lambda x: \
            G.get_node_attr(x).get('prop_tainted') is True, parent_objs))) != 0

    
    # find property name nodes and object nodes
    # (filtering is moved to find_prop)
    for i, prop_name in enumerate(prop_names):
        assert prop_name is not None
        name_nodes, obj_nodes, found_in_proto, proto_is_tainted = \
            find_prop(G, parent_objs, 
            prop_name, branches, side, parent_name,
            prop_name_for_tags=prop_name_tags[i],
            ast_node=ast_node, prop_name_sources=prop_name_sources[i])
        prop_name_nodes.update(name_nodes)
        prop_obj_nodes.update(obj_nodes)

        if prop_name == wildcard:
            multi_assign = True
        if G.check_ipt and side != 'left' and (proto_is_tainted or \
                (found_in_proto and parent_is_tainted) or \
                parent_is_prop_tainted):
                # second possibility, parent is prop_tainted
            tampered_prop = True
            G.ipt_use.add(ast_node)
            if G.exit_when_found:
                G.finished = True
            
            if 'ipt' not in G.detection_res:
                G.detection_res['ipt'] = set()

            ipt_type = 0
            if found_in_proto and parent_is_tainted:
                ipt_type = "Prototype hijacking"
            elif parent_is_prop_tainted:
                ipt_type = "App parent is prop tainted"
            else:
                ipt_type = "proto is tainted"
            detailed_info = "ipt detected in file {} Line {} node {} type {}".format(\
                    G.get_node_file_path(ast_node), 
                    G.get_node_attr(ast_node).get('lineno:int'),
                    ast_node,
                    ipt_type
                    )
            G.detection_res['ipt'].add(detailed_info)
            loggers.detail_logger.info(detailed_info)
            logger.warning(sty.fg.li_red + sty.ef.inverse + 'Possible internal'
                ' property tampering (any use) at node {} (Line {})'
                .format(ast_node, G.get_node_attr(ast_node).get('lineno:int'))
                + sty.rs.all)
            #loggers.res_logger.info(f"Internal property tampering detected in {G.package_name}")

    if len(prop_names) == 1:
        name = f'{parent_name}.{prop_names[0]}'
    else:
        name = f'{parent_name}.{"/".join(map(str, prop_names))}'

    # tricky fix, we don't really link name nodes to the undefined object
    if not prop_obj_nodes:
        prop_obj_nodes = set([G.undefined_obj])

    return NodeHandleResult(obj_nodes=list(prop_obj_nodes),
            name=f'{name}', name_nodes=list(prop_name_nodes),
            ast_node=ast_node, callback=get_df_callback(G),
            name_tainted=name_tainted, parent_is_proto=parent_is_proto,
            multi_assign=multi_assign, tampered_prop=tampered_prop,
            parent_objs = parent_objs, key_objs = key_objs
        ), handled_parent

def find_prop(G, parent_objs, prop_name, branches=None,
    side=None, parent_name='Unknown', in_proto=False, depth=0,
    prop_name_for_tags=None, ast_node=None, prop_name_sources=[]):
    '''
    Recursively find a property under parent_objs and its __proto__.
    
    Args:
        G (Graph): graph.
        parent_objs (list): parent objects.
        prop_name (str): property name.
        branches (BranchTagContainer, optional): branch information.
            Defaults to None.
        side (str, optional): 'left' or 'right', denoting left side or
            right side of assignment. Defaults to None.
        parent_name (str, optional): parent object's name, only used to
            print log. Defaults to ''.
        in_proto (bool, optional): whether __proto__ is being searched.
            Defaults to False.
    
    Returns:
        prop_name_nodes: set of possible name nodes.
        prop_obj_nodes: set of possible object nodes.
        found_in_proto: if the property is found in __proto__ chain
        proto_is_tainted: if the property is found in __proto__, and
            __proto__ is tainted (modified by user input).
    '''
    if depth == 5:
        return [], [], None, None
    
    if in_proto:
        loggers.main_logger.debug('Cannot find "direct" property, going into __proto__ ' \
                f'{parent_objs}...')
        loggers.main_logger.debug(f'  {parent_name}.{prop_name}')

    prop_name_nodes = set()
    prop_obj_nodes = set()
    # multi_assign = False
    proto_is_tainted = False
    found_in_proto = False

    for parent_obj in parent_objs:

        # removed because timeout is solved
        # if prop_name == wildcard and not is_wildcard_obj(G, parent_obj) and \
        #     not G.check_proto_pollution and not G.check_ipt:
        #     continue

        # if in_proto and G.get_node_attr(parent_obj).get('tainted'):
        if in_proto:
            found_in_proto = True
            if G.get_node_attr(parent_obj).get('tainted'):
                proto_is_tainted = True
                loggers.main_logger.debug(f'__proto__ {parent_obj} is tainted.')

        # Flag of whether any concrete name node is found
        name_node_found = False
        # Flag of whether any wildcard name node is found
        wc_name_node_found = False


        # Search "direct" properties
        prop_name_node = G.get_prop_name_node(prop_name, parent_obj)
        if prop_name_node is not None and prop_name != wildcard:
            name_node_found = True
            prop_name_nodes.add(prop_name_node)
            prop_objs = G.get_objs_by_name_node(prop_name_node,
                branches=branches)
            if prop_objs:
                prop_obj_nodes.update(prop_objs)

        # If name node is not found, search the property under __proto__.
        # Note that we cannot search "__proto__" under __proto__.
        elif prop_name != '__proto__' and prop_name != wildcard:
            __proto__name_node = G.get_prop_name_node("__proto__",
                parent_obj=parent_obj)
            if __proto__name_node is not None:
                __proto__obj_nodes = \
                    G.get_objs_by_name_node(__proto__name_node, branches)
                if parent_obj in __proto__obj_nodes:
                    loggers.main_logger.info(f'__proto__ {__proto__obj_nodes} and '
                        f'parent {parent_obj} have intersection')
                    __proto__obj_nodes = __proto__obj_nodes.remove(parent_obj)
                if __proto__obj_nodes:
                    __name_nodes, __obj_nodes, __in_proto, __t = find_prop(G,
                        __proto__obj_nodes, prop_name, branches,
                        parent_name=parent_name + '.__proto__',
                        in_proto=True, depth=depth+1)
                    if __name_nodes:
                        name_node_found = True
                        prop_name_nodes.update(__name_nodes)
                        prop_obj_nodes.update(__obj_nodes)
                        if __t:
                            proto_is_tainted = True
                        if __in_proto:
                            found_in_proto = True

        # If the property name is wildcard, fetch all properties
        if not in_proto and prop_name == wildcard:
            loggers.main_logger.info(f"prop name is wildcard, fetch all the name nodes")
            for name_node in G.get_prop_name_nodes(parent_obj):
                name = G.get_node_attr(name_node).get('name')
                if name == wildcard:
                    wc_name_node_found = True
                else:
                    name_node_found = True
                prop_name_nodes.add(name_node)
                prop_objs = G.get_objs_by_name_node(name_node,
                    branches=branches)
                if prop_objs:
                    prop_obj_nodes.update(prop_objs)
            loggers.main_logger.info(f"fetch res {prop_name_nodes}")

        # If the name node is not found, try wildcard (*).
        # If checking prototype pollution, add wildcard (*) results.
        # if (not in_proto or G.check_ipt) and prop_name != wildcard and (
        #         not name_node_found or G.check_proto_pollution or G.check_ipt):

        # always add wildcard (*) results because timeout is solved
        if prop_name != wildcard:
            prop_name_node = G.get_prop_name_node(wildcard, parent_obj)
            if prop_name_node is not None:
                wc_name_node_found = True
                prop_name_nodes.add(prop_name_node)
                prop_objs = G.get_objs_by_name_node(prop_name_node,
                    branches=branches)
                if prop_objs:
                    prop_obj_nodes.update(prop_objs)
                    if is_wildcard_obj(G, parent_obj):
                        for obj in prop_objs:
                            add_contributes_to(G, prop_name_sources, obj)

        # it happens that the not found is because of type problem
        if (not in_proto and not name_node_found) and is_wildcard_obj(G, parent_obj):
            # try to convert the object to a type of node
            for t in modeled_builtin_lists:
                if options.auto_type:
                    cur_methods = modeled_builtin_lists[t]
                else:
                    cur_methods = []
                if prop_name in cur_methods:
                    G.convert_wildcard_obj_type(parent_obj, t)
                    # re-run the find_prop after convert the obj type
                    return find_prop(G, parent_objs, prop_name, branches=branches,
                        side=side, parent_name=parent_name, in_proto=in_proto, depth=depth,
                        prop_name_for_tags=prop_name_for_tags, ast_node=ast_node, 
                        prop_name_sources=prop_name_sources)

        # Create a name node if not found.
        # We cannot create name node under __proto__.
        # Name nodes are only created under the original parent objects.

        # If this is an wildcard (unknown) object, add another
        # wildcard object as its property.
        # Note that if it's on left side and the property name is
        # known, you need to create it with the concrete property name.
        # if ((not in_proto or G.check_ipt) and is_wildcard_obj(G, parent_obj)
        #         and not wc_name_node_found and G.get_node_attr(parent_obj)['type'] == 'object' 
        #         and (side != 'left' or prop_name == wildcard)):
        
        # removed some conditions because timeout is solved
        if (is_wildcard_obj(G, parent_obj)
                and not wc_name_node_found and G.get_node_attr(parent_obj)['type'] == 'object' 
                and (side != 'left' or prop_name == wildcard)):
            added_name_node = G.add_prop_name_node(wildcard, parent_obj)
            prop_name_nodes.add(added_name_node)
            added_obj = G.add_obj_to_name_node(added_name_node,
                js_type='object' if G.check_proto_pollution or G.check_ipt
                else None, value=wildcard, ast_node=ast_node)                    

            # here since the obj comes from the parent
            # we need a CONTRIBUTE_TO from the parent to the obj
            # G.add_edge(parent_obj, added_obj, {'type': "CONTRIBUTES_TO"})
            prop_obj_nodes.add(added_obj)
            loggers.main_logger.debug('{} is a wildcard object, creating a wildcard'
                ' object {} for its properties'.format(parent_obj,
                added_obj))
            #print(parent_name, parent_obj, G.get_node_attr(parent_obj))
            if G.get_node_attr(parent_obj).get('tainted'):
                G.set_node_attr(added_obj, ('tainted', True))
                loggers.main_logger.debug("{} marked as tainted 1".format(added_obj))
            for s in prop_name_sources:
                add_contributes_to(G, [s], added_obj)
            # if name_node_found:
            #     multi_assign = True
            wc_name_node_found = True
        # Normal (known) object and concrete (known) property name,
        # or wildcard property name under normal (known) object
        elif not in_proto and ((not name_node_found and prop_name != wildcard)
                or (not wc_name_node_found and prop_name == wildcard)):
            if side == 'right':
                # Don't create anything on right side.
                # If the lookup failed, return empty results.
                continue
            elif parent_obj in G.builtin_prototypes:
                # Modifying internal prototypes are restricted
                # to avoid object explosion?
                loggers.main_logger.debug(
                    f'Trying to add prop name node under {parent_obj}')
                continue
            else:
                # On left side or normal property lookup,
                # only add a name node.
                # If there are multi-level property lookups, the object
                # node will be created on the lower level.
                added_name_node = \
                    G.add_prop_name_node(prop_name, parent_obj)
                prop_name_nodes.add(added_name_node)
                loggers.main_logger.debug(f'{sty.ef.b}Add prop name node{sty.rs.all} '
                    f'{parent_name}.{prop_name} '
                    f'({parent_obj}->{added_name_node})')
                if prop_name == wildcard:
                    wc_name_node_found = True
                else:
                    name_node_found = True
    # multi_assign = name_node_found and wc_name_node_found
    found_in_proto = found_in_proto and len(prop_name_nodes) != 0
    if found_in_proto:
        loggers.main_logger.info("{} found in prototype chain".format(prop_name))
    return prop_name_nodes, prop_obj_nodes, found_in_proto, proto_is_tainted
