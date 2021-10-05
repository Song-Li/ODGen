import re
from typing import List, Tuple, TypeVar, NoReturn
from enum import Enum
import math
import secrets
from collections import defaultdict

class NodeHandleResult:
    '''
    Object for storing AST node handling result.

    Args:
        obj_nodes (list, optional): Object nodes. Defaults to [].
        values (list, optional): Values of the variable or literal (as
            JavaScript source code, e.g. strings are quoted by quotation
            marks). Defaults to [].
        name (str, optional): Variable name. Defaults to None.
        name_nodes (list, optional): Name nodes. Defaults to [].
        used_objs (list, optional): Object nodes used in handling the
            AST node. Definition varies. Defaults to [].
        from_branches (list, optional): Experimental. Which branches
            the object nodes come from. Defaults to [].
        value_tags (list, optional): Experimental. For tags of values.
            Defaults to [].
        ast_node (optional): AST node ID. If it is not None, results
            will be printed out. Set the class variable 'print_callback'
            to customize print format. Defaults to None.
    '''

    @staticmethod
    def _print(handle_result):
        print(str(handle_result))

    print_callback = _print

    def __init__(self, **kwargs):
        self.successors = kwargs.get('successors', [])
        self.obj_nodes = kwargs.get('obj_nodes', [])
        self.values = kwargs.get('values', [])
        self.name = kwargs.get('name')
        self.name_nodes = kwargs.get('name_nodes', [])
        self.used_objs = kwargs.get('used_objs', [])
        self.from_branches = kwargs.get('from_branches', [])
        self.value_tags = kwargs.get('value_tags', [])
        self.value_sources = kwargs.get('value_sources', [])
        self.ast_node = kwargs.get('ast_node')
        self.name_tainted = kwargs.get('name_tainted')
        self.parent_is_proto = kwargs.get('parent_is_proto')
        self.parent_objs = kwargs.get('parent_objs')
        self.key_objs = kwargs.get('key_objs')
        self.terminated = kwargs.get('terminated')
        assert type(self.obj_nodes) == list
        assert type(self.used_objs) == list
        if self.ast_node:
            self.print_callback()
        if self.values and not self.value_sources:
            self.value_sources = [[]] * len(self.values)
        callback = kwargs.get('callback')
        if callback:
            callback(self)

    def __bool__(self):
        return bool(self.obj_nodes or self.values
            or (self.name is not None) or self.name_nodes or
            self.used_objs)

    def __repr__(self):
        s = []
        for key in dir(self):
            if not key.startswith("_") and not callable(getattr(self, key)) \
                and getattr(self, key):
                s.append(f'{key}={repr(getattr(self, key))}')
        args = ', '.join(s)
        return f'{self.__class__.__name__}({args})'


class BranchTag:
    '''
    Class for tagging branches.

    Args:
        point (str): ID of the branching point (e.g. if/switch
            statement).
        branch (str): Which branch (condition/case in the statement).
        mark (str): One of the following:
            Operation mark, 'A' for addition, 'D' for deletion.
            For-loop mark, 'L' for loop variable, 'P' for parent loop
                variable, 'C' for other variables created in the loop.
        ---
        or use this alternative argument:

        s (str/BranchTag): String to create the object directly, or copy
            the existing object.
    '''

    def __init__(self, s = None, **kwargs):
        self.point = None
        self.branch = None
        self.mark = None
        if s:
            try:
                self.point, self.branch, self.mark = re.match(
                    r'-?([^#]*)#(\d*)(\w?)', str(s)).groups()
                if self.point == '':
                    self.point = None
                if self.branch == '':
                    self.branch = None
                if self.mark == '':
                    self.mark = None
            except Exception:
                pass
        if 'point' in kwargs:
            self.point = kwargs['point']
        if 'branch' in kwargs:
            self.branch = str(kwargs['branch'])
        if 'mark' in kwargs:
            self.mark = kwargs['mark']
        # assert self.__bool__()

    def __str__(self):
        return '{}#{}{}'.format(
            self.point if self.point is not None else '',
            self.branch if self.branch is not None else '',
            self.mark if self.mark is not None else ''
        )

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.__str__()}")'

    def __hash__(self):
        return hash(self.__repr__())

    def __bool__(self):
        return bool(self.point and self.branch)

    def __eq__(self, other):
        return str(self) == str(other)


