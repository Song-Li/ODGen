from src.plugins.handler import Handler
from .blocks import simurun_block

class HandleTry(Handler):
    def process(self):
        children = self.G.get_ordered_ast_child_nodes(self.node_id)
        simurun_block(self.G, children[0], branches=self.extra.branches)
        for child in children[1:]:
            self.internal_manager.dispatch_node(child, self.extra)
