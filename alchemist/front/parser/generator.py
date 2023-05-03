# This file is part of the Alchemist front-end libraries
# Copyright (C) 2023  Natan Junges <natanajunges@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# The code generated by this library is also under the GNU General Public
# License.

from typing import Union
from collections.abc import Sequence

RuleTemplate = Union[Sequence["RuleTemplate"], "rule", str]


class rule:
    @staticmethod
    def get(arg: RuleTemplate) -> "rule":
        if isinstance(arg, tuple):
            return group(arg)

        if isinstance(arg, list):
            return optional(arg)

        if not isinstance(arg, rule):
            return term(arg)

        return arg

    @staticmethod
    def filter(args: Sequence[RuleTemplate]) -> list["rule"]:
        ret = [rule.get(arg) for arg in args if not isinstance(arg, switch) or
               arg.enabled]
        ret = [arg for arg in ret if isinstance(arg, term) or
               len(arg.args.args if isinstance(arg.args, group) else arg.args)
               > 0]
        return ret

    @staticmethod
    def indent(level: int) -> str:
        return "\n" + "    " * level

    @staticmethod
    def paths(level: int) -> str:
        return "paths" + str(level)

    def __init__(self, args: Union[list["rule"], "group"]):
        self.args: Union[list[rule], group] = args

    def __call__(self, indent_level: int, paths_level: int) -> str:
        raise NotImplementedError()


class group(rule):
    def __init__(self, args: Sequence[RuleTemplate]):
        super().__init__(rule.filter(args))
        i = 0

        while i < len(self.args):
            if isinstance(self.args[i], group):
                g = self.args[i].args
                self.args = self.args[:i] + g + self.args[i + 1:]
                i += len(g)
            else:
                i += 1

    def __call__(self, indent_level: int, paths_level: int) -> str:
        ret = ""

        for arg in self.args:
            ret += arg(indent_level, paths_level)

        return ret


class optional(rule):
    def __init__(self, args: list[RuleTemplate]):
        super().__init__(group(args))

        if (len(self.args.args) == 1 and
                isinstance(self.args.args[0], optional)):
            self.args = self.args.args[0].args

    def __call__(self, indent_level: int, paths_level: int) -> str:
        ret = "\n"
        ret += f"{rule.indent(indent_level)}try: # optional"
        ret += f"{rule.indent(indent_level + 1)}{rule.paths(paths_level + 1)} = {rule.paths(paths_level)}"
        ret += self.args(indent_level + 1, paths_level + 1)
        ret += f"{rule.indent(indent_level + 1)}{rule.paths(paths_level)} |= {rule.paths(paths_level + 1)}"
        ret += f"{rule.indent(indent_level)}except (CompilerSyntaxError, CompilerEOIError): pass"
        ret += "\n"
        return ret


class switch(rule):
    enabled: bool = False

    def __init__(self, *args: RuleTemplate):
        if self.enabled:
            super().__init__(group(args))

    def __call__(self, indent_level: int, paths_level: int) -> str:
        return self.args(indent_level, paths_level)


class repeat(rule):
    def __init__(self, *args: RuleTemplate):
        super().__init__(group(args))

        if len(self.args.args) == 1 and isinstance(self.args.args[0], repeat):
            self.args = self.args.args[0].args

    def __call__(self, indent_level: int, paths_level: int) -> str:
        ret = "\n"
        ret += f"{rule.indent(indent_level)}# begin repeat"
        ret += f"{rule.indent(indent_level)}{rule.paths(paths_level + 1)} = {rule.paths(paths_level)}"
        ret += "\n"
        ret += f"{rule.indent(indent_level)}while True:"
        ret += f"{rule.indent(indent_level + 1)}try:"
        ret += self.args(indent_level + 2, paths_level + 1)
        ret += f"{rule.indent(indent_level + 2)}{rule.paths(paths_level)} |= {rule.paths(paths_level + 1)}"
        ret += f"{rule.indent(indent_level + 1)}except (CompilerSyntaxError, CompilerEOIError): break"
        ret += "\n"
        ret += f"{rule.indent(indent_level)}# end repeat"
        ret += "\n"
        return ret


class oneof(rule):
    def __init__(self, *args: RuleTemplate):
        super().__init__(rule.filter(args))
        i = 0

        while i < len(self.args):
            if isinstance(self.args[i], oneof):
                o = self.args[i].args
                self.args = self.args[:i] + o + self.args[i + 1:]
                i += len(o)
            else:
                i += 1

    def __call__(self, indent_level: int, paths_level: int) -> str:
        if len(self.args) == 1:
            return self.args[0](indent_level, paths_level)

        ret = "\n"
        ret += f"{rule.indent(indent_level)}# begin oneof"
        ret += f"{rule.indent(indent_level)}{rule.paths(paths_level + 1)} = set()"

        for i, arg in enumerate(self.args):
            ret += "\n"
            ret += f"{rule.indent(indent_level)}try: # option {i + 1}"
            ret += f"{rule.indent(indent_level + 1)}{rule.paths(paths_level + 2)} = {rule.paths(paths_level)}"
            ret += arg(indent_level + 1, paths_level + 2)
            ret += f"{rule.indent(indent_level + 1)}{rule.paths(paths_level + 1)} |= {rule.paths(paths_level + 2)}"
            ret += f"{rule.indent(indent_level)}except CompilerSyntaxError: pass"

        ret += "\n"
        ret += f"{rule.indent(indent_level)}if len({rule.paths(paths_level + 1)}) == 0:"
        ret += f"{rule.indent(indent_level + 1)}raise CompilerSyntaxError(self)"
        ret += "\n"
        ret += f"{rule.indent(indent_level)}{rule.paths(paths_level)} = {rule.paths(paths_level + 1)}"
        ret += f"{rule.indent(indent_level)}# end oneof"
        ret += "\n"
        return ret


class term(rule):
    def __init__(self, arg: str):
        self.arg: str = arg

    def __call__(self, indent_level: int, paths_level: int) -> str:
        return rule.indent(indent_level) + rule.paths(paths_level) + " = self.process_paths(" + rule.paths(paths_level) + ", " + self.arg + ")"


class ProductionTemplate:
    rule: RuleTemplate = ()

    @classmethod
    def generate(cls) -> str:
        if isinstance(cls.rule, switch) and not cls.rule.enabled:
            return ""

        r = rule.get(cls.rule)

        if not isinstance(r, term) and len(r.args.args if
                                           isinstance(r.args, group) else
                                           r.args) == 0:
            return ""

        ret = f"class {cls.__name__}(Production):"
        ret += f"{rule.indent(1)}def __init__(self, parent: Optional[Production], lexer: \"Lexer\"):"
        ret += f"{rule.indent(2)}super().__init__(parent, lexer)"
        ret += f"{rule.indent(2)}{rule.paths(0)} = {{lexer.get_state()}}"
        ret += r(2, 0).replace("\n\n\n", "\n\n")
        ret += f"{rule.indent(2)}self.paths: set[\"Terminal\"] = {rule.paths(0)}"
        return ret
