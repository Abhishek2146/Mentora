"""
Coding Service - handles code execution and problem management
"""
import os
import subprocess
import tempfile
import resource
from typing import Dict, Any, Optional

from app.core.logger import get_logger

logger = get_logger(__name__)


class CodingService:
    def __init__(self):
        self.supported_languages = {
            "python": {"ext": "py", "cmd": "python"},
            "javascript": {"ext": "js", "cmd": "node"},
            "java": {"ext": "java", "cmd": "javac"},
            "cpp": {"ext": "cpp", "cmd": "g++"},
            "c": {"ext": "c", "cmd": "gcc"},
            "go": {"ext": "go", "cmd": "go"},
            "rust": {"ext": "rs", "cmd": "rustc"},
        }

    async def execute_code(
        self,
        problem_id: int,
        code: str,
        language: str,
    ) -> Dict[str, Any]:
        """Execute code and return result."""
        lang_info = self.supported_languages.get(language.lower())
        if not lang_info:
            return {
                "status": "error",
                "output": f"Language '{language}' not supported",
                "passed": False,
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            ext = lang_info["ext"]
            cmd = lang_info["cmd"]
            file_path = os.path.join(tmpdir, f"main.{ext}")

            with open(file_path, "w") as f:
                f.write(code)

            try:
                if language.lower() == "cpp":
                    compile_result = subprocess.run(
                        [cmd, "-std=c++17", file_path, "-o", os.path.join(tmpdir, "a.out")],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": compile_result.stderr,
                            "passed": False,
                        }
                    run_cmd = [os.path.join(tmpdir, "a.out")]
                elif language.lower() == "c":
                    compile_result = subprocess.run(
                        [cmd, file_path, "-o", os.path.join(tmpdir, "a.out")],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": compile_result.stderr,
                            "passed": False,
                        }
                    run_cmd = [os.path.join(tmpdir, "a.out")]
                elif language.lower() == "java":
                    run_cmd = [cmd, "Main"]
                    os.chdir(tmpdir)
                    class_file = file_path.replace(".java", ".class")
                    if os.path.exists(class_file):
                        run_cmd = ["java", "Main"]
                else:
                    run_cmd = [cmd, file_path]

                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tmpdir,
                )

                return {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "output": result.stdout + result.stderr,
                    "passed": result.returncode == 0,
                    "execution_time": result.returncode,
                    "memory_used": 0,
                }
            except subprocess.TimeoutExpired:
                return {
                    "status": "timeout",
                    "output": "Execution timed out",
                    "passed": False,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "output": str(e),
                    "passed": False,
                }

    async def generate_coding_problem(
        self, topic: str, difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """Generate a coding problem using AI."""
        from app.services.llm_service import LLMService
        llm = LLMService()

        prompt = f"""
Generate a coding problem about {topic} at {difficulty} difficulty.
Include: title, description, starter_code (in Python), test_cases (JSON array), and solution.
Return as JSON.
"""
        response = await llm.chat_completion([
            {"role": "system", "content": "You are a coding problem generator."},
            {"role": "user", "content": prompt},
        ])

        import json
        try:
            return json.loads(response.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return {"title": topic, "description": response, "starter_code": "", "test_cases": [], "solution": ""}
