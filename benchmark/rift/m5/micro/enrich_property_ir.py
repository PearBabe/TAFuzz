#!/usr/bin/env python3
"""Build an immutable M5 typed-predicate sidecar from the frozen M4 corpus.

The extractor deliberately consumes only the public frozen source, the public
typed Property IR (AP id and source-location selectors), and Clang 18 AST JSON.
It never opens the M2 oracle and never derives predicate constants from prose.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, MutableMapping, Sequence


TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0.0"
PROPERTY_SCHEMA_VERSION = "2.0.0"
SUPPORTED_COMPILER_MAJOR = 18

COMPARISON_OPERATORS = {"==", "!=", "<", "<=", ">", ">="}
BOOLEAN_BINARY_OPERATORS = {"&&", "||"}
ARITHMETIC_OPERATORS = {"+", "-", "*", "/", "%"}
BITMASK_OPERATORS = {"&", "|", "^", "<<", ">>"}
ASSIGNMENT_OPERATORS = {
    "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="
}
TRANSPARENT_AST_WRAPPERS = {
    "ParenExpr",
    "ExprWithCleanups",
    "MaterializeTemporaryExpr",
    "CXXBindTemporaryExpr",
    "FullExpr",
}
CAST_AST_KINDS = {
    "ImplicitCastExpr",
    "CStyleCastExpr",
    "CXXStaticCastExpr",
    "CXXReinterpretCastExpr",
    "CXXConstCastExpr",
    "CXXFunctionalCastExpr",
    "CXXDynamicCastExpr",
}
LITERAL_AST_KINDS = {
    "IntegerLiteral",
    "FloatingLiteral",
    "CharacterLiteral",
    "CXXBoolLiteralExpr",
    "StringLiteral",
    "CXXNullPtrLiteralExpr",
    "GNUNullExpr",
}


class EnrichmentError(RuntimeError):
    """A closed-world extraction or input-contract failure."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: pathlib.Path) -> str:
    entries: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    return sha256_bytes(canonical_json_bytes(entries))


