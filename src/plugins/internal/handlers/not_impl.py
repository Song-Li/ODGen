from src.plugins.handler import Handler
from src.core.utils import NodeHandleResult
from src.core.logger import loggers

class HandleThrow(Handler):
    def process(self):
        loggers.error_logger.error("AST_THROW is not impelmented")
        return NodeHandleResult()

class HandleBreak(Handler):
    def process(self):
        loggers.error_logger.error("AST_BREAK is not impelmented")
        return NodeHandleResult()

class HandleCatchList(Handler):
    def process(self):
        loggers.error_logger.error("AST_CATCH_LIST is not implemented")
        return NodeHandleResult()

class HandleContinue(Handler):
    def process(self):
        loggers.error_logger.error("AST_CONTINUE is not implemented")
        return NodeHandleResult()

class HandleStmtList(Handler):
    def process(self):
        loggers.error_logger.error("AST_STMT_LIST is not implemented")
        return NodeHandleResult()

class HandleAssignOP(Handler):
    def process(self):
        loggers.error_logger.error("AST_ASSIGN_OP is not implemented")
        return NodeHandleResult()

class HandleClass(Handler):
    def process(self):
        loggers.error_logger.error("AST_CLASS is not implemented")
        return NodeHandleResult()

class HandleMethod(Handler):
    def process(self):
        loggers.error_logger.error("AST_Method is not implemented")
        return NodeHandleResult()