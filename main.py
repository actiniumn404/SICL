from termcolor import colored, cprint
from inspect import signature

import sys
import importlib
import pathlib
import re


class Variable():
    def __init__(self, name: str, type: str, flags: list):
        self.type = type
        self.name = name
        self.flags = flags
        self.data = None

    def define(self, content, line: int = -1):
        print(self.name, content)
        if "const" in self.flags:
            return SICL().error("AssignmentError", "cannot redefine a constant variable", line) and False
        self.data = content


class SICL():
    def __init__(self, code = None) -> None:
        self.code = code
        self.vars = {}
        self.line = 1
        self.data_types = ("string", "int", "bool", "float")
        self.functions = {
            "program": {}
        }
        if code:
            self.preprocess()
            self.main()

    def preprocess(self):
        output = ""
        replacement = {}
        for index, line in enumerate(self.code.splitlines()):
            line = line.strip().lower()
            output += line.strip() + "\n"
            param = line[1:].split(" ", maxsplit=2)
            if param[0] == "include":
                try:
                    self.functions[param[1]] = {}
                    importlib.import_module(f"modules.{param[1]}.main").setup(self.functions[param[1]])
                except FileNotFoundError:
                    self.error("FileNotFound", f"No such file \"{param[1]}\" was found", index + 1, action="preprocessing this program")
            elif param[0] == "replace":
                replacement[param[1]] = param[2]
        for before in replacement:
            output = output.replace(before, replacement[before])
        self.code = output

    def error(self, name: str, message: str, line_num: int, action="compiling this program"):
        cprint(colored(f'An exception occured while {action}\n  Line {line_num}\n{name}: {message}'), "red")
        exit(1)

    def get_args(self, line):
        """
        Expected Symtax:
        !std (arg1), (arg2), (arg3),
        """
        result = {}
        result["type"] = line[0]
        result["args"] = []
        i = 1
        syntax = ""
        while line[i-1] != " " and line[i-1] != "\n":
            syntax += line[i]
            i += 1
        if not syntax.strip():
            syntax = "program"
        result["syntax"] = syntax.strip()
        name = ""
        while line[i] != ":" and line[i] != "\n":
            name += line[i]
            i += 1
        i += 2
        result["name"] = name
        while i < len(line):
            arg = ""
            num_parth = 0
            while (line[i] != "," or num_parth) and line[i] != "\n":
                arg += line[i]
                if line[i] == "(":
                    num_parth += 1
                elif line[i] == ")":
                    num_parth -= 1
                i += 1
            result["args"].append(arg)
            while i < len(line) and line[i-1] != " " and line[i-1] != "\n":
                i += 1
        return result

    def convert(self, arg):
        arg = arg[1:-1]
        if all([x in list("0123456789") for x in arg]):
            return int(arg)
        if all([x in list("0123456789.") for x in arg]):
            return float(arg)
        if arg[0] == "$": # variable
            if arg[1:] not in self.vars:
                self.error("NameError", f'There is no variable named "{arg[1:]}"', self.line)
            return self.vars[arg[1:]].content
        if arg[0] == '"' and arg[-1] == '"':
            return arg[1:-1]

    def main(self):
        for index, line in enumerate(self.code.splitlines()):
            if not line:
                pass
            elif line[0] == "+":
                pass
            elif line[0] == "!":
                try:
                    args = self.get_args(line)
                except IndexError:
                    self.error("EOL", f"End of line (EOL) when scanning function call", index + 1)
                if args["syntax"] not in self.functions:
                    self.error("NameError", f"No module "+args["syntax"]+" was found.", index+1)
                elif args["name"] not in self.functions[args["syntax"]]:
                    self.error("NameError", f"No function called "+args["syntax"]+"."+args["name"]+" was found.", index+1)
                else:
                    func = self.functions[args["syntax"]][args["name"]]
                    sig = [str(x) for x in list(dict(signature(func).parameters).values())]
                    len_sig = len(sig)
                    if len(args["args"]) != len_sig and "*args" not in sig:
                        self.error("TypeError",
                                   f"Expected: "+str(len_sig)+" parameters, got "+str(len(args["args"])),
                                   index + 1)

                    if len(args["args"]) < len_sig - 1 and "*args" in sig:
                        self.error("TypeError",
                                   f"Expected: <= "+str(len_sig)+" parameters, got "+str(len(args["args"])),
                                   index + 1)

                    args["args"] = list(map(self.convert, args["args"]))
                    func(*args["args"]) # Python is so cool
            elif line[0] == "$":
                outline = re.match("\$([a-zA-Z_]+)\s{1,}([a-zA-Z]+)\[(.*)]\s{1,}=\s{1,}(.*)", line)
                if not outline:
                    self.error("SyntaxError", "Syntax used here does not adhere to the variable assignment syntax", self.line + 1)
                else:
                    # Outline: variable_name, data_type, additional_info, content
                    outline = outline.groups()
                    if outline[0] not in self.vars:
                        self.vars[outline[0]] = Variable(outline[0], outline[1], outline[2].split("/"))
                    self.vars[outline[0]].define(outline[3], self.line + 1)


            self.line += 1


if __name__ == "__main__":
    sys.path.extend([str(pathlib.Path().resolve())+"/modules"])
    if sys.argv[1] == "-f":
        SICL(open(sys.argv[2], "r").read())
    elif sys.argv[1] == "-i":
        SICL(sys.argv[2])