def atomic_write(path: pathlib.Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EnrichmentError(f"cannot load JSON {path}: {error}") from error


def stable_id(*parts: str) -> str:
    raw = ".".join(parts)
    normalized = re.sub(r"[^A-Za-z0-9_.:-]", "_", raw)
    if not normalized or not normalized[0].isalpha():
        normalized = "id." + normalized
    if len(normalized) <= 128:
        return normalized
    suffix = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return normalized[:107] + "." + suffix


def decode_json_stream(payload: str) -> list[Any]:
    decoder = json.JSONDecoder()
    position = 0
    values: list[Any] = []
    while True:
        while position < len(payload) and payload[position].isspace():
            position += 1
        if position == len(payload):
            return values
        try:
            value, position = decoder.raw_decode(payload, position)
        except json.JSONDecodeError as error:
            raise EnrichmentError(f"Clang AST output is not JSON at byte {position}: {error}") from error
        values.append(value)


def strip_process_specific_ast_ids(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_process_specific_ast_ids(item) for item in value]
    if isinstance(value, dict):
        return {
            key: strip_process_specific_ast_ids(item)
            for key, item in sorted(value.items())
            if key != "id"
        }
    return value


def normalized_point(raw: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    spelling = raw.get("spellingLoc")
    if isinstance(spelling, Mapping):
        return spelling
    expansion = raw.get("expansionLoc")
    if isinstance(expansion, Mapping):
        return expansion
    return raw


@dataclass(frozen=True)
class SourceBuffer:
    relative_path: str
    payload: bytes
    line_starts: tuple[int, ...]

    @classmethod
    def load(cls, root: pathlib.Path, relative_path: str) -> "SourceBuffer":
        payload = (root / relative_path).read_bytes()
        starts = [0]
        for offset, byte in enumerate(payload):
            if byte == 10:
                starts.append(offset + 1)
        return cls(relative_path=relative_path, payload=payload, line_starts=tuple(starts))

    def line_column(self, offset: int) -> tuple[int, int]:
        if offset < 0 or offset > len(self.payload):
            raise EnrichmentError(f"AST offset {offset} is outside {self.relative_path}")
        import bisect

        line_index = bisect.bisect_right(self.line_starts, offset) - 1
        return line_index + 1, offset - self.line_starts[line_index] + 1

    def location_for_node(self, node: Mapping[str, Any], *, member_token: bool = False) -> dict[str, Any]:
        raw_range = node.get("range") if isinstance(node.get("range"), Mapping) else {}
        if member_token:
            begin = normalized_point(node.get("loc") if isinstance(node.get("loc"), Mapping) else raw_range.get("end"))
        else:
            begin = normalized_point(raw_range.get("begin") if raw_range else node.get("loc"))
        if "offset" not in begin:
            begin = normalized_point(node.get("loc") if isinstance(node.get("loc"), Mapping) else None)
        offset = begin.get("offset")
        if not isinstance(offset, int):
            raise EnrichmentError(f"{node.get('kind', 'AST node')} has no spelling offset in {self.relative_path}")
        line, column = self.line_column(offset)
        token_length = begin.get("tokLen", 1)
        if not isinstance(token_length, int) or token_length <= 0:
            token_length = 1
        end_offset = min(len(self.payload), offset + token_length - 1)
        end_line, end_column = self.line_column(end_offset)
        return {
            "file": self.relative_path,
            "line": line,
            "column": column,
            "end_line": end_line,
            "end_column": end_column,
            "location_kind": "spelling",
        }


@dataclass(frozen=True)
class TargetTypeFacts:
    char_bit: int = 8
    char_signed: bool = True
    widths: Mapping[str, int] = field(default_factory=dict)

    @classmethod
    def from_macros(cls, macros: Mapping[str, str]) -> "TargetTypeFacts":
        def integer(name: str, default: int) -> int:
            raw = macros.get(name)
            if raw is None:
                return default
            match = re.match(r"^[()]?([0-9]+)", raw)
            return int(match.group(1)) if match else default

        char_bit = integer("__CHAR_BIT__", 8)
        sizes = {
            "char": integer("__SIZEOF_CHAR__", 1),
            "short": integer("__SIZEOF_SHORT__", 2),
            "int": integer("__SIZEOF_INT__", 4),
            "long": integer("__SIZEOF_LONG__", 8),
            "long long": integer("__SIZEOF_LONG_LONG__", 8),
            "float": integer("__SIZEOF_FLOAT__", 4),
            "double": integer("__SIZEOF_DOUBLE__", 8),
            "long double": integer("__SIZEOF_LONG_DOUBLE__", 16),
            "pointer": integer("__SIZEOF_POINTER__", 8),
            "wchar_t": integer("__SIZEOF_WCHAR_T__", 4),
        }
        widths = {name: size * char_bit for name, size in sizes.items()}
        widths["bool"] = integer("__BOOL_WIDTH__", char_bit)
        return cls(
            char_bit=char_bit,
            char_signed="__CHAR_UNSIGNED__" not in macros,
            widths=widths,
        )


def compiler_macros(compiler: str, compile_arguments: Sequence[str], cwd: pathlib.Path, language: str) -> dict[str, str]:
    retained: list[str] = []
    skip_next = False
    source_suffixes = {".c", ".cc", ".cpp", ".cxx", ".C", ".m", ".mm"}
    for argument in compile_arguments[1:]:
        if skip_next:
            skip_next = False
            continue
        if argument in {"-o", "-MF", "-MT", "-MQ", "-include-pch"}:
            skip_next = True
            continue
        if argument in {"-c", "-fsyntax-only"}:
            continue
        if pathlib.Path(argument).suffix in source_suffixes and not argument.startswith("-"):
            continue
        if argument.startswith(("-W", "-g", "-O")):
            continue
        retained.append(argument)
    command = [compiler, *retained, "-dM", "-E", "-x", language, "-"]
    completed = subprocess.run(command, cwd=cwd, input="", text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise EnrichmentError(f"compiler macro query failed ({completed.returncode}): {completed.stderr.strip()}")
    macros: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        match = re.match(r"^#define\s+(\S+)(?:\s+(.*))?$", line)
        if match:
            macros[match.group(1)] = match.group(2) or "1"
    return macros


def canonical_type_text(node: Mapping[str, Any]) -> str:
    raw_type = node.get("type")
    if not isinstance(raw_type, Mapping):
        return "<unknown>"
    value = raw_type.get("desugaredQualType") or raw_type.get("qualType")
    return value if isinstance(value, str) and value else "<unknown>"


def value_type(node: Mapping[str, Any], facts: TargetTypeFacts) -> dict[str, Any]:
    canonical = canonical_type_text(node)
    simplified = re.sub(r"\b(const|volatile|restrict|_Atomic)\b", "", canonical)
    simplified = re.sub(r"\s+", " ", simplified).strip()
    result: dict[str, Any] = {"kind": "unknown", "canonical": canonical}
    if simplified in {"bool", "_Bool"}:
        return {
            "kind": "bool",
            "canonical": canonical,
            "bit_width": facts.widths.get("bool", facts.char_bit),
            "signed": False,
        }
    if simplified.startswith("enum "):
        result["kind"] = "enum"
        return result
    integer_match = re.fullmatch(
        r"(?:(unsigned|signed)\s+)?(char|short(?: int)?|int|long(?: int)?|long long(?: int)?|wchar_t|char16_t|char32_t)",
        simplified,
    )
    if integer_match:
        sign_token, base = integer_match.groups()
        base = {"short int": "short", "long int": "long", "long long int": "long long"}.get(base, base)
        signed = sign_token != "unsigned"
        if base == "char" and sign_token is None:
            signed = facts.char_signed
        width = facts.widths.get(base)
        if base == "char16_t":
            width = 16
            signed = False
        elif base == "char32_t":
            width = 32
            signed = False
        result = {"kind": "integer", "canonical": canonical, "signed": signed}
        if width:
            result["bit_width"] = width
        return result
    if simplified in {"float", "double", "long double", "__float128"}:
        width = 128 if simplified == "__float128" else facts.widths.get(simplified)
        result = {"kind": "floating", "canonical": canonical}
        if width:
            result["bit_width"] = width
        return result
    if "*" in simplified or simplified.endswith("&") or simplified.endswith("&&") or simplified == "nullptr_t":
        result = {"kind": "pointer", "canonical": canonical}
        if facts.widths.get("pointer"):
            result["bit_width"] = facts.widths["pointer"]
        return result
    if re.search(r"\[[^]]*\]$", simplified):
        return {"kind": "array", "canonical": canonical}
    if simplified.startswith(("struct ", "class ", "union ")):
        return {"kind": "record", "canonical": canonical}
    return result


def literal_value(node: Mapping[str, Any]) -> Any:
    kind = node.get("kind")
    if kind in {"CXXNullPtrLiteralExpr", "GNUNullExpr"}:
        return None
    if kind == "CXXBoolLiteralExpr":
        raw = node.get("value")
        return raw is True or raw == "true" or raw == 1
    raw = node.get("value")
    if kind in {"IntegerLiteral", "CharacterLiteral"}:
        try:
            return int(str(raw), 0)
        except (TypeError, ValueError) as error:
            raise EnrichmentError(f"Clang emitted a non-integral {kind} value: {raw!r}") from error
    if kind == "FloatingLiteral":
        try:
            return float(str(raw))
        except (TypeError, ValueError) as error:
            raise EnrichmentError(f"Clang emitted a non-floating literal value: {raw!r}") from error
    if kind == "StringLiteral":
        if not isinstance(raw, str):
            raise EnrichmentError("Clang emitted a non-string StringLiteral")
        return raw
    raise EnrichmentError(f"unsupported literal kind {kind}")


def child_nodes(node: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    inner = node.get("inner")
    if not isinstance(inner, list):
        return []
    return [child for child in inner if isinstance(child, Mapping)]


@dataclass
class ReferenceFact:
    selector_id: str
    role: str
    ast_kind: str
    location: dict[str, Any]
    value_type: dict[str, Any]
    predicate_path: str


@dataclass
class ConversionContext:
    case_id: str
    ap_id: str
    source: SourceBuffer
    type_facts: TargetTypeFacts
    references: list[ReferenceFact] = field(default_factory=list)
    unsupported: Counter[str] = field(default_factory=Counter)
    transparent_wrappers: Counter[str] = field(default_factory=Counter)

    def add_reference(self, node: Mapping[str, Any], role: str, path: str, *, member_token: bool = False) -> str:
        ordinal = len(self.references)
        selector_id = stable_id("sel", self.case_id, self.ap_id, f"ref{ordinal:03d}", str(node.get("kind", "unknown")))
        fact = ReferenceFact(
            selector_id=selector_id,
            role=role if role in {"state", "bound", "guard"} else "guard",
            ast_kind=str(node.get("kind", "unknown")),
            location=self.source.location_for_node(node, member_token=member_token),
            value_type=value_type(node, self.type_facts),
            predicate_path=path,
        )
        self.references.append(fact)
        return selector_id


def expression_from_ast(node: Mapping[str, Any], context: ConversionContext, role_hint: str, path: str = "root") -> dict[str, Any]:
    kind = str(node.get("kind", "<missing>"))
    children = child_nodes(node)
    if kind in TRANSPARENT_AST_WRAPPERS:
        context.transparent_wrappers[kind] += 1
        if len(children) != 1:
            context.unsupported[f"{kind}:arity_{len(children)}"] += 1
            return {
                "node_kind": "unknown",
                "operator": kind,
                "value_type": value_type(node, context.type_facts),
                "operands": [
                    expression_from_ast(child, context, role_hint, f"{path}.{index}")
                    for index, child in enumerate(children)
                ],
            }
        return expression_from_ast(children[0], context, role_hint, path)

    result: dict[str, Any] = {
        "node_kind": "unknown",
        "operator": None,
        "value_type": value_type(node, context.type_facts),
        "operands": [],
    }

    if kind in CAST_AST_KINDS:
        result["node_kind"] = "cast"
        result["operator"] = str(node.get("castKind") or kind)
        result["operands"] = [
            expression_from_ast(child, context, role_hint, f"{path}.{index}")
            for index, child in enumerate(children)
        ]
        if len(children) != 1:
            context.unsupported[f"{kind}:arity_{len(children)}"] += 1
        return result

    if kind == "DeclRefExpr":
        selector_id = context.add_reference(node, role_hint, path)
        result.update(
            node_kind="reference",
            operator="decl_ref",
            referenced_selector_id=selector_id,
        )
        return result

    if kind == "MemberExpr":
        selector_id = context.add_reference(node, role_hint, path, member_token=True)
        result.update(
            node_kind="field",
            operator="arrow_member" if node.get("isArrow") else "dot_member",
            referenced_selector_id=selector_id,
            operands=[
                expression_from_ast(child, context, role_hint, f"{path}.{index}")
                for index, child in enumerate(children)
            ],
        )
        return result

    if kind in LITERAL_AST_KINDS:
        result.update(node_kind="literal", operator=kind, literal=literal_value(node))
        return result

    if kind in {"BinaryOperator", "CompoundAssignOperator"}:
        opcode = node.get("opcode")
        if not isinstance(opcode, str) or not opcode:
            context.unsupported[f"{kind}:missing_opcode"] += 1
            opcode = kind
        if opcode in COMPARISON_OPERATORS:
            result["node_kind"] = "comparison"
            child_roles = ["state", "bound"]
        elif opcode in BOOLEAN_BINARY_OPERATORS:
            result["node_kind"] = "boolean"
            child_roles = ["guard", "guard"]
        elif opcode in ARITHMETIC_OPERATORS or opcode in BITMASK_OPERATORS or opcode in ASSIGNMENT_OPERATORS:
            result["node_kind"] = "binary"
            child_roles = [role_hint, role_hint]
        elif opcode == ",":
            result["node_kind"] = "binary"
            child_roles = ["guard", role_hint]
        else:
            result["node_kind"] = "unknown"
            child_roles = ["guard"] * len(children)
            context.unsupported[f"{kind}:opcode:{opcode}"] += 1
        result["operator"] = opcode
        result["operands"] = [
            expression_from_ast(
                child,
                context,
                child_roles[index] if index < len(child_roles) else "guard",
                f"{path}.{index}",
            )
            for index, child in enumerate(children)
        ]
        if len(children) != 2:
            context.unsupported[f"{kind}:arity_{len(children)}"] += 1
        return result

    if kind == "UnaryOperator":
        opcode = node.get("opcode")
        if not isinstance(opcode, str) or not opcode:
            context.unsupported["UnaryOperator:missing_opcode"] += 1
            opcode = "UnaryOperator"
        result["node_kind"] = "boolean" if opcode == "!" else "unary"
        result["operator"] = opcode
        child_role = "guard" if opcode == "!" else role_hint
        result["operands"] = [
            expression_from_ast(child, context, child_role, f"{path}.{index}")
            for index, child in enumerate(children)
        ]
        if len(children) != 1:
            context.unsupported[f"UnaryOperator:arity_{len(children)}"] += 1
        return result

    if kind in {"ConditionalOperator", "BinaryConditionalOperator"}:
        result["node_kind"] = "conditional"
        result["operator"] = "?:"
        result["operands"] = [
            expression_from_ast(
                child,
                context,
                "guard" if index == 0 else role_hint,
                f"{path}.{index}",
            )
            for index, child in enumerate(children)
        ]
        if len(children) not in {2, 3}:
            context.unsupported[f"{kind}:arity_{len(children)}"] += 1
        return result

    if kind == "ArraySubscriptExpr":
        result["node_kind"] = "index"
        result["operator"] = "[]"
        result["operands"] = [
            expression_from_ast(
                child,
                context,
                role_hint if index == 0 else "guard",
                f"{path}.{index}",
            )
            for index, child in enumerate(children)
        ]
        if len(children) != 2:
            context.unsupported[f"ArraySubscriptExpr:arity_{len(children)}"] += 1
        return result

    if kind in {"CallExpr", "CXXMemberCallExpr", "CXXOperatorCallExpr"}:
        result["node_kind"] = "call"
        result["operator"] = kind
        result["operands"] = [
            expression_from_ast(child, context, role_hint, f"{path}.{index}")
            for index, child in enumerate(children)
        ]
        return result

    context.unsupported[f"ast_kind:{kind}"] += 1
    result["operator"] = kind
    result["operands"] = [
        expression_from_ast(child, context, "guard", f"{path}.{index}")
        for index, child in enumerate(children)
    ]
    return result


def initial_role(node: Mapping[str, Any]) -> str:
    current = node
    while str(current.get("kind")) in TRANSPARENT_AST_WRAPPERS | CAST_AST_KINDS:
        children = child_nodes(current)
        if len(children) != 1:
            break
        current = children[0]
    kind = current.get("kind")
    if kind == "BinaryOperator" and current.get("opcode") in BOOLEAN_BINARY_OPERATORS:
        return "guard"
    if kind in {"DeclRefExpr", "MemberExpr", "ArraySubscriptExpr"}:
        return "state"
    return "state"


def compiler_version(compiler: str) -> tuple[str, str]:
    resolved = shutil.which(compiler)
    if resolved is None:
        raise EnrichmentError(f"compiler not found: {compiler}")
    resolved_path = pathlib.Path(resolved).resolve()
    completed = subprocess.run([str(resolved_path), "--version"], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise EnrichmentError(f"cannot query compiler version: {completed.stderr.strip()}")
    first_line = completed.stdout.splitlines()[0] if completed.stdout.splitlines() else ""
    version_match = re.search(r"clang version\s+([0-9]+)", first_line)
    if not version_match or int(version_match.group(1)) != SUPPORTED_COMPILER_MAJOR:
        raise EnrichmentError(f"expected Clang {SUPPORTED_COMPILER_MAJOR}, observed: {first_line}")
    return str(resolved_path), completed.stdout.strip()


def sanitize_ast_arguments(arguments: Sequence[str], ap_id: str, compiler: str) -> list[str]:
    if not arguments:
        raise EnrichmentError("compile command has no arguments")
    retained: list[str] = []
    index = 1
    while index < len(arguments):
        argument = arguments[index]
        if argument == "-c":
            index += 1
            continue
        if argument == "-o":
            if index + 1 >= len(arguments):
                raise EnrichmentError("compile command ends after -o")
            index += 2
            continue
        if argument == "-fsyntax-only":
            index += 1
            continue
        retained.append(argument)
        index += 1
    return [
        compiler,
        *retained,
        "-Xclang",
        "-ast-dump=json",
        "-Xclang",
        f"-ast-dump-filter={ap_id}",
        "-fsyntax-only",
    ]


def source_location_selector(ap: Mapping[str, Any], selectors: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    candidates = [
        selectors[selector_id]
        for selector_id in ap.get("selector_refs", [])
        if selector_id in selectors and selectors[selector_id].get("kind") == "source_location"
    ]
    if len(candidates) != 1:
        raise EnrichmentError(
            f"AP {ap.get('ap_id')} must have exactly one public source-location selector; observed {len(candidates)}"
        )
    return candidates[0]


def same_path_hint(expected: Any, observed: Any) -> bool:
    if not isinstance(expected, str) or not expected or not isinstance(observed, str) or not observed:
        return False
    left = pathlib.PurePosixPath(expected.replace("\\", "/")).as_posix().lstrip("./")
    right = pathlib.PurePosixPath(observed.replace("\\", "/")).as_posix().lstrip("./")
    return left == right or right.endswith("/" + left) or left.endswith("/" + right)


def find_ap_var_decl(ast_values: Sequence[Any], ap_id: str, expected: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            if value.get("kind") == "VarDecl" and value.get("name") == ap_id:
                candidates.append(value)
            for child in value.get("inner", []) if isinstance(value.get("inner"), list) else []:
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(list(ast_values))
    expected_line = expected.get("line")
    expected_column = expected.get("column")
    expected_file = expected.get("file")
    exact = []
    for candidate in candidates:
        loc = normalized_point(candidate.get("loc") if isinstance(candidate.get("loc"), Mapping) else None)
        if (
            loc.get("line") == expected_line
            and loc.get("col") == expected_column
            and same_path_hint(expected_file, loc.get("file"))
        ):
            exact.append(candidate)
    if len(exact) != 1:
        observed = [
            {
                "line": normalized_point(item.get("loc") if isinstance(item.get("loc"), Mapping) else None).get("line"),
                "column": normalized_point(item.get("loc") if isinstance(item.get("loc"), Mapping) else None).get("col"),
                "file": normalized_point(item.get("loc") if isinstance(item.get("loc"), Mapping) else None).get("file"),
            }
            for item in candidates
        ]
        raise EnrichmentError(
            f"AP {ap_id} AST site mismatch: expected {expected_line}:{expected_column}, candidates={observed}"
        )
    return exact[0]


def language_for_source(source_path: str) -> str:
    return "c++" if pathlib.Path(source_path).suffix in {".cc", ".cpp", ".cxx", ".C"} else "c"


def resolve_compile_directory(compile_database_path: pathlib.Path, raw_directory: str) -> pathlib.Path:
    directory = pathlib.Path(raw_directory)
    if not directory.is_absolute():
        directory = compile_database_path.parent / directory
    return directory.resolve()


def enrich_case(
    frozen_root: pathlib.Path,
    case_entry: Mapping[str, Any],
    output_root: pathlib.Path,
    compiler: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_id = str(case_entry["case_id"])
    source_relative = str(case_entry["source"]["path"])
    property_relative = str(case_entry["property_ir"]["path"])
    compile_relative = str(case_entry["compile_database"]["path"])
    source_path = frozen_root / source_relative
    property_path = frozen_root / property_relative
    compile_path = frozen_root / compile_relative
    for path, expected_digest in (
        (source_path, case_entry["source"]["sha256"]),
        (property_path, case_entry["property_ir"]["sha256"]),
        (compile_path, case_entry["compile_database"]["sha256"]),
    ):
        observed = sha256_file(path)
        if observed != expected_digest:
            raise EnrichmentError(f"frozen input digest mismatch for {path}: {observed} != {expected_digest}")

    original_property = load_json(property_path)
    if original_property.get("schema_version") != "1.0.0":
        raise EnrichmentError(f"{case_id} input Property IR is not frozen schema 1.0.0")
    compile_commands = load_json(compile_path)
    if not isinstance(compile_commands, list) or len(compile_commands) != 1:
        raise EnrichmentError(f"{case_id} compile database must contain exactly one command")
    command_entry = compile_commands[0]
    arguments = command_entry.get("arguments")
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        raise EnrichmentError(f"{case_id} compile command must use a string arguments array")
    cwd = resolve_compile_directory(compile_path, str(command_entry.get("directory", "")))
    macros = compiler_macros(compiler, arguments, cwd, language_for_source(source_relative))
    facts = TargetTypeFacts.from_macros(macros)
    source = SourceBuffer.load(frozen_root, source_relative)

    enriched = copy.deepcopy(original_property)
    enriched["schema_version"] = PROPERTY_SCHEMA_VERSION
    enriched["artifact_id"] = stable_id(str(original_property["artifact_id"]), "m5", "typed_predicate")
    selector_list = enriched.get("selectors")
    if not isinstance(selector_list, list):
        raise EnrichmentError(f"{case_id} selectors must be an array")
    selectors_by_id: dict[str, MutableMapping[str, Any]] = {}
    for selector in selector_list:
        if not isinstance(selector, MutableMapping) or not isinstance(selector.get("selector_id"), str):
            raise EnrichmentError(f"{case_id} contains an invalid selector")
        selectors_by_id[selector["selector_id"]] = selector

    ap_records: list[dict[str, Any]] = []
    total_unsupported: Counter[str] = Counter()
    for ap in enriched.get("atomic_propositions", []):
        if not isinstance(ap, MutableMapping):
            raise EnrichmentError(f"{case_id} contains an invalid AP")
        ap_id = str(ap.get("ap_id"))
        site_selector = source_location_selector(ap, selectors_by_id)
        expected_location = site_selector.get("location")
        if not isinstance(expected_location, Mapping):
            raise EnrichmentError(f"{case_id}/{ap_id} site selector has no location")
        ast_command = sanitize_ast_arguments(arguments, ap_id, compiler)
        completed = subprocess.run(ast_command, cwd=cwd, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise EnrichmentError(
                f"Clang AST extraction failed for {case_id}/{ap_id} ({completed.returncode}): {completed.stderr.strip()}"
            )
        ast_values = decode_json_stream(completed.stdout)
        var_decl = find_ap_var_decl(ast_values, ap_id, expected_location)
        initializers = child_nodes(var_decl)
        context = ConversionContext(case_id=case_id, ap_id=ap_id, source=source, type_facts=facts)
        if len(initializers) != 1:
            context.unsupported[f"VarDecl:initializer_arity_{len(initializers)}"] += 1
            predicate = {
                "node_kind": "unknown",
                "operator": "missing_or_ambiguous_initializer",
                "value_type": value_type(var_decl, facts),
                "operands": [
                    expression_from_ast(item, context, "guard", f"root.{index}")
                    for index, item in enumerate(initializers)
                ],
            }
        else:
            predicate = expression_from_ast(initializers[0], context, initial_role(initializers[0]))

        old_selector_refs = list(ap.get("selector_refs", []))
        del ap["selector_refs"]
        ap["value_type"] = value_type(var_decl, facts)
        ap["predicate"] = predicate

        expression_selector_ids = [
            selector_id
            for selector_id in old_selector_refs
            if selector_id in selectors_by_id and selectors_by_id[selector_id].get("kind") == "expression_structure"
        ]
        if not expression_selector_ids:
            expression_selector_id = stable_id("sel", case_id, ap_id, "expression")
            expression_selector: MutableMapping[str, Any] = {
                "selector_id": expression_selector_id,
                "kind": "expression_structure",
                "expression_structure": copy.deepcopy(predicate),
            }
            selector_list.append(expression_selector)
            selectors_by_id[expression_selector_id] = expression_selector
            expression_selector_ids = [expression_selector_id]
        for selector_id in expression_selector_ids:
            selectors_by_id[selector_id]["expression_structure"] = copy.deepcopy(predicate)

        for reference in context.references:
            selector = {
                "selector_id": reference.selector_id,
                "kind": "source_location",
                "location": reference.location,
                "value_type": reference.value_type,
            }
            selector_list.append(selector)
            selectors_by_id[reference.selector_id] = selector

        original_roles = [str(role) for role in ap.get("roles", [])]
        inferred_roles = [reference.role for reference in context.references]
        ordered_roles: list[str] = []
        for role in [*original_roles, "state", "bound", "guard"]:
            if (role in original_roles or role in inferred_roles) and role not in ordered_roles:
                ordered_roles.append(role)
        ap["roles"] = ordered_roles
        groups: list[dict[str, Any]] = []
        site_selector_id = str(site_selector["selector_id"])
        for role in original_roles:
            groups.append(
                {
                    "group_id": stable_id("grp", case_id, ap_id, role, "ap_site"),
                    "role": role,
                    "all_of": [site_selector_id],
                }
            )
        for ordinal, reference in enumerate(context.references):
            groups.append(
                {
                    "group_id": stable_id("grp", case_id, ap_id, reference.role, f"ref{ordinal:03d}"),
                    "role": reference.role,
                    "all_of": [reference.selector_id],
                }
            )
        ap["role_selector_groups"] = groups

        total_unsupported.update(context.unsupported)
        ast_semantics = strip_process_specific_ast_ids(var_decl)
        ap_records.append(
            {
                "ap_id": ap_id,
                "site": copy.deepcopy(expected_location),
                "ast_semantic_sha256": sha256_bytes(canonical_json_bytes(ast_semantics)),
                "extraction_status": "SUPPORTED" if not context.unsupported else "UNKNOWN_UNSUPPORTED_AST",
                "unsupported_reasons": dict(sorted(context.unsupported.items())),
                "transparent_ast_wrappers": dict(sorted(context.transparent_wrappers.items())),
                "reference_count": len(context.references),
                "references": [
                    {
                        "selector_id": reference.selector_id,
                        "ast_kind": reference.ast_kind,
                        "role": reference.role,
                        "predicate_path": reference.predicate_path,
                        "location": reference.location,
                    }
                    for reference in context.references
                ],
                "role_mapping_contract": {
                    "comparison_operand_0": "state",
                    "comparison_operand_1": "bound",
                    "boolean_condition": "guard",
                    "semantic_threshold_confirmation": "NOT_CLAIMED",
                },
                "clang_arguments": ast_command[1:],
            }
        )

    enriched_path = output_root / "cases" / case_id / "property_ir.json"
    enriched_payload = pretty_json_bytes(enriched)
    atomic_write(enriched_path, enriched_payload)
    case_record = {
        "case_id": case_id,
        "language": case_entry.get("language"),
        "source": {"path": source_relative, "sha256": sha256_file(source_path)},
        "compile_database": {"path": compile_relative, "sha256": sha256_file(compile_path)},
        "original_property_ir": {"path": property_relative, "sha256": sha256_file(property_path)},
        "enriched_property_ir": {
            "path": enriched_path.relative_to(output_root).as_posix(),
            "sha256": sha256_bytes(enriched_payload),
        },
        "aps": ap_records,
        "fully_supported": not total_unsupported,
        "unsupported_reasons": dict(sorted(total_unsupported.items())),
    }
    return case_record, enriched


def verify_manifest_inputs(frozen_root: pathlib.Path, manifest: Mapping[str, Any]) -> None:
    for case in manifest.get("cases", []):
        for key in ("source", "property_ir", "compile_database"):
            record = case.get(key)
            if not isinstance(record, Mapping):
                raise EnrichmentError(f"manifest case {case.get('case_id')} is missing {key}")
            path = frozen_root / str(record.get("path"))
            observed = sha256_file(path)
            if observed != record.get("sha256"):
                raise EnrichmentError(f"frozen manifest digest mismatch: {path}")


def build_bundle(
    frozen_root: pathlib.Path,
    output_root: pathlib.Path,
    compiler_name: str,
    case_filter: set[str] | None = None,
) -> dict[str, Any]:
    frozen_root = frozen_root.resolve()
    output_root = output_root.resolve()
    if output_root == frozen_root or frozen_root in output_root.parents:
        raise EnrichmentError("output must not be placed inside the frozen M4 input")
    manifest_path = frozen_root / "manifest.json"
    frozen_manifest = load_json(manifest_path)
    if not isinstance(frozen_manifest, Mapping):
        raise EnrichmentError("frozen manifest root must be an object")
    verify_manifest_inputs(frozen_root, frozen_manifest)
    before_tree = tree_digest(frozen_root)
    compiler, version = compiler_version(compiler_name)
    tool_path = pathlib.Path(__file__).resolve()
    tool_digest = sha256_file(tool_path)
    cases = [
        case
        for case in frozen_manifest.get("cases", [])
        if case_filter is None or case.get("case_id") in case_filter
    ]
    if case_filter is not None:
        observed = {str(case.get("case_id")) for case in cases}
        missing = sorted(case_filter - observed)
        if missing:
            raise EnrichmentError(f"requested cases are absent from frozen manifest: {missing}")

    case_records: list[dict[str, Any]] = []
    unsupported = Counter()
    supported_aps = 0
    total_aps = 0
    for case in cases:
        record, _ = enrich_case(frozen_root, case, output_root, compiler)
        case_records.append(record)
        unsupported.update(record["unsupported_reasons"])
        for ap in record["aps"]:
            total_aps += 1
            if ap["extraction_status"] == "SUPPORTED":
                supported_aps += 1

    after_tree = tree_digest(frozen_root)
    if before_tree != after_tree:
        raise EnrichmentError(
            f"frozen input changed during enrichment: before={before_tree}, after={after_tree}"
        )
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "rift.m5.micro.typed_predicate_enrichment",
        "generator": {
            "tool": "enrich_property_ir.py",
            "tool_version": TOOL_VERSION,
            "tool_sha256": tool_digest,
            "clang_executable": compiler,
            "clang_executable_sha256": sha256_file(pathlib.Path(compiler)),
            "clang_version": version,
            "ast_format": "clang-18-json",
            "process_specific_ast_ids_excluded_from_digest": True,
        },
        "source_bundle": {
            "root_hint": "benchmark/rift/m4/micro/frozen",
            "manifest_sha256": sha256_file(manifest_path),
            "tree_sha256_before": before_tree,
            "tree_sha256_after": after_tree,
            "frozen_unchanged": True,
        },
        "knowledge_boundary": {
            "inputs": ["public source", "public Property IR AP id/location", "Clang 18 AST JSON"],
            "description_text_used_for_predicate_extraction": False,
            "gold_mutation_answers_used": False,
            "comparison_role_mapping": "STRUCTURAL_CANDIDATE_ONLY",
            "semantic_threshold_confirmation": "NOT_CLAIMED",
        },
        "cases": case_records,
        "summary": {
            "case_count": len(case_records),
            "ap_count": total_aps,
            "fully_supported_case_count": sum(1 for case in case_records if case["fully_supported"]),
            "fully_supported_ap_count": supported_aps,
            "unsupported_reason_distribution": dict(sorted(unsupported.items())),
        },
    }
    atomic_write(output_root / "manifest.json", pretty_json_bytes(bundle))
    return bundle


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    script_root = pathlib.Path(__file__).resolve().parent
    workspace_root = script_root.parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frozen-root",
        type=pathlib.Path,
        default=workspace_root / "benchmark/rift/m4/micro/frozen",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=script_root / "bundle",
    )
    parser.add_argument("--clang", default="clang-18")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--summary-output", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if argv is None else argv)
    try:
        bundle = build_bundle(
            options.frozen_root,
            options.output_dir,
            options.clang,
            set(options.cases) if options.cases else None,
        )
        if options.summary_output:
            result = {
                "schema_version": SCHEMA_VERSION,
                "artifact_id": "rift.m5.micro.typed_predicate_enrichment.result",
                "bundle_manifest": {
                    "path": (options.output_dir.resolve() / "manifest.json").as_posix(),
                    "sha256": sha256_file(options.output_dir.resolve() / "manifest.json"),
                },
                "summary": bundle["summary"],
                "frozen_unchanged": bundle["source_bundle"]["frozen_unchanged"],
                "knowledge_boundary": bundle["knowledge_boundary"],
            }
            atomic_write(options.summary_output.resolve(), pretty_json_bytes(result))
        summary = bundle["summary"]
        print(
            "PASS typed-predicate-enrichment "
            f"cases={summary['case_count']} aps={summary['ap_count']} "
            f"supported_aps={summary['fully_supported_ap_count']} "
            f"unsupported={sum(summary['unsupported_reason_distribution'].values())} "
            f"output={options.output_dir.resolve()}"
        )
        return 0
    except (EnrichmentError, OSError) as error:
        print(f"FAIL typed-predicate-enrichment: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
