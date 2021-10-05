from src.core.graph import Graph
from src.plugins.handler import Handler
from src.core.utils import NodeHandleResult, wildcard
from ..utils import combine_values, val_to_float

class HandleIncDec(Handler):
    """
    handle the PRE_INC, POST_INC, PRE_DEC, POST_DEC
    """
    def process(self):
        G = self.G
        node_id = self.node_id
        cur_type = self.G.get_node_attr(self.node_id)['type']
        child = self.G.get_ordered_ast_child_nodes(self.node_id)[0]
        handled_child = self.internal_manager.dispatch_node(child, self.extra)
        returned_values = []
        sources = []
        for name_node in handled_child.name_nodes:
            updated_objs = []
            for obj in G.get_objs_by_name_node(name_node, self.extra.branches):
                v = G.get_node_attr(obj).get('code')
                if v == wildcard or v is None:
                    continue
                n = val_to_float(v)
                if 'POST' in cur_type:
                    returned_values.append(n)
                else:
                    if 'INC' in cur_type:
                        returned_values.append(n + 1)
                    else:
                        returned_values.append(n - 1)
                sources.append([obj])
                if 'INC' in cur_type:
                    new_value = n + 1
                else:
                    new_value = n - 1
                updated_objs.append(G.add_obj_node(
                        G.get_obj_def_ast_node(obj), 'number', new_value))
            G.assign_obj_nodes_to_name_node(name_node, updated_objs,
                branches=self.extra.branches)
        returned_values, sources = combine_values(returned_values, sources)
        return NodeHandleResult(values=returned_values, value_sources=sources)

