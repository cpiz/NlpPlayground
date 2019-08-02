from abc import ABCMeta


class DoubleLinkedListNode(metaclass=ABCMeta):
    """
    双链表结点
    """
    prev = None
    next = None

    def __init__(self, prev=None, next=None):
        self.prev = prev
        self.next = next

    def nodes(self):
        """返回从当前结点开始所有结点的迭代器"""
        node = self
        while True:
            yield node
            node = node.next
            if not node:
                break

    def size(self):
        """
        获得链表结点数
        :return: 结点数
        """
        node = self
        count = 0
        while True:
            count = +1
            node = node.next
            if not node:
                break

        return count

    def head(self):
        """
        获得链表头部结点
        :return: 头结点
        """
        head = self
        while head.prev:
            head = head.prev
        return head

    def tail(self):
        """
        获得链表尾部结点
        :return: 尾结点
        """
        tail = self
        while tail.next:
            tail = tail.next
        return tail

    def insert_before(self, node):
        """
        在当前结点前方插入新结点，并返回新结点
        :param node: 新结点
        :return: 插入的新结点
        """
        node.prev = self.prev
        node.next = self
        self.prev = node
        if node.prev:
            node.prev.next = node

        return self.prev

    def insert_before_head(self, node):
        """
        在头结点前插入
        :return: 插入的新结点
        """
        return self.head().insert_before(node)

    def insert_after(self, node):
        """
        在当前结点之后插入新结点，并返回新结点
        :param node: 新结点
        :return: 插入的新结点
        """
        node.prev = self
        node.next = self.next
        self.next = node
        if node.next:
            node.next.prev = node

        return self.next

    def insert_after_tail(self, node):
        """
        在当前结点后方插入
        :return: 插入的新结点
        """
        return self.tail().insert_after(node)

    def delete(self):
        """
        删除当前结点
        :return: 返回下一个结点
        """
        if self.prev:
            self.prev.next = self.next

        if self.next:
            self.next.prev = self.prev

        return self.next if self.next else self.prev
