"""
Coding Service - problem execution helper.

NOTE: Executing arbitrary user code directly on the API host is unsafe.
For production, run this service inside an isolated sandbox/container.
"""
import os
import subprocess
import tempfile
import time
from typing import Dict, Any


class CodingService:
    def __init__(self):
        self.supported_languages = {
            "python": {"ext": "py", "cmd": ["python"]},
            "javascript": {"ext": "js", "cmd": ["node"]},
            "java": {"ext": "java", "cmd": ["java"]},
            "cpp": {"ext": "cpp", "cmd": ["g++"]},
            "c": {"ext": "c", "cmd": ["gcc"]},
            "go": {"ext": "go", "cmd": ["go"]},
            "rust": {"ext": "rs", "cmd": ["rustc"]},
        }

    async def execute_code(self, problem_id: int, code: str, language: str) -> Dict[str, Any]:
        language = language.lower().strip()
        info = self.supported_languages.get(language)
        if not info:
            return {"status": "error", "output": f"Language '{language}' not supported", "passed": False}

        start = time.perf_counter()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ext = info["ext"]
                source = os.path.join(tmpdir, f"Main.{ext}" if language == "java" else f"main.{ext}")
                with open(source, "w", encoding="utf-8") as fh:
                    fh.write(code)

                if language in {"cpp", "c"}:
                    binary = os.path.join(tmpdir, "main.exe" if os.name == "nt" else "main")
                    compiler = info["cmd"][0]
                    compile_cmd = [compiler, source, "-o", binary]
                    if language == "cpp":
                        compile_cmd.insert(1, "-std=c++17")
                    compile_result = subprocess.run(
                        compile_cmd, capture_output=True, text=True, timeout=10, cwd=tmpdir
                    )
                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": compile_result.stderr,
                            "passed": False,
                            "execution_time": int((time.perf_counter() - start) * 1000),
                            "error_message": compile_result.stderr,
                        }
                    run_cmd = [binary]
                elif language == "java":
                    compile_result = subprocess.run(
                        ["javac", source], capture_output=True, text=True, timeout=10, cwd=tmpdir
                    )
                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": compile_result.stderr,
                            "passed": False,
                            "execution_time": int((time.perf_counter() - start) * 1000),
                            "error_message": compile_result.stderr,
                        }
                    run_cmd = ["java", "-cp", tmpdir, "Main"]
                elif language == "rust":
                    binary = os.path.join(tmpdir, "main.exe" if os.name == "nt" else "main")
                    subprocess.run(
                        ["rustc", source, "-o", binary],
                        capture_output=True, text=True, timeout=10, cwd=tmpdir, check=True,
                    )
                    run_cmd = [binary]
                elif language == "go":
                    # go run executes and compiles the source in one step.
                    run_cmd = ["go", "run", source]
                else:
                    run_cmd = info["cmd"] + [source]

                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tmpdir,
                )
                elapsed = int((time.perf_counter() - start) * 1000)
                output = (result.stdout or "") + (result.stderr or "")
                passed = result.returncode == 0
                return {
                    "status": "passed" if passed else "failed",
                    "output": output,
                    "passed": passed,
                    "score": 100 if passed else 0,
                    "execution_time": elapsed,
                    "error_message": result.stderr or None,
                    "passed_test_cases": 0,
                    "total_test_cases": 0,
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "output": "Execution timed out", "passed": False}
        except Exception as exc:
            return {"status": "error", "output": str(exc), "passed": False, "error_message": str(exc)}

    async def generate_coding_problem(self, topic: str, difficulty: str = "medium") -> Dict[str, Any]:
        import json
        from app.services.llm_service import LLMService

        llm = LLMService()
        prompt = (
            f"Generate a coding problem about {topic} at {difficulty} difficulty. "
            "Return JSON with title, description, starter_code, test_cases, solution_code."
        )
        response = await llm.chat_completion([
            {"role": "system", "content": "You are a coding problem generator."},
            {"role": "user", "content": prompt},
        ])
        try:
            return json.loads(response.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return {
                "title": topic,
                "description": response,
                "starter_code": "",
                "test_cases": [],
                "solution_code": "",
            }
