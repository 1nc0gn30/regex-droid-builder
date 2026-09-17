"""
Regex Abstract Syntax Tree (AST) & Natural Language Explainer Engine.
Zero external runtime dependencies (100% Python Standard Library).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class NodeType(str, Enum):
    ROOT = "ROOT"
    SEQUENCE = "SEQUENCE"
    ALTERNATION = "ALTERNATION"
    GROUP = "GROUP"
    CHARACTER_CLASS = "CHARACTER_CLASS"
    LITERAL = "LITERAL"
    QUANTIFIER = "QUANTIFIER"
    ANCHOR = "ANCHOR"
    LOOKAROUND = "LOOKAROUND"


@dataclass
class ASTNode:
    """Represents a node in the Regex Abstract Syntax Tree."""
    type: NodeType
    value: str = ""
    description: str = ""
    quantifier: Optional[str] = None
    children: List[ASTNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AST node to dictionary."""
        return {
            "type": self.type.value,
            "value": self.value,
            "description": self.description,
            "quantifier": self.quantifier,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class RegexASTParser:
    """Parses a standard regular expression into a structured AST and human-readable explanation."""

    def __init__(self, pattern: str, flags: str = "") -> None:
        self.pattern = pattern
        self.flags = flags
        self.pos = 0
        self.length = len(pattern)

    def parse(self) -> ASTNode:
        """Parse the full regex pattern into an AST root node."""
        root = ASTNode(
            type=NodeType.ROOT,
            value=self.pattern,
            description=f"Regular Expression /{self.pattern}/{self.flags}"
        )
        if not self.pattern:
            return root

        nodes = self._parse_sequence()
        if len(nodes) == 1:
            root.children = [nodes[0]]
        else:
            seq = ASTNode(
                type=NodeType.SEQUENCE,
                value=self.pattern,
                description="Sequence of matching expressions",
                children=nodes
            )
            root.children = [seq]

        return root

    def _peek(self) -> Optional[str]:
        if self.pos < self.length:
            return self.pattern[self.pos]
        return None

    def _next(self) -> Optional[str]:
        if self.pos < self.length:
            ch = self.pattern[self.pos]
            self.pos += 1
            return ch
        return None

    def _parse_sequence(self) -> List[ASTNode]:
        nodes: List[ASTNode] = []
        alternation_branches: List[List[ASTNode]] = [[]]

        while self.pos < self.length:
            ch = self._peek()

            if ch == ")":
                # End of current group
                break

            if ch == "|":
                self._next()
                alternation_branches.append([])
                continue

            node = self._parse_atom()
            if node:
                # Check for subsequent quantifier
                node = self._apply_quantifier_if_present(node)
                alternation_branches[-1].append(node)

        if len(alternation_branches) > 1:
            branches = []
            for b in alternation_branches:
                if len(b) == 1:
                    branches.append(b[0])
                else:
                    branches.append(ASTNode(
                        type=NodeType.SEQUENCE,
                        description="Alternative branch",
                        children=b
                    ))
            alt_node = ASTNode(
                type=NodeType.ALTERNATION,
                description="Match either of the alternative branches",
                children=branches
            )
            return [alt_node]

        return alternation_branches[0]

    def _parse_atom(self) -> Optional[ASTNode]:
        ch = self._peek()
        if ch is None:
            return None

        # Group ( ... )
        if ch == "(":
            return self._parse_group()

        # Character class [ ... ]
        if ch == "[":
            return self._parse_character_class()

        # Anchors ^, $, \b, \B
        if ch in ("^", "$"):
            self._next()
            desc = "Start of string / line" if ch == "^" else "End of string / line"
            return ASTNode(type=NodeType.ANCHOR, value=ch, description=desc)

        # Escaped tokens
        if ch == "\\":
            self._next()
            esc = self._next()
            if esc is None:
                return ASTNode(type=NodeType.LITERAL, value="\\", description="Literal backslash")

            token = "\\" + esc
            if esc in ("d", "D"):
                desc = "Digit character (0-9)" if esc == "d" else "Non-digit character"
                return ASTNode(type=NodeType.CHARACTER_CLASS, value=token, description=desc)
            elif esc in ("w", "W"):
                desc = "Word character (a-z, A-Z, 0-9, _)" if esc == "w" else "Non-word character"
                return ASTNode(type=NodeType.CHARACTER_CLASS, value=token, description=desc)
            elif esc in ("s", "S"):
                desc = "Whitespace character (space, tab, newline)" if esc == "s" else "Non-whitespace character"
                return ASTNode(type=NodeType.CHARACTER_CLASS, value=token, description=desc)
            elif esc in ("b", "B"):
                desc = "Word boundary" if esc == "b" else "Non-word boundary"
                return ASTNode(type=NodeType.ANCHOR, value=token, description=desc)
            elif esc in ("A", "Z"):
                desc = "Absolute start of string" if esc == "A" else "Absolute end of string"
                return ASTNode(type=NodeType.ANCHOR, value=token, description=desc)
            else:
                return ASTNode(type=NodeType.LITERAL, value=token, description=f"Escaped literal '{esc}'")

        # Wildcard .
        if ch == ".":
            self._next()
            return ASTNode(type=NodeType.CHARACTER_CLASS, value=".", description="Any character (except newline)")

        # Normal Literal
        self._next()
        return ASTNode(type=NodeType.LITERAL, value=ch, description=f"Literal '{ch}'")

    def _parse_character_class(self) -> ASTNode:
        start_pos = self.pos
        self._next()  # Consume '['

        negated = False
        if self._peek() == "^":
            negated = True
            self._next()

        content = []
        while self.pos < self.length:
            ch = self._next()
            if ch == "]" and content:
                break
            if ch == "\\" and self.pos < self.length:
                ch += self._next()
            content.append(ch)

        inner = "".join(content)
        raw = f"[{'^' if negated else ''}{inner}]"
        desc = f"Match any character {'NOT ' if negated else ''}in set ({inner})"
        return ASTNode(
            type=NodeType.CHARACTER_CLASS,
            value=raw,
            description=desc,
            metadata={"negated": negated, "set": inner}
        )

    def _parse_group(self) -> ASTNode:
        self._next()  # Consume '('
        group_type = "capturing"
        name = None
        desc = "Capturing group"

        # Check for non-capturing, named, or lookaround
        if self._peek() == "?":
            self._next()
            spec = self._peek()

            if spec == ":":
                self._next()
                group_type = "non_capturing"
                desc = "Non-capturing group (grouping without backreference)"
            elif spec == "=":
                self._next()
                group_type = "positive_lookahead"
                desc = "Positive Lookahead: Asserts that following text matches"
            elif spec == "!":
                self._next()
                group_type = "negative_lookahead"
                desc = "Negative Lookahead: Asserts that following text does NOT match"
            elif spec == "<":
                self._next()
                look_sub = self._peek()
                if look_sub == "=":
                    self._next()
                    group_type = "positive_lookbehind"
                    desc = "Positive Lookbehind: Asserts that preceding text matches"
                elif look_sub == "!":
                    self._next()
                    group_type = "negative_lookbehind"
                    desc = "Negative Lookbehind: Asserts that preceding text does NOT match"
                else:
                    # Named capture group (?P<name>...) or (?<name>...)
                    name_chars = []
                    while self.pos < self.length and self._peek() != ">":
                        name_chars.append(self._next())
                    if self._peek() == ">":
                        self._next()
                    name = "".join(name_chars).lstrip("P")
                    group_type = "named_capture"
                    desc = f"Named capturing group '{name}'"

        children = self._parse_sequence()

        if self._peek() == ")":
            self._next()

        node_type = NodeType.LOOKAROUND if "look" in group_type else NodeType.GROUP
        return ASTNode(
            type=node_type,
            description=desc,
            children=children,
            metadata={"group_type": group_type, "name": name}
        )

    def _apply_quantifier_if_present(self, node: ASTNode) -> ASTNode:
        ch = self._peek()
        if ch in ("*", "+", "?", "{"):
            quant = ""
            if ch == "{":
                brace_chars = []
                while self.pos < self.length:
                    c = self._next()
                    brace_chars.append(c)
                    if c == "}":
                        break
                quant = "".join(brace_chars)
            else:
                quant = self._next()

            # Check for laziness '?' or possessiveness '+'
            modifier = ""
            if self._peek() == "?":
                modifier = self._next()
                quant += modifier
            elif self._peek() == "+":
                modifier = self._next()
                quant += modifier

            desc_map = {
                "*": "0 or more times (greedy)",
                "*?": "0 or more times (lazy / non-greedy)",
                "+": "1 or more times (greedy)",
                "+?": "1 or more times (lazy / non-greedy)",
                "?": "0 or 1 time (optional)",
                "??": "0 or 1 time (lazy optional)",
            }
            desc = desc_map.get(quant, f"Repeated {quant} times")

            node.quantifier = quant
            node.description = f"{node.description} — {desc}"
        return node


def explain_regex(pattern: str, flags: str = "") -> List[Dict[str, Any]]:
    """Generate a step-by-step plain English breakdown of the regular expression."""
    parser = RegexASTParser(pattern, flags)
    ast = parser.parse()

    breakdown: List[Dict[str, Any]] = []

    def walk(node: ASTNode, depth: int = 0) -> None:
        if node.type != NodeType.ROOT and node.type != NodeType.SEQUENCE:
            breakdown.append({
                "type": node.type.value,
                "value": node.value,
                "quantifier": node.quantifier,
                "explanation": node.description,
                "depth": depth,
            })
        for child in node.children:
            walk(child, depth + (1 if node.type != NodeType.ROOT else 0))

    walk(ast)
    return breakdown


class RegexBuilder:
    """Fluent programmatic Regex Builder API."""

    def __init__(self) -> None:
        self.parts: List[str] = []

    def start_of_line(self) -> RegexBuilder:
        self.parts.append("^")
        return self

    def end_of_line(self) -> RegexBuilder:
        self.parts.append("$")
        return self

    def literally(self, text: str) -> RegexBuilder:
        self.parts.append(re.escape(text))
        return self

    def digits(self, min_count: int = 1, max_count: Optional[int] = None) -> RegexBuilder:
        if max_count is None and min_count == 1:
            self.parts.append(r"\d+")
        elif max_count is None:
            self.parts.append(rf"\d{{{min_count},}}")
        elif min_count == max_count:
            self.parts.append(rf"\d{{{min_count}}}")
        else:
            self.parts.append(rf"\d{{{min_count},{max_count}}}")
        return self

    def word_characters(self, min_count: int = 1) -> RegexBuilder:
        self.parts.append(r"\w+" if min_count == 1 else rf"\w{{{min_count},}}")
        return self

    def whitespace(self) -> RegexBuilder:
        self.parts.append(r"\s+")
        return self

    def email(self) -> RegexBuilder:
        self.parts.append(r"[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}")
        return self

    def url(self) -> RegexBuilder:
        self.parts.append(r"https?:\/\/[^\s/$.?#].[^\s]*")
        return self

    def build(self) -> str:
        return "".join(self.parts)
