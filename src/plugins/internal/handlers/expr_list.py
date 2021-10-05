from src.core.graph import Graph
from src.plugins.handler import Handler

class HandleExprList(Handler):
    """
    handle the expr list ast
    """
    def process(self):
        for child in self.G.get_ordered_ast_child_nodes(self.node_id):
            result = self.internal_manager.dispatch_node(child, self.extra)
        return result

