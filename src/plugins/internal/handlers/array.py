from src.plugins.handler import Handler
from src.core.utils import ExtraInfo
from src.plugins.internal.utils import to_values, wildcard, val_to_float
from src.core.logger import loggers
from ..utils import to_obj_nodes, NodeHandleResult, get_df_callback

class HandleArray(Handler):
    """
    the array handler
    """
    def process(self):
        G = self.G
        node_id = self.node_id
        if G.get_node_attr(node_id).get('flags:string[]') == 'JS_OBJECT':
            added_obj = G.add_obj_node(node_id, "object")
        else:
            added_obj = G.add_obj_node(node_id, "array")

        used_objs = set()
        children = G.get_ordered_ast_child_nodes(node_id)

        for child in children:
            result = self.internal_manager.dispatch_node(child, ExtraInfo(self.extra,
                parent_obj=added_obj))
            # used_objs.update(result.obj_nodes)

        G.add_obj_as_prop(prop_name='length', js_type='number',
            value=len(children), ast_node=node_id, parent_obj=added_obj)

        return NodeHandleResult(obj_nodes=[added_obj],
                                used_objs=list(used_objs),
                                callback=get_df_callback(G))

class HandleArrayElem(Handler):
    """
    the array element handler
    """
    def process(self):
        if not (self.extra and self.extra.parent_obj is not None):
            loggers.main_logger.error("AST_ARRAY_ELEM occurs outside AST_ARRAY")
            return None
        else:
            # should only have two childern
            try:
                value_node, key_node = self.G.get_ordered_ast_child_nodes(self.node_id)
            except:
                # TODO: Check what happend here for colorider
                return NodeHandleResult()
                
            key = self.G.get_name_from_child(key_node)
            if key is not None:
                key = key.strip("'\"")
            else:
                # shouldn't convert it to int
                key = self.G.get_node_attr(self.node_id).get('childnum:int')
            if key is None:
                key = wildcard
            handled_value = self.internal_manager.dispatch_node(value_node, self.extra)
            value_objs = to_obj_nodes(self.G, handled_value, self.node_id)
            # used_objs = list(set(handled_value.used_objs))
            for obj in value_objs:
                self.G.add_obj_as_prop(key, self.node_id,
                    parent_obj=self.extra.parent_obj, tobe_added_obj=obj)
        return NodeHandleResult(obj_nodes=value_objs, # used_objs=used_objs,
            callback=get_df_callback(self.G))

class HandleUnaryOp(Handler):
    def process(self):
        G = self.G
        node_id = self.node_id
        extra = self.extra

        child = G.get_ordered_ast_child_nodes(node_id)[0]
        handled = self.internal_manager.dispatch_node(child, extra)
        values, sources, _ = to_values(G, handled)
        new_values = []
        for v in values:
            if v == wildcard or v is None:
                new_values.append(v)
                continue
            v = val_to_float(v)
            if v != float('nan') and G.get_node_attr(node_id).get(
                    'flags:string[]') == 'UNARY_MINUS':
                new_values.append(-v)
            else:
                new_values.append(v)
        loggers.main_logger.debug(f'New values: {new_values}')
        return NodeHandleResult(values=new_values, value_sources=sources)

