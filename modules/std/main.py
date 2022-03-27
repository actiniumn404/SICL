def setup(func: dict):
    func["print"] = _print
    func["input"] = _input

def _print(*args):
    print(*args)

def _input(prompt):
    return input(prompt)