from src.plugins.handler import Handler
from src.core.utils import NodeHandleResult

class HandleConst(Handler) :
    """
    this is the handler for const values, including
    int, double and string
    """

    def process(self):
        G = self.G
        node_id = self.node_id
        cur_type = self.G.get_node_attr(self.node_id)['type']

        js_type = 'string' if cur_type == 'string' else 'number'
        code = self.G.get_node_attr(self.node_id).get('code')
        if cur_type == 'integer' and \
            code.startswith("0x") or code.startswith("0X"):
                value = int(code, 16)
        elif cur_type == 'integer' and \
            code.startswith("0b") or code.startswith("0B"):
                value = int(code, 2)
        elif cur_type == 'string':
            if self.G.get_node_attr(self.node_id).get('flags:string[]') == 'JS_REGEXP':
                added_obj = G.add_obj_node(ast_node=self.node_id,
                                           js_type=None, value=code)
                G.add_obj_as_prop('__proto__',
                    parent_obj=added_obj, tobe_added_obj=self.G.regexp_prototype)
                return NodeHandleResult(obj_nodes=[added_obj])
            else:
                value = code
        else:
            value = float(code)
        assert value is not None
        # added_obj = G.add_obj_node(node_id, js_type, code)
        return NodeHandleResult(values=[value])
