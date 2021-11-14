from src.core.logger import loggers
from src.core.utils import ExtraInfo
from src.core.utils import NodeHandleResult
from src.core.options import options

class PluginManager(object):
    """
    this is the parent class for all the plugins
    the Obj should be a singleton
    if you want to use different handlers,
    change the location of the handlers here
    """
    instance = None
    class __PluginManager:
        from .internal.handlers.file import HandleFile as HandleFile
        from .internal.handlers.file import HandleToplevel \
                as HandleToplevel
        from .internal.handlers.operators import HandleAssign as HandleAssign
        from .internal.handlers.operators import HandleBinaryOP as HandleBinaryOP
        from .internal.handlers.functions import HandleASTCall as HandleASTCall
        from .internal.handlers.vars import HandleVar as HandleVar
        from .internal.handlers.const import HandleConst as HandleConst
        from .internal.handlers.func_decl import HandleFuncDecl as HandleFuncDecl
        from .internal.handlers.property import HandleProp as HandleProp
        from .internal.handlers.array import HandleArray as HandleArray, \
                HandleArrayElem as HandleArrayElem
        from .internal.handlers.array import HandleUnaryOp as HandleUnaryOp 
        from .internal.handlers.loop import HandleFor as HandleFor
        from .internal.handlers.loop import HandleForEach as HandleForEach
        from .internal.handlers.loop import HandleWhile as HandleWhile
        from .internal.handlers.expr_list import HandleExprList as HandleExprList
        from .internal.handlers.inc_dec import HandleIncDec as HandleIncDec
        from .internal.handlers.condition import HandleIf as HandleIf
        from .internal.handlers.condition import HandleConditional as HandleConditional
        from .internal.handlers.condition import HandleIfElem as HandleIfElem
        from .internal.handlers.switch import HandleSwitch as HandleSwitch
        from .internal.handlers.switch import HandleSwitchList as HandleSwitchList
        from .internal.handlers.returns import HandleReturn as HandleReturn 
        from .internal.handlers.null import HandleNULL as HandleNULL
        from .internal.handlers.try_catch import HandleTry as HandleTry 
        from .internal.handlers.encaps_list import HandleEncapsList as HandleEncapsList
        from .internal.handlers.assign_op import HandleAssignOP as HandleAssignOP
        from .internal.handlers.await_ import HandleAwait as HandleAwait
        from .internal.handlers.not_impl import HandleThrow as HandleThrow
        from .internal.handlers.not_impl import HandleBreak as HandleBreak
        from .internal.handlers.not_impl import HandleCatchList as HandleCatchList
        from .internal.handlers.not_impl import HandleContinue as HandleContinue
        from .internal.handlers.not_impl import HandleStmtList as HandleStmtList
        from .internal.handlers.not_impl import HandleClass as HandleClass
        from .internal.handlers.not_impl import HandleMethod as HandleMethod 
        def __init__(self, G):
            self.G = G
            self.handler_map = {
                    'File': self.HandleFile,
                    'Directory': self.HandleFile,
                    'AST_TOPLEVEL': self.HandleToplevel,
                    'AST_ASSIGN': self.HandleAssign,
                    'AST_CALL': self.HandleASTCall,
                    'AST_METHOD_CALL': self.HandleASTCall,
                    'AST_METHOD': self.HandleMethod,
                    'AST_NEW': self.HandleASTCall,
                    'AST_NAME': self.HandleVar,
                    'AST_VAR': self.HandleVar,
                    'AST_PROP': self.HandleProp,
                    'AST_DIM': self.HandleProp,
                    'AST_CONST': self.HandleVar,
                    'integer': self.HandleConst,
                    'string': self.HandleConst,
                    'double': self.HandleConst,
                    'AST_FUNC_DECL': self.HandleFuncDecl,
                    'AST_CLOSURE': self.HandleFuncDecl,
                    'AST_ARRAY': self.HandleArray,
                    'AST_ARRAY_ELEM': self.HandleArrayElem,
                    'AST_UNARY_OP': self.HandleUnaryOp,
                    'AST_FOR': self.HandleFor,
                    'AST_WHILE': self.HandleWhile,
                    'AST_FOREACH': self.HandleForEach,
                    'AST_BREAK': self.HandleBreak,
                    'AST_EXPR_LIST': self.HandleExprList,
                    'AST_PRE_INC': self.HandleIncDec,
                    'AST_POST_INC': self.HandleIncDec,
                    'AST_PRE_DEC': self.HandleIncDec,
                    'AST_POST_DEC': self.HandleIncDec,
                    'AST_IF': self.HandleIf,
                    'AST_IF_ELEM': self.HandleIfElem,
                    'AST_CONDITIONAL': self.HandleConditional,
                    'AST_BINARY_OP': self.HandleBinaryOP,
                    'AST_SWITCH': self.HandleSwitch,
                    'AST_SWITCH_LIST': self.HandleSwitchList,
                    'AST_RETURN': self.HandleReturn,
                    'AST_TRY': self.HandleTry,
                    'NULL': self.HandleNULL,
                    'AST_THROW': self.HandleThrow,
                    'AST_CATCH_LIST': self.HandleCatchList,
                    'AST_CONTINUE': self.HandleContinue,
                    'AST_STMT_LIST': self.HandleStmtList,
                    'AST_ASSIGN_OP': self.HandleAssignOP,
                    'AST_ENCAPS_LIST': self.HandleEncapsList,
                    'AST_CLASS': self.HandleClass,
                    'AST_YIELD': self.HandleAwait,
                    }

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
            if self.G.finished:
                return NodeHandleResult()

            if self.G.is_statement(node_id):
                line_mark = self.G.get_node_attr(node_id)['namespace'].split(":")
                loggers.main_logger.info(f"Running Line {line_mark[0]} to {line_mark[2]}")
                if node_id not in self.G.covered_stat:
                    self.G.covered_stat[node_id] = 0
                    self.G.all_stat.add(node_id)
                    loggers.progress_logger.info("{}".format(len(self.G.covered_stat) / self.G.get_total_num_statements()))
                #elif self.G.covered_stat[node_id] > 300:
                #    return NodeHandleResult()
                else:
                    self.G.covered_stat[node_id] += 1

            node_attr = self.G.get_node_attr(node_id)
            loggers.debug_logger.info("processing {}".format(node_id) + str(node_attr));
            node_type = node_attr['type']

            if node_type not in self.handler_map:
                loggers.error_logger.info(node_type + " not implemented")
                return NodeHandleResult()
                #raise LookupError(node_type + " not implemented")

            # remove side information
            # we should consider remove it totally, bug fixed on 08/03/2021
            # takes many hours to debug this one
            side = extra.side if extra else None
            extra = ExtraInfo(extra, side=None)

            handle_obj = self.handler_map[node_type](self.G, node_id, extra=extra)
            handle_res = handle_obj.process()

            return handle_res

        def update_graph(self, G):
            """
            update the graph
            """
            self.G = G

    def __init__(self, G=None, init=False):
       if not PluginManager.instance or init:
           print("new instance")
           PluginManager.instance = PluginManager.__PluginManager(G)
    def __getattr__(self, val):
        return getattr(self.instance, val)
    def __setattr__(self, val):
        return setattr(self.instance, val)

