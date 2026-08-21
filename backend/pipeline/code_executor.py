"""
Sandboxed Code Execution Module for Zenix AI.
Provides safe execution of Python and JavaScript code.
Uses restricted execution environment with timeout and resource limits.
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
import signal
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: str
    execution_time: float
    language: str
    memory_used: Optional[int] = None


class CodeExecutor:
    """
    Sandboxed code execution environment.
    Supports Python and JavaScript with safety restrictions.
    """

    # Maximum execution time in seconds
    MAX_TIMEOUT = 10

    # Maximum output size in characters
    MAX_OUTPUT_SIZE = 10000

    # Restricted Python builtins
    RESTRICTED_BUILTINS = {
        "__import__": None,
        "exec": None,
        "eval": None,
        "compile": None,
        "open": None,
        "input": None,
        "breakpoint": None,
        "exit": None,
        "quit": None,
    }

    # Allowed Python modules
    ALLOWED_PYTHON_MODULES = {
        "math", "random", "datetime", "collections", "itertools",
        "functools", "operator", "string", "re", "json",
        "statistics", "decimal", "fractions", "heapq", "bisect",
        "array", "enum", "dataclasses", "typing",
    }

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zenix_code_")

    def execute(self, code: str, language: str = "python") -> ExecutionResult:
        """
        Execute code in a sandboxed environment.

        Args:
            code: Code to execute
            language: Programming language ("python" or "javascript")

        Returns:
            ExecutionResult with output, errors, and metadata
        """
        if language.lower() == "python":
            return self._execute_python(code)
        elif language.lower() in ("javascript", "js", "node"):
            return self._execute_javascript(code)
        else:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Unsupported language: {language}. Use 'python' or 'javascript'.",
                execution_time=0,
                language=language,
            )

    def _execute_python(self, code: str) -> ExecutionResult:
        """Execute Python code safely."""
        import time
        start_time = time.time()

        # Create a restricted Python script
        restricted_code = self._create_restricted_python(code)

        # Write to temp file
        script_path = os.path.join(self.temp_dir, "exec.py")
        with open(script_path, "w") as f:
            f.write(restricted_code)

        try:
            # Execute with timeout
            result = subprocess.run(
                [sys.executable, "-u", script_path],
                capture_output=True,
                text=True,
                timeout=self.MAX_TIMEOUT,
                cwd=self.temp_dir,
                env=self._get_restricted_env(),
            )

            execution_time = time.time() - start_time

            output = result.stdout[:self.MAX_OUTPUT_SIZE]
            error = result.stderr[:self.MAX_OUTPUT_SIZE]

            return ExecutionResult(
                success=result.returncode == 0,
                output=output,
                error=error,
                execution_time=round(execution_time, 3),
                language="python",
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.MAX_TIMEOUT} seconds.",
                execution_time=self.MAX_TIMEOUT,
                language="python",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time,
                language="python",
            )

    def _create_restricted_python(self, code: str) -> str:
        """Create a restricted Python execution environment."""
        restricted = '''
import sys
import os

# Restrict imports
_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

ALLOWED_MODULES = {allowed_modules}

def restricted_import(name, *args, **kwargs):
    if name.split('.')[0] not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{{name}}' is not allowed in sandboxed execution")
    return _original_import(name, *args, **kwargs)

# Apply restrictions
import builtins
builtins.__import__ = restricted_import

# Remove dangerous builtins
for attr in ['open', 'exec', 'eval', 'compile', '__import__', 'input', 'breakpoint', 'exit', 'quit']:
    if hasattr(builtins, attr):
        delattr(builtins, attr)

# Execute user code
try:
    # Create a restricted namespace
    namespace = {{'__builtins__': builtins}}
    
    # Execute the code
    exec("""{code}""", namespace)
    
    # Print result if there's a 'result' variable
    if 'result' in namespace:
        print(f"Result: {{namespace['result']}}")
        
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
'''.format(
            allowed_modules=json.dumps(list(self.ALLOWED_PYTHON_MODULES)),
            code=code.replace('\\', '\\\\').replace('"""', '\\"\\"\\"'),
        )
        return restricted

    def _execute_javascript(self, code: str) -> ExecutionResult:
        """Execute JavaScript code using Node.js."""
        import time
        start_time = time.time()

        # Write to temp file
        script_path = os.path.join(self.temp_dir, "exec.js")
        with open(script_path, "w") as f:
            f.write(code)

        try:
            # Execute with timeout
            result = subprocess.run(
                ["node", "--max-old-space-size=64", script_path],
                capture_output=True,
                text=True,
                timeout=self.MAX_TIMEOUT,
                cwd=self.temp_dir,
            )

            execution_time = time.time() - start_time

            output = result.stdout[:self.MAX_OUTPUT_SIZE]
            error = result.stderr[:self.MAX_OUTPUT_SIZE]

            return ExecutionResult(
                success=result.returncode == 0,
                output=output,
                error=error,
                execution_time=round(execution_time, 3),
                language="javascript",
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                output="",
                error="Node.js is not installed. JavaScript execution unavailable.",
                execution_time=0,
                language="javascript",
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.MAX_TIMEOUT} seconds.",
                execution_time=self.MAX_TIMEOUT,
                language="javascript",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time,
                language="javascript",
            )

    def _get_restricted_env(self) -> Dict[str, str]:
        """Get restricted environment variables."""
        env = os.environ.copy()
        # Remove potentially dangerous environment variables
        for key in ["PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME"]:
            env.pop(key, None)
        return env

    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


