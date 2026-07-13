"""Language-agnostic code generation, compilation, and execution engine.

Centralizes language detection, extension resolution, compilation, and
execution so the planner never hardcodes Python or any single language.
"""
import os
import re
import shutil
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LanguageDef:
    name: str               # canonical name, e.g. "cpp"
    extension: str           # e.g. ".cpp"
    aliases: tuple           # alternative names, e.g. ("c++", "cplusplus")
    interpreter: Optional[str]  # interpreter binary, e.g. "python"
    compiler: Optional[str]     # compiler binary, e.g. "g++"
    compile_ext: Optional[str]  # extension of compiled output, e.g. ".exe" on Windows
    runnable: bool = True    # False for html/css (no execution step)
    compile_before_run: bool = False  # True for C, C++, Rust, Java


LANGUAGES: list[LanguageDef] = [
    LanguageDef("python",      ".py",  ("py",),                       "python",   None,       None),
    LanguageDef("cpp",         ".cpp", ("c++", "cplusplus"),          None,       "g++",      ".exe", compile_before_run=True),
    LanguageDef("c",           ".c",   ("clang",),                    None,       "gcc",      ".exe", compile_before_run=True),
    LanguageDef("java",        ".java",("jdk"),                       None,       "javac",    ".class", compile_before_run=True),
    LanguageDef("javascript",  ".js",  ("js", "node", "nodejs"),      "node",     None,       None),
    LanguageDef("typescript",  ".ts",  ("ts",),                       "ts-node",  "tsc",      ".js", compile_before_run=True),
    LanguageDef("html",        ".html",("htm", "webpage"),            None,       None,       None, runnable=False),
    LanguageDef("css",         ".css", ("stylesheet",),               None,       None,       None, runnable=False),
    LanguageDef("react",       ".jsx", ("reactjs", "react.js"),       None,       None,       None, runnable=False),
    LanguageDef("go",          ".go",  ("golang",),                   "go",       None,       None),
    LanguageDef("rust",        ".rs",  (),                            None,       "rustc",    ".exe", compile_before_run=True),
    LanguageDef("php",         ".php", (),                            "php",      None,       None),
    LanguageDef("csharp",      ".cs",  ("c#", "cs", "dotnet"),        None,       "dotnet",   ".dll", compile_before_run=True),
    LanguageDef("kotlin",      ".kt",  (),                            None,       "kotlinc",  ".jar", compile_before_run=True),
    LanguageDef("swift",       ".swift",(),                           None,       "swiftc",   None, compile_before_run=True),
    LanguageDef("ruby",        ".rb",  (),                            "ruby",     None,       None),
    LanguageDef("bash",        ".sh",  ("shell", "sh", "zsh"),        "bash",     None,       None),
    LanguageDef("r",           ".r",   ("rscript",),                  "Rscript",  None,       None),
]

# Build fast lookup structures
_ALIAS_TO_NAME: dict[str, str] = {}
_NAME_TO_DEF: dict[str, LanguageDef] = {}
_EXT_TO_DEF: dict[str, LanguageDef] = {}

for _ld in LANGUAGES:
    _NAME_TO_DEF[_ld.name] = _ld
    _EXT_TO_DEF[_ld.extension] = _ld
    _ALIAS_TO_NAME[_ld.name] = _ld.name
    for alias in _ld.aliases:
        _ALIAS_TO_NAME[alias.lower()] = _ld.name


# ---------------------------------------------------------------------------
# LanguageDetector
# ---------------------------------------------------------------------------

