from src.core.graph import Graph
from src.core.utils import *

class Handler(object):
    """
    this is the parent class for all the handlers, including a 
    process method, a post_successors method.
    """
    def __init__(self, G: Graph, node_id: str, extra=None):
        from src.plugins.manager_instance import internal_manager as internal_manager
        self.internal_manager = internal_manager
        self.G = G
        self.node_id = node_id
        self.extra = extra

    def process(self):
        """
        for each handler, we should have a pre processing 
        method, which will actually run the node handle process.
        If the handling process can be finished in one function,
        we do not need further functions
        """
        print("Unimplemented Process Function")
        pass

