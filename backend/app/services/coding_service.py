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
                details.append(f"Test {index}: passed")
            else:
                details.append(
                    f"Test {index}: failed\n"
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
        file_path = os.path.join(tmpdir, self._get_source_filename(language, ext))

        with open(file_path, "w", encoding="utf-8") as source_file:
            source_file.write(code)

        if language == "java":
            compile_result = subprocess.run(
                [lang_info["cmd"][0], file_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                return {
                    "status": "error",
                    "output": (compile_result.stdout or "") + (compile_result.stderr or ""),
                    "stdout": "",
                    "error_message": compile_result.stderr or "Compilation failed",
                }
            run_cmd = ["java", "Main"]

        elif language == "cpp":
            executable = os.path.join(tmpdir, "main.exe" if self.is_windows else "main")
            compile_result = subprocess.run(
                [lang_info["cmd"][0], "-std=c++17", file_path, "-o", executable],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                return {
                    "status": "error",
                    "output": (compile_result.stdout or "") + (compile_result.stderr or ""),
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
                timeout=10,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                return {
                    "status": "error",
                    "output": (compile_result.stdout or "") + (compile_result.stderr or ""),
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
                timeout=10,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                return {
                    "status": "error",
                    "output": (compile_result.stdout or "") + (compile_result.stderr or ""),
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
                timeout=10,
                cwd=tmpdir,
            )
            if compile_result.returncode != 0:
                return {
                    "status": "error",
                    "output": (compile_result.stdout or "") + (compile_result.stderr or ""),
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
        output = stdout + stderr
        passed = result.returncode == 0
        return {
            "status": "passed" if passed else "failed",
            "output": output,
            "stdout": stdout,
            "error_message": stderr or None,
        }

    @staticmethod
    def _normalize_output(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip())

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

    @staticmethod
    def _get_source_filename(language: str, extension: str) -> str:
        if language == "java":
            return "Main.java"
        return f"main.{extension}"

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
        if syllabus_id:
            problem.subject_id = None

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

        prompt = f"""
Generate a {difficulty} coding practice problem about "{topic}".
{context_line}
Target language: {language}

Return ONLY valid JSON (no markdown fences) with this structure:
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
- starter_code must compile/run in {language}.
- Do not include markdown code fences.
"""

        try:
            response = await llm.generate(prompt, temperature=0.4)
            cleaned = (
                response.replace("```json", "").replace("```", "").strip()
            )
            data = json.loads(cleaned)
            if not isinstance(data.get("test_cases"), list):
                data["test_cases"] = []
            if not isinstance(data.get("examples"), list):
                data["examples"] = []
            return data
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for coding problem.")
            raise ValueError(
                "AI returned an invalid problem format. Please try again."
            ) from None
        except Exception as exc:
            logger.exception("Failed to generate coding problem: %s", exc)
            raise
