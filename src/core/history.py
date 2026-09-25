class Stack:
    def __init__(self):
        self.data = []

    def push(self, item):
        self.data.append(item)

    def pop(self):
        return self.data.pop()

    def peak(self):
        if len(self.data) > 0:
            return self.data[-1]
        return None

    def clear(self):
        self.data.clear()

    def __len__(self): #Returns length of stack when len() is called
        return len(self.data)

class History:
    def __init__(self):
        self.undo_stack = Stack()
        self.redo_stack = Stack()

    #Save a new snapshot to the undo stack. Clear the redo stack
    def save_snapshot(self, snapshot):
        self.undo_stack.push(snapshot)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 0:
            snapshot = self.undo_stack.pop()
            self.redo_stack.push(snapshot)
            return snapshot

    def redo(self):
        if len(self.redo_stack) > 0:
            snapshot = self.redo_stack.pop()
            self.undo_stack.push(snapshot)
            return snapshot
