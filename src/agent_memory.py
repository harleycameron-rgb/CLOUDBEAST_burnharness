"""Process-local FIFO buffer for agent state."""


class AgentMemory:
    def __init__(self):
        self.buffer = []

    def push(self, item):
        self.buffer.append(item)

    def pull(self):
        if not self.buffer:
            return None
        return self.buffer.pop(0)

    def clear(self):
        self.buffer.clear()
