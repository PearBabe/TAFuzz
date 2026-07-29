#!/usr/bin/env python3
"""Shared, truth-free support for the RIFT-M4 synthetic acceptance bundle.

This module deliberately knows only about compiler commands, source text, and
the production artifact schemas.  Private relation labels are loaded solely by
``evaluate.py`` after a sealed analyzer run has passed all public checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

import jsonschema


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
DEFAULT_CORPUS = WORKSPACE / "benchmark" / "rift" / "gold"
PRODUCTION_SCHEMA_DIR = WORKSPACE / "src" / "StaticAnalysis" / "schema"
LOCAL_SCHEMA_DIR = HERE / "schemas"
SCHEMA_MIGRATION_LEDGER = HERE / "schema_migration_ledger.json"

PRODUCTION_SCHEMA_FILES = (
    "common.schema.json",
    "typed_property_ir.schema.json",
    "semantic_index.schema.json",
    "ap_bindings.schema.json",
    "contextual_influence_graph.schema.json",
    "ap_influence_cones.schema.json",
    "analysis_certificate.schema.json",
    "model_pack.schema.json",
)

HEADER_PATTERN = re.compile(r"\A/\*.*?\*/\n", re.DOTALL)
PUBLIC_HEADER = """/*
 * Opaque RIFT-M4 synthetic input {case_id}.
 * Evaluation metadata is intentionally excluded.
 * Property locations are supplied separately in typed Property IR.
 */
