from src.plugins.handler import Handler
from src.plugins.internal.utils import to_obj_nodes

class HandleReturn(Handler):
    def process(self):
        returned_exp = self.G.get_ordered_ast_child_nodes(self.node_id)[0]
        results = self.internal_manager.dispatch_node(returned_exp, self.extra)
        # print(f'Returns: {results} -> {G.function_returns[G.find_ancestor_scope()]}')
        obj_nodes = to_obj_nodes(self.G, results, self.node_id)
        self.G.function_returns[self.G.find_ancestor_scope()][0].append(results)
        self.G.function_returns[self.G.find_ancestor_scope()][1].extend(obj_nodes)
        return results
