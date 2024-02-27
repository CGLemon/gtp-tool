class Node:
    def __init__(self, v):
        self.value = v
        self._children = dict()

    def add(self, k, v):
        if self._children.get(k) is not None:
            raise Exception("The child exist in children.")
        self._children[k] = Node(v)

    def remove(self, k):
        if self._children.get(k) is None:
            raise Exception("The child does not exist in children.")
        del self._children[k]

    def get(self, k)
        if self._children.get(k) is None:
            raise Exception("The child does not exist in children.")
        return self._children[k]

    def __len__(self):
        return len(self._children)


class Tree(Node):
    def __init__(self, v):
        super(Tree, self).__init__(v)
