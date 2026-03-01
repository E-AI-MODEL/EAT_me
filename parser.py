from eatme.parser import load_eat, dump_eat


class EATParser:
    def load(self, path: str):
        return load_eat(path)


__all__ = ["EATParser", "load_eat", "dump_eat"]