class LanguageDetector:
    """Detects programming language from a natural-language prompt."""

    # Ordered patterns: first match wins
    # Use (?![a-z0-9]) instead of \b at end — \b fails for tokens ending in
    # non-word chars (e.g. c++, c#) because there's no word/non-word transition.
    _LANG_ALTS = (
        r'c\+\+|cpp|cplusplus|c#|csharp|dotnet|'
        r'python|py|java|javascript|js|node|nodejs|typescript|ts|'
        r'html|htm|webpage|css|stylesheet|react|reactjs|'
        r'go|golang|rust|rs|php|ruby|rb|swift|kotlin|kt|'
        r'bash|shell|r|c'
    )
    _PATTERNS: list[tuple[str, str]] = [
        # Explicit "in <lang>" / "using <lang>" / "with <lang>"
        (rf'\b(?:in|using|with|written\s+in)\s+({_LANG_ALTS})(?![a-z0-9])', "lang"),
        # File extension hints like ".py", ".cpp"
        (r'\.(\w{1,4})\b', "ext"),
        # Standalone language keywords
        (rf'\b({_LANG_ALTS})(?![a-z0-9])', "keyword"),
    ]

    @classmethod
    def detect(cls, prompt: str) -> LanguageDef:
        """Detect the language from a prompt. Never returns None — defaults to Python."""
        p = prompt.lower()

        for pattern, kind in cls._PATTERNS:
            m = re.search(pattern, p)
            if m:
                raw = m.group(1) if kind != "ext" else m.group(0)
                # For extension hints, only accept known extensions
                if kind == "ext":
                    ext = "." + raw.lower()
                    if ext in _EXT_TO_DEF:
                        return _EXT_TO_DEF[ext]
                    continue
                name = _ALIAS_TO_NAME.get(raw.lower())
                if name:
                    return _NAME_TO_DEF[name]

        return _NAME_TO_DEF["python"]  # ultimate fallback

    @classmethod
    def detect_all(cls, prompt: str) -> List[LanguageDef]:
        """Return all languages mentioned in the prompt (for multi-file projects)."""
        p = prompt.lower()
        found = []
        seen = set()
        for pattern, kind in cls._PATTERNS:
            for m in re.finditer(pattern, p):
                raw = m.group(1) if kind != "ext" else m.group(0)
                if kind == "ext":
                    ext = "." + raw.lower()
                    if ext in _EXT_TO_DEF:
                        ld = _EXT_TO_DEF[ext]
                else:
                    name = _ALIAS_TO_NAME.get(raw.lower())
                    ld = _NAME_TO_DEF.get(name) if name else None
                if ld and ld.name not in seen:
                    found.append(ld)
                    seen.add(ld.name)
        return found or [_NAME_TO_DEF["python"]]


# ---------------------------------------------------------------------------
# ExtensionResolver
# ---------------------------------------------------------------------------

class ExtensionResolver:
    """Resolves file extension from language and validates explicit extensions."""

    @staticmethod
    def resolve(lang: LanguageDef, explicit_filename: Optional[str] = None) -> str:
        """Return the correct extension. If explicit_filename is given and already
        has the right extension, return it unchanged. If wrong, fix it."""
        if explicit_filename:
            base, ext = os.path.splitext(explicit_filename)
            if ext.lower() == lang.extension:
                return explicit_filename
            # Wrong extension — fix it
            return base + lang.extension
        return lang.extension

    @staticmethod
    def validate_extension(filename: str, lang: LanguageDef) -> bool:
        """Check that the file extension matches the language."""
        _, ext = os.path.splitext(filename)
        return ext.lower() == lang.extension


# ---------------------------------------------------------------------------
# ExecutionDispatcher
# ---------------------------------------------------------------------------