"""
MARKER_PATTERN = re.compile(r"RIFT_(SOURCE|NODE|AP):([a-z][a-z0-9_]*)")
AP_MARKER_PATTERN = re.compile(r"RIFT_AP:([a-z][a-z0-9_]*)")
IDENTIFIER_BOUNDARY = r"(?<![A-Za-z0-9_]){token}(?![A-Za-z0-9_])"

# These tokens encode the generator's answers or case strata.  They are
# forbidden only in analyzer-visible generated artifacts, not in evaluator
# source code or in the private corpus.
FORBIDDEN_VISIBLE_PATTERNS = (
    re.compile(r"RIFT-GOLD-[0-9]{3}", re.IGNORECASE),
    re.compile(r"\b(?:MUST_INFLUENCE|MAY_INFLUENCE|NO_INFLUENCE)\b", re.IGNORECASE),
    re.compile(r"\b(?:must|may|negative)_v[0-9]+\b", re.IGNORECASE),
    re.compile(
        r"\b(?:direct_data|indirect_data|control_only|alias_object_field|"
        r"config_threshold|message_parser_state|async_timer_callback_queue|"
        r"setup_mode_prerequisite|timing_drop_repeat_reorder|"
        r"uncontrollable_false_correlation|one_input_multi_ap|joint_inputs)\b",
        re.IGNORECASE,
    ),
)


class AcceptanceError(ValueError):
    """Raised when a frozen input or analyzer result violates the contract."""


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_named_files(paths: Iterable[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        name = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def production_schema_tree_sha256() -> str:
    """Hash the complete active schema tree with stable, root-relative names.

    This is intentionally independent of the schema snapshot recorded in a
    prepared input manifest.  The latter freezes what the analyzer was given;
    this digest seals the active output contract used to validate a run.
    """
    paths = sorted(path for path in PRODUCTION_SCHEMA_DIR.rglob("*") if path.is_file())
    expected = {PRODUCTION_SCHEMA_DIR / name for name in PRODUCTION_SCHEMA_FILES}
    if set(paths) != expected:
        extra = sorted(path.relative_to(PRODUCTION_SCHEMA_DIR).as_posix() for path in set(paths) - expected)
        missing = sorted(path.relative_to(PRODUCTION_SCHEMA_DIR).as_posix() for path in expected - set(paths))
        raise AcceptanceError(
            f"active production schema tree differs from declared contract; "
            f"extra={extra} missing={missing}"
        )
    # Match scripts/generate_embedded_manifest.py: names are relative to the
    # StaticAnalysis source root (for example ``schema/common.schema.json``).
    return sha256_named_files(paths, PRODUCTION_SCHEMA_DIR.parent)


def stable_file(path: str | Path) -> str:
    return Path(path).as_posix()


def assert_no_answer_tokens(text: str, label: str) -> None:
    for pattern in FORBIDDEN_VISIBLE_PATTERNS:
        match = pattern.search(text)
        if match:
            raise AcceptanceError(
                f"analyzer-visible {label} leaks answer token {match.group(0)!r}"
            )


def schema_store() -> dict[str, dict[str, Any]]:
    store: dict[str, dict[str, Any]] = {}
    paths = [PRODUCTION_SCHEMA_DIR / name for name in PRODUCTION_SCHEMA_FILES]
    paths.extend(sorted(LOCAL_SCHEMA_DIR.glob("*.schema.json")))
    for path in paths:
        schema = read_json(path)
        jsonschema.Draft7Validator.check_schema(schema)
        identifier = schema.get("$id")
        if identifier:
            store[str(identifier)] = schema
    return store


def validate_schema(instance: Any, schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    store = schema_store()
    resolver = jsonschema.RefResolver.from_schema(schema, store=store)
    try:
        jsonschema.Draft7Validator(schema, resolver=resolver).validate(instance)
    except jsonschema.ValidationError as error:
        location = "/".join(str(item) for item in error.absolute_path)
        raise AcceptanceError(
            f"{label} schema error at {location or '<root>'}: {error.message}"
        ) from error


def sanitize_source(text: str, case_id: str) -> str:
    header = HEADER_PATTERN.match(text)
    if header is None:
        raise AcceptanceError("synthetic source lacks its generated header")
    replacement = PUBLIC_HEADER.format(case_id=case_id)
    if header.group(0).count("\n") != replacement.count("\n"):
        raise AcceptanceError("public header would change source line locations")
    sanitized = replacement + text[header.end() :]
    private_identifiers = sorted(
        {
            identifier
            for kind, identifier in MARKER_PATTERN.findall(sanitized)
            if kind in {"SOURCE", "NODE"}
        },
        key=lambda item: (-len(item), item),
    )
    sanitized = re.sub(
        r"/\*\s*RIFT_(?:SOURCE|NODE):[a-z][a-z0-9_]*\s*\*/",
        "/* public declaration */",
        sanitized,
    )
    for identifier in private_identifiers:
        if len(identifier) < 3:
            raise AcceptanceError(f"cannot anonymize short private identifier {identifier}")
        replacement_identifier = "v_" + hashlib.sha256(
            f"{case_id}:{identifier}".encode("utf-8")
        ).hexdigest()[: len(identifier) - 2]
        if re.search(
            IDENTIFIER_BOUNDARY.format(token=re.escape(replacement_identifier)),
            sanitized,
        ):
            raise AcceptanceError("deterministic private identifier collides with source")
        sanitized = re.sub(
            IDENTIFIER_BOUNDARY.format(token=re.escape(identifier)),
            replacement_identifier,
            sanitized,
        )
    if "RIFT_AP:" not in sanitized:
        raise AcceptanceError("source has no public AP marker")
    if "RIFT_SOURCE:" in sanitized or "RIFT_NODE:" in sanitized:
        raise AcceptanceError("private source/node marker survived sanitization")
    assert_no_answer_tokens(sanitized, f"source {case_id}")
    return sanitized


def strip_ap_markers(source: str) -> str:
    public = re.sub(
        r"/\*\s*RIFT_AP:[a-z][a-z0-9_]*\s*\*/",
        "/* public property declaration */",
        source,
    )
    if re.search(r"RIFT_(?:SOURCE|NODE|AP):", public):
        raise AcceptanceError("generator marker survived analyzer-visible sanitization")
    return public


def _resolve_command_file(command: dict[str, Any]) -> Path:
    source = Path(str(command["file"]))
    if not source.is_absolute():
        source = Path(str(command["directory"])) / source
    return source.resolve()


def discover_source_records(corpus_root: Path) -> list[dict[str, Any]]:
    """Discover cases without opening the corpus manifest or private labels."""
    corpus_root = corpus_root.resolve()
    commands = read_json(corpus_root / "compile_commands.json")
    if not isinstance(commands, list) or not commands:
        raise AcceptanceError("compile_commands.json must be a non-empty array")
    by_source: dict[Path, dict[str, Any]] = {}
    for command in commands:
        if not isinstance(command, dict):
            raise AcceptanceError("compile command entry is not an object")
        source = _resolve_command_file(command)
        if source in by_source:
            raise AcceptanceError(f"duplicate compile command for {source}")
        by_source[source] = command

    source_dir = corpus_root / "cases"
    source_paths = sorted(
        path.resolve()
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix in {".c", ".cpp"}
    )
    if len(source_paths) != len(by_source):
        raise AcceptanceError(
            f"source/compile-command count mismatch: {len(source_paths)} != {len(by_source)}"
        )

    records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for path in source_paths:
        command = by_source.get(path)
        if command is None:
            raise AcceptanceError(f"missing compile command for {path}")
        digest = sha256_file(path)
        if digest in seen_hashes:
            raise AcceptanceError("source hashes must be unique for opaque ordering")
        seen_hashes.add(digest)
        records.append(
            {
                "original_path": path,
                "original_sha256": digest,
                "source_text": path.read_text(encoding="utf-8"),
                "compile_command": command,
            }
        )

    records.sort(key=lambda item: (item["original_sha256"], item["original_path"].name))
    for index, record in enumerate(records, start=1):
        record["case_id"] = f"case_{index:03d}"
    return records


def rewrite_compile_command(
    original: dict[str, Any], original_source: Path, relative_source: str, relative_object: str
) -> dict[str, Any]:
    arguments = original.get("arguments")
    if not isinstance(arguments, list) or not arguments:
        raise AcceptanceError("compile command requires an arguments array")
    rewritten: list[str] = []
    source_replacements = 0
    output_replacements = 0
    index = 0
    while index < len(arguments):
        argument = str(arguments[index])
        if argument == "-o":
            if index + 1 >= len(arguments):
                raise AcceptanceError("compile command ends after -o")
            rewritten.extend(["-o", relative_object])
            output_replacements += 1
            index += 2
            continue
        candidate = Path(argument)
        matches_source = False
        if candidate.is_absolute():
            matches_source = candidate.resolve() == original_source.resolve()
        elif argument in {original_source.name, str(original_source)}:
            matches_source = True
        if matches_source:
            rewritten.append(relative_source)
            source_replacements += 1
        else:
            assert_no_answer_tokens(argument, "compile argument")
            rewritten.append(argument)
        index += 1
    if source_replacements != 1 or output_replacements != 1:
        raise AcceptanceError(
            "compile rewrite requires exactly one source and one -o target; "
            f"got {source_replacements}/{output_replacements}"
        )
    return {"directory": ".", "file": relative_source, "arguments": rewritten}


def _source_value_type(type_text: str) -> dict[str, Any]:
    normalized = " ".join(type_text.split())
    if normalized in {"bool", "_Bool"}:
        return {"kind": "bool", "canonical": normalized, "bit_width": 1, "signed": False}
    if normalized in {"float", "double", "long double"}:
        return {"kind": "floating", "canonical": normalized}
    if normalized in {"int", "signed", "signed int"}:
        return {"kind": "integer", "canonical": "int", "bit_width": 32, "signed": True}
    if normalized.startswith("unsigned"):
        return {"kind": "integer", "canonical": normalized, "bit_width": 32, "signed": False}
    return {"kind": "unknown", "canonical": normalized or "unknown"}


def expression_structure(expression: str, value_type: dict[str, Any]) -> dict[str, Any]:
    stripped = expression.strip()
    node_kind = "unknown"
    operator: str | None = None
    for candidate in ("||", "&&"):
        if candidate in stripped:
            node_kind, operator = "boolean", candidate
            break
    if operator is None:
        comparison = re.search(r"(?:==|!=|>=|<=|>|<)", stripped)
        if comparison:
            node_kind, operator = "comparison", comparison.group(0)
    if operator is None:
        binary = re.search(r"(?:<<|>>|[+\-*/%&|^])", stripped)
        if binary:
            node_kind, operator = "binary", binary.group(0)
    if operator is None and stripped.startswith("!"):
        node_kind, operator = "unary", "!"
    if operator is None and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stripped):
        node_kind, operator = "reference", "source-reference"
    if operator is None and re.fullmatch(r"[-+]?[0-9]+", stripped):
        node_kind, operator = "literal", "integer-literal"
    if operator is None and re.search(r"[A-Za-z_][A-Za-z0-9_]*\s*\(", stripped):
        node_kind, operator = "call", "call-expression"
    return {
        "node_kind": node_kind,
        "operator": operator or f"source-expression:{stripped}",
        "value_type": value_type,
        "operands": [],
    }


def discover_ap_declarations(
    source: str,
    relative_source: str,
    known_ap_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    lines = source.splitlines()
    declarations: list[dict[str, Any]] = []
    targets: list[tuple[str, range]] = []
    if known_ap_ids is None:
        seen: set[str] = set()
        for marker_index, line in enumerate(lines):
            marker = AP_MARKER_PATTERN.search(line)
            if marker is None:
                continue
            ap_id = marker.group(1)
            if ap_id in seen:
                raise AcceptanceError(f"duplicate AP marker {ap_id}")
            seen.add(ap_id)
            targets.append(
                (ap_id, range(marker_index + 1, min(marker_index + 6, len(lines))))
            )
    else:
        if not known_ap_ids or len(known_ap_ids) != len(set(known_ap_ids)):
            raise AcceptanceError("known AP IDs are absent or duplicated")
        targets = [(ap_id, range(len(lines))) for ap_id in known_ap_ids]

    for ap_id, candidate_lines in targets:
        token_pattern = re.compile(
            IDENTIFIER_BOUNDARY.format(token=re.escape(ap_id))
        )
        found_values: list[dict[str, Any]] = []
        for declaration_index in candidate_lines:
            declaration_line = lines[declaration_index]
            token = token_pattern.search(declaration_line)
            if token is None:
                continue
            declaration = re.search(
                rf"\b(?P<type>bool|_Bool|int|signed(?:\s+int)?|unsigned(?:\s+int)?|"
                rf"float|double|long\s+double)\s+{re.escape(ap_id)}\s*=\s*(?P<expr>.*);\s*$",
                declaration_line,
            )
            if declaration is None:
                if known_ap_ids is not None:
                    continue
                raise AcceptanceError(
                    f"unsupported public AP declaration after marker {ap_id}: {declaration_line}"
                )
            value_type = _source_value_type(declaration.group("type"))
            expression = declaration.group("expr").strip()
            structure = expression_structure(expression, value_type)
            found_values.append({
                "ap_id": ap_id,
                "location": {
                    "file": relative_source,
                    "line": declaration_index + 1,
                    "column": token.start() + 1,
                    "location_kind": "spelling",
                },
                "value_type": value_type,
                "expression": expression,
                "structure": structure,
                "role": "guard"
                if structure["node_kind"] in {"comparison", "boolean"}
                else "state",
            })
            if known_ap_ids is None:
                break
        if not found_values:
            raise AcceptanceError(f"could not locate AP declaration for {ap_id}")
        if len(found_values) != 1:
            raise AcceptanceError(f"AP declaration is ambiguous for {ap_id}")
        declarations.append(found_values[0])
    if not declarations:
        raise AcceptanceError("no AP declarations discovered")
    return declarations


def build_property_ir(
    case_id: str,
    source: str,
    relative_source: str,
    known_ap_ids: list[str] | None = None,
) -> dict[str, Any]:
    declarations = discover_ap_declarations(source, relative_source, known_ap_ids)
    selectors: list[dict[str, Any]] = []
    aps: list[dict[str, Any]] = []
    atoms: list[dict[str, Any]] = []
    formula_terms: list[str] = []
    for declaration in declarations:
        ap_id = declaration["ap_id"]
        location_selector = f"sel.{case_id}.{ap_id}.location"
        expression_selector = f"sel.{case_id}.{ap_id}.expression"
        selectors.extend(
            [
                {
                    "selector_id": location_selector,
                    "kind": "source_location",
                    "location": declaration["location"],
                },
                {
                    "selector_id": expression_selector,
                    "kind": "expression_structure",
                    "expression_structure": declaration["structure"],
                },
            ]
        )
        aps.append(
            {
                "ap_id": ap_id,
                "roles": [declaration["role"]],
                "value_type": declaration["value_type"],
                "predicate": declaration["structure"],
                "selector_refs": [location_selector, expression_selector],
                "description": f"public source declaration: {ap_id} = {declaration['expression']}",
            }
        )
        atoms.append(
            {
                "node_id": f"formula.{case_id}.{ap_id}",
                "operator": "atom",
                "ap_ref": ap_id,
                "operands": [],
            }
        )
        formula_terms.append(f"{ap_id} := ({declaration['expression']})")
    formula = atoms[0]
    if len(atoms) > 1:
        formula = {
            "node_id": f"formula.{case_id}.root",
            "operator": "and",
            "operands": atoms,
        }
    return {
        "schema_version": "1.0.0",
        "artifact_id": f"artifact.property.{case_id}",
        "property_id": f"property.{case_id}",
        "logic": "MITL",
        "time_domain": "dense",
        "formula_text": " and ".join(formula_terms),
        "formula": formula,
        "atomic_propositions": aps,
        "selectors": selectors,
    }


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def prepare_bundle(
    corpus_root: Path, output: Path, private_oracle_commitment_sha256: str
) -> dict[str, Any]:
    """Create a deterministic analyzer-visible bundle without private answers."""
    corpus_root = corpus_root.resolve()
    output = output.resolve()
    if not re.fullmatch(r"[0-9a-f]{64}", private_oracle_commitment_sha256):
        raise AcceptanceError("private oracle commitment must be a lowercase SHA-256")
    if output.exists():
        raise AcceptanceError(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    completed = False
    try:
        records = discover_source_records(corpus_root)
        global_commands: list[dict[str, Any]] = []
        cases: list[dict[str, Any]] = []
        ap_count = 0
        for record in records:
            case_id = record["case_id"]
            extension = record["original_path"].suffix
            relative_source = f"sources/{case_id}{extension}"
            relative_object = f"build/{case_id}.o"
            marked_source = sanitize_source(record["source_text"], case_id)
            global_command = rewrite_compile_command(
                record["compile_command"],
                record["original_path"],
                relative_source,
                relative_object,
            )
            case_command = {**global_command, "directory": "../.."}
            property_ir = build_property_ir(case_id, marked_source, relative_source)
            source = strip_ap_markers(marked_source)
            validate_schema(
                property_ir,
                PRODUCTION_SCHEMA_DIR / "typed_property_ir.schema.json",
                f"typed property {case_id}",
            )
            property_path = staging / "cases" / case_id / "property_ir.json"
            compile_path = staging / "cases" / case_id / "compile_commands.json"
            source_path = staging / relative_source
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(source, encoding="utf-8")
            write_json(property_path, property_ir)
            write_json(compile_path, [case_command])
            global_commands.append(global_command)
            case_ap_count = len(property_ir["atomic_propositions"])
            ap_count += case_ap_count
            cases.append(
                {
                    "case_id": case_id,
                    "language": "c++" if extension == ".cpp" else "c",
                    "source": {
                        "path": relative_source,
                        "sha256": sha256_file(source_path),
                    },
                    "compile_database": {
                        "path": _relative(compile_path, staging),
                        "sha256": sha256_file(compile_path),
                    },
                    "property_ir": {
                        "path": _relative(property_path, staging),
                        "sha256": sha256_file(property_path),
                    },
                    "ap_count": case_ap_count,
                }
            )

        global_compile_path = staging / "compile_commands.json"
        write_json(global_compile_path, global_commands)
        (staging / "build").mkdir(parents=True, exist_ok=True)

        production_schemas = []
        for name in PRODUCTION_SCHEMA_FILES:
            path = PRODUCTION_SCHEMA_DIR / name
            schema = read_json(path)
            production_schemas.append(
                {
                    "name": name,
                    "schema_id": schema["$id"],
                    "path": path.relative_to(WORKSPACE).as_posix(),
                    "sha256": sha256_file(path),
                }
            )
        manifest = {
            "schema_version": "rift.m4.micro-input.v1",
            "corpus_kind": "SYNTHETIC_MECHANICAL_SOURCE_CORPUS",
            "human_labels_required": False,
            "answer_access_policy": "PRE_ANALYSIS_SOURCE_AND_BUILD_METADATA_ONLY",
            "private_oracle_commitment_sha256": private_oracle_commitment_sha256,
            "case_count": len(cases),
            "ap_count": ap_count,
            "global_compile_database": {
                "path": "compile_commands.json",
                "sha256": sha256_file(global_compile_path),
            },
            "production_schemas": production_schemas,
            "cases": cases,
        }
        validate_schema(
            manifest,
            LOCAL_SCHEMA_DIR / "analyzer_input_manifest.schema.json",
            "analyzer input manifest",
        )
        manifest_text = canonical_json(manifest).decode("utf-8")
        assert_no_answer_tokens(manifest_text, "manifest")
        assert_no_answer_tokens(
            global_compile_path.read_text(encoding="utf-8"), "global compile database"
        )
        write_json(staging / "manifest.json", manifest)
        os.replace(staging, output)
        completed = True
        return manifest
    finally:
        if not completed and staging.exists():
            print(f"PARTIAL staging retained at {staging}")


def artifact_entry(root: Path, relative_path: str) -> dict[str, str]:
    path = root / relative_path
    return {"path": relative_path, "sha256": sha256_file(path)}


def unique_by(items: Iterable[dict[str, Any]], field: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item[field])
        if key in result:
            raise AcceptanceError(f"duplicate {label}: {key}")
        result[key] = item
    return result


def location_matches(candidate: dict[str, Any], expected: dict[str, Any]) -> bool:
    candidate_file = Path(str(candidate["file"])).as_posix()
    expected_file = Path(str(expected["file"])).as_posix()
    files_match = (
        candidate_file == expected_file
        or candidate_file.endswith("/" + expected_file)
        or expected_file.endswith("/" + candidate_file)
    )
    if not files_match:
        return False
    return (
        int(candidate["line"]) == int(expected["line"])
        and int(candidate["column"]) == int(expected["column"])
    )
