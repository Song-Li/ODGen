class PluginManager(object):
    """
    this is the parent class for all the internal plugins
    the Obj should be a singleton
    """
    instance = None
    class __PluginManager:
        def __init__(self, G):
            self.G = G
            self.handlermap = {}

        def dispatch_node(self, node_id, extra=None):
            """
            this method will dispatch nodes to different modules based
            on the type of the node
            the handling process for each node include multiple stages
            
            Args:
                G (Graph): the graph
                node_id (str): the id of the node
                extra (Extra): the extra info
            Returns:
                NodeHandleResult: the handle result of the node
            """
            node_attr = self.G.get_node_attr(node_id)
            print(node_attr)
            node_type = node_attr['type']

            handle_obj = self.handler_map[node_type](self.G, node_id, extra=extra)
            handle_res = handle_obj.process()
            return handle_res


    def __init__(self, G=None):
       if not PluginManager.instance:
           PluginManager.instance = PluginManager.__PluginManager(G)
    def __getattr__(self, val):
        return getattr(self.instance, val)
    def __setattr__(self, val):
        return setattr(self.instance, val)