class ExecutionDispatcher:
    """Generates compile and run commands for any supported language."""

    @staticmethod
    def build_filename(topic: str, lang: LanguageDef) -> str:
        """Build a safe filename from topic and language."""
        clean = re.sub(r'[^a-z0-9_]+', '_', topic.lower()).strip('_')[:40]
        if not clean:
            clean = "program"
        return f"{clean}{lang.extension}"

    @staticmethod
    def compile_command(filepath: str, lang: LanguageDef, output_dir: str) -> Optional[Tuple[str, str]]:
        """Return (compiler_binary, compile_command_string) or None if no compilation needed."""
        if not lang.compile_before_run or not lang.compiler:
            return None

        out_name = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(output_dir, out_name + (lang.compile_ext or ".exe"))

        if lang.name == "java":
            cmd = f'javac "{filepath}"'
            return (lang.compiler, cmd)

        if lang.name in ("c", "cpp"):
            compiler = lang.compiler
            cmd = f'{compiler} "{filepath}" -o "{out_path}" && echo "Compiled successfully"'
            return (compiler, cmd)

        if lang.name == "rust":
            cmd = f'rustc "{filepath}" -o "{out_path}" && echo "Compiled successfully"'
            return ("rustc", cmd)

        if lang.name == "kotlin":
            cmd = f'kotlinc "{filepath}" -include-runtime -d "{out_path}" && echo "Compiled successfully"'
            return ("kotlinc", cmd)

        if lang.name == "swift":
            cmd = f'swiftc "{filepath}" -o "{out_path}" && echo "Compiled successfully"'
            return ("swiftc", cmd)

        if lang.name == "csharp":
            cmd = f'dotnet build "{filepath}" && echo "Compiled successfully"'
            return ("dotnet", cmd)

        if lang.name == "typescript":
            cmd = f'tsc "{filepath}" && echo "Compiled successfully"'
            return ("tsc", cmd)

        return None

    @staticmethod
    def run_command(filepath: str, lang: LanguageDef, output_dir: str) -> str:
        """Return the command string to execute the program."""
        out_name = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(output_dir, out_name + (lang.compile_ext or ".exe"))

        if not lang.runnable:
            return f'echo "File saved to {filepath} — no execution needed for {lang.name}"'

        # Compiled languages: run the binary
        if lang.compile_before_run:
            if lang.name == "java":
                class_name = os.path.splitext(os.path.basename(filepath))[0]
                return f'java -cp "{output_dir}" {class_name}'
            if lang.compile_ext:
                return f'"{out_path}"'

        # Interpreted languages
        if lang.interpreter:
            if lang.name == "go":
                return f'go run "{filepath}"'
            return f'{lang.interpreter} "{filepath}"'

        # Fallback
        return f'echo "No interpreter configured for {lang.name}. File saved to {filepath}"'


# ---------------------------------------------------------------------------
# CompilerManager
# ---------------------------------------------------------------------------

class CompilerManager:
    """Checks availability of compilers/interpreters."""

    @staticmethod
    def check(name: str) -> bool:
        """Return True if the binary is on PATH."""
        return shutil.which(name) is not None

    @classmethod
    def check_language(cls, lang: LanguageDef) -> Tuple[bool, str]:
        """Check if the language can be executed. Returns (ok, message)."""
        if not lang.runnable:
            return True, f"{lang.name} files do not need execution"

        if lang.compile_before_run and lang.compiler:
            if cls.check(lang.compiler):
                return True, f"{lang.compiler} found"
            return False, f"{lang.compiler} not found — install it to compile {lang.name} files"

        if lang.interpreter:
            if cls.check(lang.interpreter):
                return True, f"{lang.interpreter} found"
            return False, f"{lang.interpreter} not found — install it to run {lang.name} files"

        return True, f"{lang.name} — no compiler/interpreter check needed"

    @classmethod
    def get_missing_for_plan(cls, steps: list) -> list[str]:
        """Scan a list of plan steps for missing compilers. Returns error messages."""
        errors = []
        for step in steps:
            if step.get("agent_type") == "terminal":
                cmd = step.get("parameters", {}).get("command", "")
                # Extract the first token (the compiler/interpreter)
                first_token = cmd.strip().split()[0] if cmd.strip() else ""
                if first_token and not cls.check(first_token):
                    if first_token not in ("echo", "cd", "dir", "ls", "python", "node", "java"):
                        errors.append(f"{first_token} is not installed on this system")
        return errors