class CodeAnalysis:
    """Analyze code for common patterns and provide suggestions."""

    @staticmethod
    def analyze_python(code: str) -> Dict[str, Any]:
        """Analyze Python code and provide suggestions."""
        issues = []
        suggestions = []

        # Check for common issues
        if "import os" in code:
            issues.append("OS module import detected - may be restricted in sandbox")
        if "import subprocess" in code:
            issues.append("Subprocess import detected - may be restricted in sandbox")
        if "open(" in code:
            issues.append("File open detected - may be restricted in sandbox")
        if "exec(" in code or "eval(" in code:
            issues.append("Dynamic code execution detected - may be restricted")

        # Check for code quality
        lines = code.split("\n")
        if len(lines) > 100:
            suggestions.append("Code is quite long. Consider breaking into functions.")

        if not any(line.strip().startswith("def ") for line in lines if line.strip()):
            if len(lines) > 20:
                suggestions.append("Consider using functions for better organization.")

        return {
            "issues": issues,
            "suggestions": suggestions,
            "line_count": len(lines),
            "has_functions": any(line.strip().startswith("def ") for line in lines),
            "imports": [line for line in lines if line.strip().startswith("import ")],
        }

    @staticmethod
    def get_code_examples(language: str = "python") -> str:
        """Get code execution examples."""
        if language == "python":
            return '''
# Python Examples

# 1. Math calculation
import math
result = math.sqrt(144)
print(f"Square root of 144 = {result}")

# 2. List comprehension
squares = [x**2 for x in range(10)]
result = squares

# 3. String manipulation
text = "Hello, Zenix!"
result = text.upper()

# 4. Dictionary operations
data = {"name": "Priya", "city": "Mumbai", "age": 25}
result = {k: v for k, v in data.items() if k != "age"}

# 5. Statistics
import statistics
numbers = [10, 20, 30, 40, 50]
result = {
    "mean": statistics.mean(numbers),
    "median": statistics.median(numbers),
    "stdev": statistics.stdev(numbers)
}
'''
        elif language in ("javascript", "js"):
            return '''
// JavaScript Examples

// 1. Math calculation
const sqrt = Math.sqrt(144);
console.log(`Square root of 144 = ${sqrt}`);

// 2. Array operations
const squares = Array.from({length: 10}, (_, i) => i ** 2);
console.log("Squares:", squares);

// 3. String manipulation
const text = "Hello, Zenix!";
console.log("Uppercase:", text.toUpperCase());

// 4. Object operations
const data = {name: "Priya", city: "Mumbai", age: 25};
const filtered = Object.fromEntries(
    Object.entries(data).filter(([k]) => k !== "age")
);
console.log("Filtered:", filtered);

// 5. Statistics
const numbers = [10, 20, 30, 40, 50];
const mean = numbers.reduce((a, b) => a + b, 0) / numbers.length;
console.log("Mean:", mean);
'''
        return ""


# Singleton instances
_code_executor = None
_code_analysis = None


def get_code_executor() -> CodeExecutor:
    """Get or create the code executor singleton."""
    global _code_executor
    if _code_executor is None:
        _code_executor = CodeExecutor()
    return _code_executor


def get_code_analysis() -> CodeAnalysis:
    """Get or create the code analysis singleton."""
    global _code_analysis
    if _code_analysis is None:
        _code_analysis = CodeAnalysis()
    return _code_analysis
