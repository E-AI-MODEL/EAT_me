class CycleManager:
    PHASES = ["P", "TD", "C", "V", "T", "E", "L"]

    def __init__(self, loop=True, start="P"):
        self.loop = loop
        self.index = self.PHASES.index(start)

    @property
    def current(self) -> str:
        return self.PHASES[self.index]

    def advance(self) -> str:
        self.index = (self.index + 1) % len(self.PHASES)
        return self.current
