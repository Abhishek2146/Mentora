"""
Coding Service - problem execution and AI generation.

NOTE: Executing arbitrary user code directly on the API host is unsafe.
For production, run this service inside an isolated sandbox/container.
"""

import json
import os
import platform
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.coding_problem import CodingProblem


logger = get_logger(__name__)


class CodingService:
    """Service for coding practice and code execution."""

    def __init__(self):
        self.supported_languages = {
            "python": {"ext": "py", "cmd": ["python"]},
            "javascript": {"ext": "js", "cmd": ["node"]},
            "java": {"ext": "java", "cmd": ["javac"]},
            "cpp": {"ext": "cpp", "cmd": ["g++"]},
            "c": {"ext": "c", "cmd": ["gcc"]},
            "go": {"ext": "go", "cmd": ["go"]},
            "rust": {"ext": "rs", "cmd": ["rustc"]},
        }
        self.is_windows = platform.system() == "Windows"

    # ============================================================
    # Code Execution
    # ============================================================

    async def execute_code(
        self,
        problem_id: int,
        code: str,
        language: str,
        test_cases: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Execute submitted code and grade against test cases when provided."""
        language = language.lower().strip()
        lang_info = self.supported_languages.get(language)

        if not lang_info:
            return self._error_result(
                f"Language '{language}' is not supported.",
                execution_time=0,
            )

        if not self._command_exists(lang_info["cmd"][0]):
            return self._error_result(
                f"Required executable '{lang_info['cmd'][0]}' was not found on this system.",
                execution_time=0,
            )

        cases = test_cases or []
        start = time.perf_counter()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                if cases:
                    return self._grade_test_cases(
                        code=code,
                        language=language,
                        lang_info=lang_info,
                        test_cases=cases,
                        tmpdir=tmpdir,
                        start=start,
                    )

                run = self._run_program(
                    code=code,
                    language=language,
                    lang_info=lang_info,
                    tmpdir=tmpdir,
                    stdin="",
                )
                elapsed = int((time.perf_counter() - start) * 1000)
                passed = run["status"] == "passed"
                return {
                    "status": run["status"],
                    "output": run["output"],
                    "passed": passed,
                    "score": 100 if passed else 0,
                    "execution_time": elapsed,
                    "error_message": run.get("error_message"),
                    "passed_test_cases": 1 if passed else 0,
                    "total_test_cases": 1,
                }
            except subprocess.TimeoutExpired:
                return self._error_result(
                    "Execution timed out.",
                    status="timeout",
                    execution_time=int((time.perf_counter() - start) * 1000),
                )
            except Exception as exc:
                logger.exception("Code execution failed: %s", exc)
                return self._error_result(
                    str(exc),
                    execution_time=int((time.perf_counter() - start) * 1000),
                )

    def _grade_test_cases(
        self,
        code: str,
        language: str,
        lang_info: Dict[str, Any],
        test_cases: List[Any],
        tmpdir: str,
        start: float,
    ) -> Dict[str, Any]:
        passed_count = 0
        total = len(test_cases)
        details: List[str] = []

        for index, case in enumerate(test_cases, start=1):
            if not isinstance(case, dict):
                details.append(f"Test {index}: invalid test case format")
                continue

            stdin = str(case.get("input", ""))
            expected = self._normalize_output(str(case.get("expected", "")))
            run = self._run_program(
                code=code,
                language=language,
                lang_info=lang_info,
                tmpdir=tmpdir,
                stdin=stdin,
            )

            if run["status"] == "error":
                details.append(f"Test {index}: error — {run['output'][:500]}")
                continue
            if run["status"] == "timeout":
                details.append(f"Test {index}: timed out")
                continue

            actual = self._normalize_output(run.get("stdout", ""))
            if actual == expected:
                passed_count += 1
                details.append(f"Test {index}: ✓ passed")
            else:
                details.append(
                    f"Test {index}: ✗ failed\n"
                    f"  Expected: {expected!r}\n"
                    f"  Got:      {actual!r}"
                )

        elapsed = int((time.perf_counter() - start) * 1000)
        all_passed = passed_count == total and total > 0
        score = int(round(100 * passed_count / total)) if total else 0

        return {
            "status": "passed" if all_passed else "failed",
            "output": "\n".join(details),
            "passed": all_passed,
            "score": score,
            "execution_time": elapsed,
            "error_message": None if all_passed else "Some test cases failed",
            "passed_test_cases": passed_count,
            "total_test_cases": total,
        }

    def _run_program(
        self,
        code: str,
        language: str,
        lang_info: Dict[str, Any],
        tmpdir: str,
        stdin: str,
    ) -> Dict[str, Any]:
        ext = lang_info["ext"]

        if language == "java":
            # Extract the public class name so the filename matches.
            class_name = self._extract_java_class_name(code)
            file_path = os.path.join(tmpdir, f"{class_name}.java")
        else:
            file_path = os.path.join(tmpdir, f"main.{ext}")

        with open(file_path, "w", encoding="utf-8") as source_file:
            source_file.write(code)

        if language == "java":
            compile_result = subprocess.run(
                [lang_info["cmd"][0], file_path],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                err = (compile_result.stdout or "") + (compile_result.stderr or "")
                return {
                    "status": "error",
                    "output": err,
                    "stdout": "",
                    "error_message": compile_result.stderr or "Compilation failed",
                }
            run_cmd = ["java", class_name]

        elif language == "cpp":
            executable = os.path.join(tmpdir, "main.exe" if self.is_windows else "main")
            compile_result = subprocess.run(
                [lang_info["cmd"][0], "-std=c++17", file_path, "-o", executable],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                err = (compile_result.stdout or "") + (compile_result.stderr or "")
                return {
                    "status": "error",
                    "output": err,
                    "stdout": "",
                    "error_message": compile_result.stderr or "Compilation failed",
                }
            run_cmd = [executable]

        elif language == "c":
            executable = os.path.join(tmpdir, "main.exe" if self.is_windows else "main")
            compile_result = subprocess.run(
                [lang_info["cmd"][0], file_path, "-o", executable],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                err = (compile_result.stdout or "") + (compile_result.stderr or "")
                return {
                    "status": "error",
                    "output": err,
                    "stdout": "",
                    "error_message": compile_result.stderr or "Compilation failed",
                }
            run_cmd = [executable]

        elif language == "go":
            executable = os.path.join(tmpdir, "main.exe" if self.is_windows else "main")
            compile_result = subprocess.run(
                [lang_info["cmd"][0], "build", "-o", executable, file_path],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                err = (compile_result.stdout or "") + (compile_result.stderr or "")
                return {
                    "status": "error",
                    "output": err,
                    "stdout": "",
                    "error_message": compile_result.stderr or "Compilation failed",
                }
            run_cmd = [executable]

        elif language == "rust":
            executable = os.path.join(tmpdir, "main.exe" if self.is_windows else "main")
            compile_result = subprocess.run(
                [lang_info["cmd"][0], file_path, "-o", executable],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                err = (compile_result.stdout or "") + (compile_result.stderr or "")
                return {
                    "status": "error",
                    "output": err,
                    "stdout": "",
                    "error_message": compile_result.stderr or "Compilation failed",
                }
            run_cmd = [executable]

        else:
            run_cmd = [lang_info["cmd"][0], file_path]

        try:
            result = subprocess.run(
                run_cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "output": "Execution timed out.",
                "stdout": "",
                "error_message": "Execution timed out.",
            }

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + (f"\n{stderr}" if stderr else "")
        # A non-zero exit code means a runtime error, but if the program
        # exited cleanly we report "passed" so the grader can compare output.
        if result.returncode != 0:
            return {
                "status": "error",
                "output": output,
                "stdout": stdout,
                "error_message": stderr or "Runtime error",
            }
        return {
            "status": "passed",
            "output": output,
            "stdout": stdout,
            "error_message": stderr or None,
        }

    @staticmethod
    def _normalize_output(value: str) -> str:
        """Normalize output for comparison.

        Standard judge behaviour:
        - Strip leading/trailing whitespace from each line.
        - Collapse runs of blank lines into a single blank line.
        - Strip leading/trailing whitespace from the whole result.
        This preserves intentional newlines while removing incidental
        trailing spaces that compilers / print statements often emit.
        """
        lines = value.splitlines()
        stripped = [line.strip() for line in lines]
        # Remove trailing empty lines, then rejoin
        while stripped and stripped[-1] == "":
            stripped.pop()
        return "\n".join(stripped).strip()

    @staticmethod
    def _extract_java_class_name(code: str) -> str:
        """Return the public class name from Java source, defaulting to 'Main'."""
        # Look for: public class ClassName
        match = re.search(r"\bpublic\s+class\s+(\w+)", code)
        if match:
            return match.group(1)
        # Fallback: first class declaration
        match = re.search(r"\bclass\s+(\w+)", code)
        if match:
            return match.group(1)
        return "Main"

    @staticmethod
    def _error_result(
        message: str,
        status: str = "error",
        execution_time: int = 0,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "output": message,
            "passed": False,
            "score": 0,
            "execution_time": execution_time,
            "error_message": message,
            "passed_test_cases": 0,
            "total_test_cases": 0,
        }

    @staticmethod
    def _command_exists(command: str) -> bool:
        from shutil import which
        return which(command) is not None

    # ============================================================
    # AI Coding Problem Generation
    # ============================================================

    async def generate_and_save_problem(
        self,
        user_id: int,
        topic: str,
        difficulty: str,
        language: str,
        syllabus_context: str,
        db: AsyncSession,
        syllabus_id: Optional[int] = None,
    ) -> CodingProblem:
        generated = await self.generate_coding_problem(
            topic=topic,
            difficulty=difficulty,
            language=language,
            syllabus_context=syllabus_context,
        )

        title = (generated.get("title") or topic).strip()
        description = (generated.get("description") or "").strip()
        if not description:
            raise ValueError("AI could not generate a valid problem description.")

        problem = CodingProblem(
            user_id=user_id,
            subject_id=None,
            chapter_id=None,
            title=title[:255],
            description=description,
            difficulty=difficulty,
            category=generated.get("category") or "Algorithms",
            language=language,
            starter_code=generated.get("starter_code") or "",
            solution_code=generated.get("solution") or generated.get("solution_code"),
            input_format=generated.get("input_format"),
            output_format=generated.get("output_format"),
            constraints=generated.get("constraints"),
            examples=generated.get("examples") or [],
            test_cases=generated.get("test_cases") or [],
            hints=generated.get("hints") or [],
            tags=generated.get("tags") or [language, difficulty],
            is_ai_generated=True,
            ai_explanation=generated.get("explanation"),
            is_active=True,
        )

        db.add(problem)
        await db.commit()
        await db.refresh(problem)
        return problem

    async def generate_coding_problem(
        self,
        topic: str,
        difficulty: str = "medium",
        language: str = "python",
        syllabus_context: str = "",
    ) -> Dict[str, Any]:
        from app.services.llm_service import LLMService

        llm = LLMService()
        context_line = (
            f"Syllabus context: {syllabus_context}\n" if syllabus_context else ""
        )

        # Provide a language-specific stdin hint so the LLM generates
        # runnable starter/solution code for the target platform.
        stdin_hint = self._stdin_hint(language)

        prompt = f"""
Generate a {difficulty} coding practice problem about "{topic}".
{context_line}
Target language: {language}

Return ONLY valid JSON (no markdown fences, no extra text) with this structure:
{{
  "title": "Short problem title",
  "description": "Clear problem statement with requirements",
  "category": "Algorithms",
  "input_format": "Describe stdin input format",
  "output_format": "Describe expected stdout output",
  "constraints": "Time/space or input limits",
  "starter_code": "Starter code in {language} that reads stdin and prints answer",
  "solution": "Working solution in {language}",
  "examples": [
    {{"input": "sample stdin", "output": "expected stdout", "explanation": "why"}}
  ],
  "test_cases": [
    {{"input": "stdin for test 1", "expected": "exact expected stdout"}},
    {{"input": "stdin for test 2", "expected": "exact expected stdout"}},
    {{"input": "stdin for test 3", "expected": "exact expected stdout"}}
  ],
  "hints": ["hint 1", "hint 2"],
  "tags": ["tag1", "tag2"],
  "explanation": "Brief solution approach"
}}

Rules:
- Problems must be solvable by reading from stdin and writing to stdout.
- test_cases must have at least 3 entries with exact expected output strings.
- starter_code and solution must compile/run in {language}.
{stdin_hint}- Do NOT include markdown code fences or any text outside the JSON object.
"""

        try:
            response = await llm.generate(prompt, temperature=0.4)
            data = self._parse_llm_json(response)

            # Validate and normalise required fields
            if not isinstance(data.get("test_cases"), list) or len(data["test_cases"]) == 0:
                logger.warning("LLM returned no test_cases; generating empty list.")
                data["test_cases"] = []
            if not isinstance(data.get("examples"), list):
                data["examples"] = []
            if not data.get("title"):
                data["title"] = topic
            if not data.get("description"):
                raise ValueError("AI returned a problem without a description. Please try again.")
            if not data.get("starter_code"):
                data["starter_code"] = self._default_starter_code(language)

            # Sanitise JavaScript code: replace /dev/stdin with the
            # cross-platform process.stdin.fd equivalent.
            if language == "javascript":
                for field in ("starter_code", "solution"):
                    if data.get(field):
                        data[field] = data[field].replace(
                            "'/dev/stdin'", "process.stdin.fd"
                        ).replace(
                            '"/dev/stdin"', "process.stdin.fd"
                        )

            return data
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("Failed to generate coding problem: %s", exc)
            raise

    @staticmethod
    def _parse_llm_json(response: str) -> Dict[str, Any]:
        """Robustly parse JSON that may be wrapped in markdown fences or have
        leading/trailing prose."""
        text = response.strip()

        # 1. Strip markdown fences: ```json ... ``` or ``` ... ```
        fenced = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        fenced = re.sub(r"\s*```$", "", fenced).strip()
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass

        # 2. Extract first {...} block (handles leading/trailing prose)
        match = re.search(r"\{.*\}", fenced, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 3. Try the raw response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for coding problem.")
            raise ValueError(
                "AI returned an invalid problem format. Please try again."
            ) from None

    @staticmethod
    def _default_starter_code(language: str) -> str:
        """Return a minimal stdin-reading starter template for a language."""
        templates: Dict[str, str] = {
            "python": "# Read input and print output\nline = input()\nprint(line)\n",
            "javascript": (
                "const lines = require('fs').readFileSync(process.stdin.fd, 'utf8').trim().split('\\n');\n"
                "console.log(lines[0]);\n"
            ),
            "java": (
                "import java.util.Scanner;\n\npublic class Main {\n"
                "    public static void main(String[] args) {\n"
                "        Scanner sc = new Scanner(System.in);\n"
                "        System.out.println(sc.nextLine());\n"
                "    }\n}\n"
            ),
            "cpp": (
                "#include <iostream>\nusing namespace std;\n\nint main() {\n"
                "    string line;\n    cin >> line;\n    cout << line << endl;\n    return 0;\n}\n"
            ),
            "c": (
                "#include <stdio.h>\n\nint main() {\n"
                "    char line[1024];\n    scanf(\"%s\", line);\n    printf(\"%s\\n\", line);\n    return 0;\n}\n"
            ),
            "go": (
                "package main\n\nimport (\n    \"bufio\"\n    \"fmt\"\n    \"os\"\n)\n\n"
                "func main() {\n    reader := bufio.NewReader(os.Stdin)\n"
                "    line, _ := reader.ReadString('\\n')\n    fmt.Print(line)\n}\n"
            ),
            "rust": (
                "use std::io::{self, BufRead};\n\nfn main() {\n"
                "    let stdin = io::stdin();\n"
                "    let line = stdin.lock().lines().next().unwrap().unwrap();\n"
                "    println!(\"{}\", line);\n}\n"
            ),
        }
        return templates.get(language, "# Write your solution here\n")

    @staticmethod
    def _stdin_hint(language: str) -> str:
        """Return a language-specific rule for the LLM prompt so the generated
        starter/solution code reads stdin correctly on all platforms."""
        hints: Dict[str, str] = {
            "javascript": (
                "- For JavaScript use: "
                "require('fs').readFileSync(process.stdin.fd, 'utf8') "
                "to read stdin. Do NOT use '/dev/stdin' or 'readline'.\n"
            ),
            "python": (
                "- For Python use input() or sys.stdin for reading.\n"
            ),
        }
        return hints.get(language, "")
