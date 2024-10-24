from enum import Enum


class Relation(str, Enum):
    PARENT = 'parent'
    CHILD = 'child'