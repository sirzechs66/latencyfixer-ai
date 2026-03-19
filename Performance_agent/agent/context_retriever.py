"""
Context Retriever Module for LatencyFixer AI.

Implements dependency-aware context retrieval that extracts only relevant
code based on error logs, stack traces, and import relationships.

This avoids passing the entire codebase to the LLM by:
1. Parsing logs to extract file/function names
2. Building a shallow dependency graph (depth 1-2 max)
3. Including only directly imported modules and caller/callee relationships
"""

import re
import ast
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

from .state import AgentState, ExtractedEntity, DependencyContext


@dataclass
class FileEntity:
    """Represents a parsed file entity."""
    file_path: str
    content: str
    functions: List[str]
    async_functions: List[str]
    imports: List[str]
    classes: List[str]
    class_methods: Dict[str, List[str]]  # class_name -> [methods]
    decorators: Dict[str, List[str]]  # function_name -> [decorators]
    line_markers: Dict[int, str]  # line_number -> code snippet


class ContextRetriever:
    """
    Dependency-aware context retriever.

    Extracts relevant code context from logs and stack traces without
    requiring the full codebase as input.
    """

    # Regex patterns for entity extraction
    PATTERNS = {
        "file_path": r"[/\\]?(?:[\w.-]+[/\\])+[\w.-]+\.py",
        "function_call": r"(\w+)\s*\(",
        "stack_trace_line": r"File\s+\"([^\"]+)\",\s+line\s+(\d+),\s+in\s+(\w+)",
        "error_location": r"in\s+(\w+)\s+at\s+([^\s:]+):(\d+)",
        "import_statement": r"(?:from\s+([\w.]+)\s+)?import\s+([\w.]+)",
        "module_reference": r"module\s+['\"]?([\w.]+)['\"]?",
        # Extended patterns for better retrieval
        "class_method": r"(\w+)\.(\w+)\s*\(",  # obj.method() calls
        "async_function": r"async\s+def\s+(\w+)",
        "decorator": r"@(\w+)",
        "database_query": r"(?:SELECT|INSERT|UPDATE|DELETE|QUERY).*?(?:FROM|INTO|WHERE|VALUES)",
        "http_request": r"(?:GET|POST|PUT|DELETE|PATCH)\s+['\"]?(/[\w./-]+)",
        "log_level": r"(?:ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL|FATAL)",
        "exception_type": r"(\w+Error|\w+Exception|\w+Interrupt):",
        "line_reference": r"line\s+(\d+)",
        "relative_import": r"from\s+\.+(\w*)",
    }

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the context retriever.

        Args:
            base_path: Base directory for code search. Defaults to current dir.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._file_cache: Dict[str, FileEntity] = {}

    def extract_entities(self, logs: List[str]) -> List[ExtractedEntity]:
        """
        Extract entities (files, functions, modules, classes, methods) from logs.

        Args:
            logs: List of log strings, stack traces, error messages

        Returns:
            List of extracted entities with type, name, source, confidence
        """
        entities = []
        builtin_funcs = {'print', 'len', 'str', 'int', 'float',
                         'list', 'dict', 'set', 'range', 'open',
                         'sum', 'min', 'max', 'abs', 'round', 'zip'}

        for log_idx, log in enumerate(logs):
            # Extract stack trace entries
            stack_matches = re.findall(
                self.PATTERNS["stack_trace_line"],
                log,
                re.MULTILINE
            )
            for file_path, line_num, func_name in stack_matches:
                entities.append(ExtractedEntity(
                    entity_type="file",
                    name=file_path,
                    source=f"log_{log_idx}",
                    line_number=int(line_num),
                    confidence=0.95
                ))
                entities.append(ExtractedEntity(
                    entity_type="function",
                    name=func_name,
                    source=f"log_{log_idx}",
                    line_number=int(line_num),
                    confidence=0.9
                ))

            # Extract file paths
            file_matches = re.findall(
                self.PATTERNS["file_path"],
                log
            )
            for file_path in file_matches:
                # Avoid duplicates from stack traces
                if not any(e.name == file_path and e.entity_type == "file"
                          for e in entities):
                    entities.append(ExtractedEntity(
                        entity_type="file",
                        name=file_path,
                        source=f"log_{log_idx}",
                        confidence=0.85
                    ))

            # Extract class.method() calls
            method_matches = re.findall(
                self.PATTERNS["class_method"],
                log
            )
            for class_name, method_name in method_matches:
                if class_name.lower() not in ['the', 'a', 'an', 'this']:
                    entities.append(ExtractedEntity(
                        entity_type="class",
                        name=class_name,
                        source=f"log_{log_idx}",
                        confidence=0.75
                    ))
                    entities.append(ExtractedEntity(
                        entity_type="method",
                        name=f"{class_name}.{method_name}",
                        source=f"log_{log_idx}",
                        confidence=0.8
                    ))

            # Extract function calls (exclude builtins)
            func_matches = re.findall(
                self.PATTERNS["function_call"],
                log
            )
            for func_name in func_matches:
                if func_name not in builtin_funcs:
                    entities.append(ExtractedEntity(
                        entity_type="function",
                        name=func_name,
                        source=f"log_{log_idx}",
                        confidence=0.7
                    ))

            # Extract exception types
            exception_matches = re.findall(
                self.PATTERNS["exception_type"],
                log
            )
            for exc_type in exception_matches:
                entities.append(ExtractedEntity(
                    entity_type="exception",
                    name=exc_type,
                    source=f"log_{log_idx}",
                    confidence=0.9
                ))

            # Extract database queries
            query_matches = re.findall(
                self.PATTERNS["database_query"],
                log
            )
            for query in query_matches:
                entities.append(ExtractedEntity(
                    entity_type="query",
                    name=query[:50],  # Truncate long queries
                    source=f"log_{log_idx}",
                    confidence=0.85
                ))

            # Extract HTTP endpoints
            http_matches = re.findall(
                self.PATTERNS["http_request"],
                log
            )
            for endpoint in http_matches:
                entities.append(ExtractedEntity(
                    entity_type="endpoint",
                    name=endpoint,
                    source=f"log_{log_idx}",
                    confidence=0.85
                ))

            # Extract line references
            line_matches = re.findall(
                self.PATTERNS["line_reference"],
                log
            )
            for line_num in line_matches:
                # Try to associate with nearby file
                entities.append(ExtractedEntity(
                    entity_type="line",
                    name=line_num,
                    source=f"log_{log_idx}",
                    confidence=0.6
                ))

        return entities

    def parse_file(self, file_path: str) -> Optional[FileEntity]:
        """
        Parse a Python file to extract its structure.

        Args:
            file_path: Path to the Python file

        Returns:
            FileEntity with functions, imports, classes, async functions, methods
        """
        if file_path in self._file_cache:
            return self._file_cache[file_path]

        # Try to resolve the file
        full_path = self.base_path / file_path
        if not full_path.exists():
            # Try as absolute path
            full_path = Path(file_path)
            if not full_path.exists():
                return None

        try:
            content = full_path.read_text(encoding='utf-8')
        except Exception:
            return None

        functions = []
        async_functions = []
        imports = []
        classes = []
        class_methods = {}
        decorators = {}
        line_markers = {}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                    # Collect decorators
                    decorators[node.name] = [
                        d.id if isinstance(d, ast.Name) else str(d)
                        for d in node.decorator_list
                    ]
                    # Store line marker
                    line_markers[node.lineno] = f"def {node.name}()"
                elif isinstance(node, ast.AsyncFunctionDef):
                    async_functions.append(node.name)
                    decorators[node.name] = [
                        d.id if isinstance(d, ast.Name) else str(d)
                        for d in node.decorator_list
                    ]
                    line_markers[node.lineno] = f"async def {node.name}()"
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    # Extract methods
                    class_methods[node.name] = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            class_methods[node.name].append(item.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                    # Handle relative imports
                    if node.level > 0:
                        imports.append(f".{'.' * (node.level - 1)}{node.module or ''}")
        except SyntaxError:
            # Fallback to regex-based parsing
            import_matches = re.findall(
                self.PATTERNS["import_statement"],
                content
            )
            for match in import_matches:
                if match[0]:
                    imports.append(match[0])
                imports.append(match[1])

            # Relative imports
            rel_matches = re.findall(
                self.PATTERNS["relative_import"],
                content
            )
            for match in rel_matches:
                imports.append(f".{match}")

            func_matches = re.findall(
                r'def\s+(\w+)\s*\(',
                content
            )
            functions.extend(func_matches)

            async_func_matches = re.findall(
                self.PATTERNS["async_function"],
                content
            )
            async_functions.extend(async_func_matches)

            class_matches = re.findall(
                r'class\s+(\w+)',
                content
            )
            classes.extend(class_matches)

            # Extract decorators
            decorator_matches = re.findall(
                self.PATTERNS["decorator"],
                content
            )
            decorators["module_level"] = decorator_matches

            # Class methods
            for cls in classes:
                method_matches = re.findall(
                    rf"def\s+(\w+)\s*\(\s*self[,\)]",
                    content
                )
                class_methods[cls] = method_matches

        entity = FileEntity(
            file_path=str(file_path),
            content=content,
            functions=functions,
            async_functions=async_functions,
            imports=imports,
            classes=classes,
            class_methods=class_methods,
            decorators=decorators,
            line_markers=line_markers
        )

        self._file_cache[file_path] = entity
        return entity

    def build_dependency_context(
        self,
        entities: List[ExtractedEntity],
        max_depth: int = 2
    ) -> Dict[str, DependencyContext]:
        """
        Build dependency-aware context from extracted entities.

        Args:
            entities: List of extracted entities from logs
            max_depth: Maximum dependency depth (1 or 2 recommended)

        Returns:
            Dictionary mapping file paths to DependencyContext
        """
        contexts = {}
        processed_files: Set[str] = set()

        # Process file entities first
        file_entities = [e for e in entities if e.entity_type == "file"]

        for entity in file_entities:
            file_path = entity.name
            if file_path in processed_files:
                continue

            parsed = self.parse_file(file_path)
            if not parsed:
                continue

            # Create primary context
            context = DependencyContext(
                primary_file=file_path,
                content=parsed.content,
                imports=parsed.imports,
                related_functions=[
                    {"name": f, "file": file_path}
                    for f in parsed.functions
                ],
                token_count=self._count_tokens(parsed.content),
                depth=0
            )
            contexts[file_path] = context
            processed_files.add(file_path)

            # Expand to dependencies (depth 1)
            if max_depth >= 1:
                for imp in parsed.imports:
                    # Try to resolve import to local file
                    resolved = self._resolve_import(imp)
                    if resolved and resolved not in processed_files:
                        dep_parsed = self.parse_file(resolved)
                        if dep_parsed:
                            dep_context = DependencyContext(
                                primary_file=resolved,
                                content=dep_parsed.content,
                                imports=dep_parsed.imports,
                                related_functions=[
                                    {"name": f, "file": resolved}
                                    for f in dep_parsed.functions
                                ],
                                token_count=self._count_tokens(dep_parsed.content),
                                depth=1
                            )
                            contexts[resolved] = dep_context
                            processed_files.add(resolved)

            # Expand to depth 2 (direct callers/callees)
            if max_depth >= 2:
                for func_entity in [e for e in entities if e.entity_type == "function"]:
                    func_name = func_entity.name
                    # Find functions with this name in parsed files
                    for file_path, ctx in list(contexts.items()):
                        if func_name in [f["name"] for f in ctx.related_functions]:
                            # This function is already included
                            continue
                        # Check if any function in this file calls the target
                        parsed_file = self.parse_file(file_path)
                        if parsed_file:
                            # Simple heuristic: include files that import related modules
                            for imp in parsed_file.imports:
                                resolved = self._resolve_import(imp)
                                if resolved and resolved not in processed_files:
                                    dep_parsed = self.parse_file(resolved)
                                    if dep_parsed and func_name in dep_parsed.functions:
                                        dep_context = DependencyContext(
                                            primary_file=resolved,
                                            content=dep_parsed.content[:10000],  # limit size
                                            imports=dep_parsed.imports,
                                            related_functions=[
                                                {"name": func_name, "file": resolved}
                                            ],
                                            token_count=self._count_tokens(dep_parsed.content[:10000]),
                                            depth=2
                                        )
                                        contexts[resolved] = dep_context
                                        processed_files.add(resolved)

        return contexts

    def _resolve_import(self, import_name: str) -> Optional[str]:
        """
        Resolve an import statement to a local file path.

        Args:
            import_name: Module import name (e.g., "utils.helpers")

        Returns:
            File path if found, None otherwise
        """
        # Skip external/standard library imports
        external_modules = {
            'os', 'sys', 're', 'ast', 'json', 'time', 'datetime',
            'collections', 'itertools', 'functools', 'typing',
            'pathlib', 'io', 'threading', 'multiprocessing',
            'asyncio', 'concurrent', 'logging', 'unittest',
            'requests', 'flask', 'django', 'fastapi', 'sqlalchemy',
            'numpy', 'pandas', 'torch', 'tensorflow',
            'boto3', 'botocore', 'aws', 'aws_bedrock',
            'langchain', 'langgraph', 'pydantic', 'rich',
            'pytest', 'setuptools', 'pip'
        }

        # Check if it's an external module
        root_module = import_name.lstrip('.').split('.')[0]
        if root_module in external_modules:
            return None  # External library, skip

        # Handle relative imports (e.g., "..utils")
        if import_name.startswith('.'):
            dots = len(import_name) - len(import_name.lstrip('.'))
            parts = import_name.lstrip('.').split('.')

            # Go up directories for each dot
            current = self.base_path
            for _ in range(dots):
                current = current.parent

            # Build path from remaining parts
            if parts and parts[0]:
                candidates = [
                    current / '/'.join(parts) / '__init__.py',
                    current / '/'.join(parts) + '.py',
                    current / parts[-1] + '.py',
                ]
            else:
                candidates = [current / '__init__.py']
        else:
            # Convert module name to path
            parts = import_name.split(".")

            candidates = [
                self.base_path / '/'.join(parts) / '__init__.py',
                self.base_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py" if len(parts) > 1 else None,
                self.base_path / f"{parts[-1]}.py",
                self.base_path / f"{parts[0]}.py",
            ]

        for candidate in candidates:
            if candidate and candidate.exists():
                return str(candidate)

        # Also check for package __init__.py
        if len(parts) >= 1:
            pkg_init = self.base_path / parts[0] / '__init__.py'
            if pkg_init.exists():
                return str(pkg_init)

        return None

    def _count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses simple heuristic: ~4 chars per token for Python code.
        """
        # Simple estimation: 1 token ≈ 4 characters for code
        return len(text) // 4

    def extract_line_content(self, file_path: str, line_number: int) -> Optional[str]:
        """
        Extract specific line content from a file.

        Args:
            file_path: Path to the Python file
            line_number: Line number to extract (1-indexed)

        Returns:
            The line content if found, None otherwise
        """
        entity = self.parse_file(file_path)
        if not entity:
            return None

        lines = entity.content.split('\n')
        if 0 < line_number <= len(lines):
            return lines[line_number - 1]
        return None

    def get_error_context(self, file_path: str, line_number: int, context_lines: int = 3) -> Optional[str]:
        """
        Get error context with surrounding lines.

        Args:
            file_path: Path to the Python file
            line_number: Line number of the error
            context_lines: Number of lines before/after to include

        Returns:
            Context snippet if found, None otherwise
        """
        entity = self.parse_file(file_path)
        if not entity:
            return None

        lines = entity.content.split('\n')
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        context = []
        for i in range(start, end):
            marker = ">>>" if i == line_number - 1 else "   "
            context.append(f"{marker} {i + 1}: {lines[i]}")

        return '\n'.join(context)

    def identify_external_dependencies(self, entities: List[ExtractedEntity]) -> List[str]:
        """
        Identify external library dependencies mentioned in logs.

        Args:
            entities: List of extracted entities

        Returns:
            List of external dependency names
        """
        external_deps = set()

        # Common external library patterns
        lib_patterns = {
            'aws': ['boto3', 'botocore', 'aws_sdk'],
            'database': ['sqlalchemy', 'psycopg2', 'pymongo', 'redis'],
            'web': ['flask', 'django', 'fastapi', 'requests', 'aiohttp'],
            'ml': ['numpy', 'pandas', 'torch', 'tensorflow', 'scikit-learn'],
            'async': ['asyncio', 'aioboto3', 'aiohttp', 'asyncpg'],
        }

        for entity in entities:
            if entity.entity_type == "module":
                for lib_name, modules in lib_patterns.items():
                    if any(m in entity.name for m in modules):
                        external_deps.add(lib_name)

        return list(external_deps)

    def retrieve(self, state: AgentState) -> AgentState:
        """
        Main retrieval method - processes state and adds context.

        Args:
            state: Current agent state

        Returns:
            Updated state with dependency context
        """
        # Extract entities from logs
        entities = self.extract_entities(state.input_logs)
        for entity in entities:
            state.add_entity(entity)

        # Build dependency context from log entities
        contexts = self.build_dependency_context(entities)

        # Add contexts to state
        for file_path, context in contexts.items():
            state.add_dependency_context(context)
            state.context_tokens_total += context.token_count

        # Also include any directly provided code snippets
        for file_path, content in state.code_snippets.items():
            if file_path not in contexts:
                # Parse the snippet to extract structure
                entity = self._parse_content(file_path, content)
                ctx = DependencyContext(
                    primary_file=file_path,
                    content=content,
                    imports=entity.imports if entity else [],
                    related_functions=[
                        {"name": f, "file": file_path}
                        for f in (entity.functions + entity.async_functions if entity else [])
                    ],
                    token_count=self._count_tokens(content),
                    depth=0
                )
                state.add_dependency_context(ctx)
                # Cache the parsed entity
                if entity:
                    self._file_cache[file_path] = entity

        return state

    def get_relevant_context_summary(self, state: AgentState) -> str:
        """
        Get a summary of the retrieved context.

        Args:
            state: Agent state with populated context

        Returns:
            Human-readable context summary
        """
        summary_lines = ["=== Retrieved Context ==="]

        for file_path, ctx in state.dependency_context.items():
            summary_lines.append(f"\n[FILE] {file_path} (depth={ctx.depth})")
            summary_lines.append(f"   Tokens: {ctx.token_count}")
            summary_lines.append(f"   Imports: {', '.join(ctx.imports[:5])}")
            summary_lines.append(f"   Functions: {len(ctx.related_functions)} found")

            # Show file entity details if cached
            if file_path in self._file_cache:
                entity = self._file_cache[file_path]
                if entity.async_functions:
                    summary_lines.append(f"   Async functions: {', '.join(entity.async_functions[:3])}")
                if entity.classes:
                    summary_lines.append(f"   Classes: {', '.join(entity.classes)}")

        summary_lines.append(f"\n=== Context Efficiency ===")
        efficiency = state.get_context_efficiency()
        summary_lines.append(f"Relevant tokens: {state.relevant_tokens}")
        summary_lines.append(f"Total tokens: {state.context_tokens_total}")
        summary_lines.append(f"Efficiency: {efficiency:.2%}")

        return "\n".join(summary_lines)

    def get_retrieval_stats(self, state: AgentState) -> Dict[str, any]:
        """
        Get retrieval statistics.

        Args:
            state: Agent state with populated context

        Returns:
            Dictionary of retrieval statistics
        """
        file_count = len(state.dependency_context)
        total_tokens = state.context_tokens_total
        relevant_tokens = state.relevant_tokens

        # Count entity types
        entity_counts = {}
        for entity in state.extracted_entities:
            entity_type = entity.entity_type
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        # Count async vs sync functions
        async_count = 0
        sync_count = 0
        for file_path in self._file_cache:
            entity = self._file_cache[file_path]
            async_count += len(entity.async_functions)
            sync_count += len(entity.functions)

        return {
            "files_retrieved": file_count,
            "total_tokens": total_tokens,
            "relevant_tokens": relevant_tokens,
            "efficiency": state.get_context_efficiency(),
            "entity_counts": entity_counts,
            "async_functions": async_count,
            "sync_functions": sync_count,
            "classes_found": sum(len(e.classes) for e in self._file_cache.values()),
            "external_deps": self.identify_external_dependencies(list(state.extracted_entities)),
        }
