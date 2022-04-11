from termcolor import colored, cprint
from inspect import signature

import sys
import importlib
import pathlib
import re


class Variable():
    def __init__(self, name: str, type: str = "", flags: list = []):
        self.type = type
        self.additional = {}
        self.name = name
        self.flags = []
        self.flags.extend(flags)
        self.data = None


    def add_data(self, name, content):
        self.additional[name] = content


class SICL():
    def __init__(self, code="\n") -> None:
        self.code = code
        self.vars = {}
        self.line = 1
        self.data_types = ("string", "int", "bool", "float")
        self.functions = {
            "program": {}
        }
        if code != "\n":
            self.vars["__previf__"] = Variable("__previf__", "bool", ["sysdef"])
            self.define("__previf__", True)
            self.preprocess()
            self.main()

    def define(self, name, content):
        converter = {
            "string": str,
            "integer": int,
            "dec": float,
            "bool": lambda x: self.bool(str(x))
        }
        var = self.vars[name]
        if "const" in var.flags and var.data != None:
            return self.error("AssignmentError", "cannot redefine a constant variable", self.line + 1) and False
        if var.type not in converter:
            return self.error("MemoryError", "Invalid data type", self.line+1) and False
        var.data = converter[var.type](self.convert(content))

    def preprocess(self):
        output = ""
        replacement = {}
        for index, line in enumerate(self.code.splitlines()):
            line = line.strip()
            output += line.strip() + "\n"
            param = line[1:].split(" ", maxsplit=2)
            if param[0] == "include":
                try:
                    self.functions[param[1]] = {}
                    importlib.import_module(f"modules.{param[1]}.main").setup(self.functions[param[1]])
                except FileNotFoundError:
                    self.error("FileNotFound", f"No such file \"{param[1]}\" was found", index + 1,
                               action="preprocessing this program")
            elif param[0] == "replace":
                replacement[param[1]] = param[2]
        for before in replacement:
            output = output.replace(before, replacement[before])
        self.code = output

    def error(self, name: str, message: str, line_num: int, action="compiling this program", code=""):
        try:
            if not code:
                code = self.code
            line = code.splitlines()[line_num - 1]
        except IndexError:
            line = "[ERROR]"

        cprint(colored(f'An exception occured while {action}\n  Line {line_num}\n    {line}\n{name}: {message}'), "red")
        exit(1)

    def bool(self, boolstr):
        queue = boolstr.split(" ")
        while len(queue) != 1:
            try:
                op1 = self.convert(queue.pop(0))
                op = queue.pop(0)
                op2 = self.convert(queue.pop(0))
            except IndexError:
                self.error("SyntaxError", "Insufficient amount of logical arugments", self.line)
            if op == "+":
                queue.insert(0, op1 or op2)
            elif op == "*":
                queue.insert(0, op1 and op2)
            elif op == "~":
                queue.insert(0, not op1)
            elif op == "^":
                queue.insert(0, str(op1) in str(op2))
            elif op == "=":
                queue.insert(0, op1 == op2)
            elif op == "<":
                queue.insert(0, op1 < op2)
            elif op == ">":
                queue.insert(0, op1 > op2)
            else:
                self.error("SyntaxError", "Invalid logical operator \""+op+"\"", self.line)
        return bool(self.convert(queue[0]))

    def eval_func(self, line):
        outline = re.match("!([a-zA-Z_0-9]+) ([a-zA-Z_]+): (\(.*\),){1,}", line)
        if not outline:
            self.error("EOL", f"End of line (EOL) when scanning function call", self.line + 1)
        library, name, args = outline.groups()
        args = args.split(", ")
        if library not in self.functions:
            self.error("NameError", f"No module " + library + " was found.", self.line + 1)
        elif name not in self.functions[library]:
            self.error("NameError",
                       f"No function called " + library + "." + name + " was found.",
                       self.line + 1)
        else:
            func = self.functions[library][name]
            sig = [str(x) for x in list(dict(signature(func).parameters).values())]
            len_sig = len(sig)
            if len(args) != len_sig and "*args" not in sig:
                self.error("TypeError",
                           f"Expected: " + str(len_sig) + " parameters, got " + str(len(args)),
                           self.line + 1)

            if len(args) < len_sig - 1 and "*args" in sig:
                self.error("TypeError",
                           f"Expected: <= " + str(len_sig) + " parameters, got " + str(len(args)),
                           self.line + 1)

            args = list(map(self.convert, args))
            return func(*args)  # Python is so cool


    def convert(self, arg):
        if str(arg)[0] == "!":
            return self.eval_func(arg)
        arg = str(arg).strip("(),")
        if arg == "True":
            return True
        if arg == "False":
            return False
        if arg[:1] == "b!":
            return self.bool(arg[2:])
        if all([x in list("0123456789") for x in arg]):
            return int(arg)
        if all([x in list("0123456789.") for x in arg]):
            return float(arg)
        if arg[0] == "$":  # variable
            if arg[1:] not in self.vars:
                self.error("NameError", f'There is no variable named "{arg[1:]}"', self.line+1)
            return self.vars[arg[1:]].data
        if arg[0] == '"' and arg[-1] == '"':
            return arg[1:-1]

        return arg

    def main(self):
        while self.line < len(self.code.splitlines()):
            line = self.code.splitlines()[self.line]
            if not line:
                pass
            elif line[0] in ["+", "#"]:
                pass
            elif line[0] == "!":
                self.eval_func(line)

            elif line[0] == "$":
                outline = re.match("\$([a-zA-Z_]+)\s{1,}([a-zA-Z]+)\[(.*)]\s{1,}=\s{1,}(.*)", line)
                if not outline:
                    self.error("SyntaxError", "Syntax used here does not adhere to the variable assignment syntax",
                               self.line + 1)
                else:
                    # Outline: variable_name, data_type, additional_info, content
                    outline = outline.groups()
                    if outline[0] not in self.vars:
                        self.vars[outline[0]] = Variable(outline[0])
                    self.vars[outline[0]].type = outline[1]
                    self.define(outline[0], outline[3])
                    self.vars[outline[0]].flags.extend(outline[2].split("/"))

            elif line[0] == "@":
                if line[1] == "n":
                    outline = re.match("@n\s{1,}\$([a-zA-Z_]+)\s{1,}([0-9]+)\s{1,}([0-9]+)", line)
                    if not outline:
                        self.error("SyntaxError", "Syntax used here does not adhere to the number loop syntax",
                                   self.line + 1)
                    else:
                        var_name, lower, higher = outline.groups()
                        if not self.vars.get(var_name):
                            self.vars[var_name] = Variable(var_name, "integer", ["loopn"])
                        self.define(var_name, lower)
                        self.vars[var_name].add_data("upper", int(higher))
                        self.vars[var_name].add_data("loopback", self.line + 1)
                elif line[1] == "c":
                    outline = re.match("@c\s{1,}\$([a-zA-Z_]+)\s{1,}(.*)", line)
                    if not outline:
                        self.error("SyntaxError", "Syntax used here does not adhere to the conditional loop syntax",
                                   self.line + 1)
                    else:
                        var_name, cond = outline.groups()
                        if not self.vars.get(var_name):
                            self.vars[var_name] = Variable(var_name, "string", ["loopc"])
                        self.define(var_name, cond)
                        self.vars[var_name].add_data("loopback", self.line + 1)


                elif line[1] == "b":  # loopBack
                    outline = re.match("@b \$([a-zA-Z_]+)", line)
                    if not outline:
                        self.error("SyntaxError", "Syntax used here does not adhere to the loopback syntax",
                                   self.line + 1)
                    else:
                        var_name = outline.groups()[0]
                        if not self.vars.get(var_name):
                            self.error("NameError", f"Variable \"${var_name}\" does not exist", self.line + 1)
                        elif "loopc" not in self.vars.get(var_name).flags and "loopn" not in self.vars.get(var_name).flags:
                            self.error("TypeError", f"Variable \"{var_name}\" is not a loop variable", self.line + 1)
                        if "loopn" in self.vars.get(var_name).flags and self.vars[var_name].data < \
                                self.vars[var_name].additional["upper"]:
                            self.vars[var_name].data += 1
                            self.line = self.vars[var_name].additional["loopback"] - 1
                        elif "loopc" in self.vars.get(var_name).flags and self.bool(self.vars.get(var_name).data):
                            self.line = self.vars[var_name].additional["loopback"] - 1

            elif line[0] == "?":
                if line[1] == "i":
                    outline = re.match("\?if \$([a-zA-Z_]+) \| (.*)", line)
                    if not outline:
                        self.error("SyntaxError", "Syntax used here does not adhere to the conditional syntax",
                                   self.line + 1)
                    var_name, boolstr = outline.groups()
                    boolstr = self.bool(boolstr)
                    orig_line = self.line
                    self.define("__previf__", boolstr)
                    if not boolstr:
                        while not re.match("\?end \$"+var_name, self.code.splitlines()[self.line]):
                            self.line += 1
                            if self.line > len(self.code.splitlines()):
                                self.error("EOF", "End of file while scanning for end of conditional", orig_line)

            self.line += 1

if __name__ == "__main__":
    sys.path.extend([str(pathlib.Path().resolve()) + "/modules"])
    if sys.argv[1] == "-f":
        SICL(open(sys.argv[2], "r").read())
    elif sys.argv[1] == "-i":
        SICL(sys.argv[2])
