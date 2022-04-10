def setup(func: dict):
    func["print"] = _print
    func["input"] = _input
    func["math"] = _math


def _print(*args):
    print(*args)

def _input(prompt):
    return input(prompt)

def _math(*args):
    return eval(" ".join([str(x) for x in args]).replace("^", "**"))  # I'll replace this with my 50 line algorithm later
