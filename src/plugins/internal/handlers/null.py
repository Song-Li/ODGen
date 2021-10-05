from src.plugins.handler import Handler
from src.core.utils import NodeHandleResult

class HandleNULL(Handler):
    def process(self):
        return NodeHandleResult()