class BranchTagContainer(list):
    '''
    Experimental. An extension to list that contains branch tags.
    '''
    def __add__(self, other):
        return BranchTagContainer(list.__add__(self, other))

    def __repr__(self):
        return f'{self.__class__.__name__}({list.__repr__(self)})'

    def __str__(self):
        return list.__repr__(self)

    def __bool__(self):
        return len(self) != 0

    def get_last_choice_tag(self):
        '''
        Get the last choice statement (if/switch) tag.
        '''
        for i in reversed(self):
            if i.point.startswith('If') or i.point.startswith('Switch'):
                return i
        return None

    def get_last_for_tag(self):
        '''
        Get the last for statement or forEach tag.
        '''
        for i in reversed(self):
            if i.point.startswith('For'):
                return i
        return None

    def get_choice_tags(self):
        '''
        Get all choice statement (if/switch) tags.
        '''
        return BranchTagContainer(filter(
            lambda i: i.point.startswith('If') or i.point.startswith('Switch'),
            self))

    def get_for_tags(self):
        '''
        Get all for statement or forEach tags.
        '''
        return BranchTagContainer(filter(
            lambda i: i.point.startswith('For'), self))

    def get_creating_for_tags(self):
        '''
        Get all choice statement (if/switch) tags with an 'C' mark.
        '''
        return BranchTagContainer(filter(
            lambda i: i.point.startswith('For') and i.mark == 'C', self))

    def set_marks(self, mark):
        '''
        Set all tags' marks to a new mark.
        '''
        for tag in self:
            tag.mark = mark
        return self

    def get_matched_tags(self, target, level=2):
        '''
        Get tags matching with tags in 'target'.
        
        Args:
            target (Iterable): Target container.
            level (int, optional): Matching level.
                1: Only point matches.
                2: Point and branch match.
                3: Point, branch and mark match.
                Defaults to 2.
        
        Returns:
            BranchTagContainer: all matching tags.
        '''
        result = []
        for i in self:
            for j in target:
                flag = True
                if level >= 1 and i.point != j.point:
                    flag = False
                if level >= 2 and i.branch != j.branch:
                    flag = False
                if level >= 3 and i.mark != j.mark:
                    flag = False
                if flag:
                    result.append(i)
                    break
        return BranchTagContainer(set(result))

    def match(self, tag: BranchTag = None, point=None, branch=None, mark=None) \
        -> Tuple[int, BranchTag]:
        '''
        Find a matching BranchTag in the array.

        Use either a BranchTag or three strings as argument.

        Returns:
            Tuple[int, BranchTag]: index and the value of the matching
            BranchTag.
        '''
        if tag:
            point = tag.point
            branch = tag.branch
            mark = tag.mark
        for i, t in enumerate(self):
            if t.point == point and t.branch == branch:
                if mark and t.mark == mark:
                    return i, t
        return None, None

    def append(self, tag=None, point=None, branch=None, mark=None):
        if tag is not None:
            list.append(tag)
        elif point != None and branch != None:
            list.append(BranchTag(point=point, branch=branch, mark=mark))

    def is_empty(self):
        return not bool(self)


class ExtraInfo:
    def __init__(self, original=None, **kwargs):
        self.branches = BranchTagContainer()
        self.side = None
        self.parent_obj = None
        self.caller_ast = None
        self.switch_var = None
        self.class_obj = None
        if original is not None:
            self.branches = original.branches
            self.side = original.side
            self.parent_obj = original.parent_obj
            self.caller_ast = original.caller_ast
            self.switch_var = original.switch_var
            self.class_obj = original.class_obj
        if 'branches' in kwargs:
            self.branches = kwargs.get('branches')
        if 'side' in kwargs:
            self.side = kwargs.get('side')
        if 'parent_obj' in kwargs:
            self.parent_obj = kwargs.get('parent_obj')
        if 'caller_ast' in kwargs:
            self.caller_ast = kwargs.get('caller_ast')
        if 'switch_var' in kwargs:
            self.switch_var = kwargs.get('switch_var')
        if 'class_obj' in kwargs:
            self.class_obj = kwargs.get('class_obj')

    def __bool__(self):
        return bool(self.branches or (self.side is not None) or
            (self.parent_obj is not None) or (self.caller_ast is not None)
            or (self.switch_var is not None))

    def __repr__(self):
        s = []
        for key in dir(self):
            if not key.startswith("__"):
                s.append(f'{key}={repr(getattr(self, key))}')
        args = ', '.join(s)
        return f'{self.__class__.__name__}({args})'


class ValueRange:
    def __init__(self, original=None, **kwargs):
        self.min = kwargs.get('min', -math.inf)
        self.max = kwargs.get('max', math.inf)
        self.type = kwargs.get('type', 'float')


class DictCounter(defaultdict):
    def __init__(self):
        super().__init__(lambda: 0)
    def gets(self, key, val=0):
        value = super().get(key, val)
        return f'{key}:{value}'
    def __repr__(self):
        return f'{self.__class__.__name__}({dict(self)})'


def get_random_hex(length=6):
    return secrets.token_hex(length // 2)


class _SpecialValue(object):
    def __init__(self, alt):
        self.alt = alt
    def __str__(self):
        return self.alt
    def __repr__(self):
        return self.alt

wildcard = _SpecialValue('*')
undefined = _SpecialValue('undefined')


class JSSpecialValue(Enum):
    # deprecated
    UNDEFINED = 0
    NULL = 1
    NAN = 10
    INFINITY = 11
    NEGATIVE_INFINITY = 12
    TRUE = 20
    FALSE = 21
    OBJECT = 100
    FUNCTION = 101
