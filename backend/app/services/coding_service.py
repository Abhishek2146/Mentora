# """
# Coding Service - handles code execution and problem management
# """
# import os
# import subprocess
# import tempfile
# import resource
# from typing import Dict, Any, Optional

# from app.core.logger import get_logger

# logger = get_logger(__name__)


# class CodingService:
#     def __init__(self):
#         self.supported_languages = {
#             "python": {"ext": "py", "cmd": "python"},
#             "javascript": {"ext": "js", "cmd": "node"},
#             "java": {"ext": "java", "cmd": "javac"},
#             "cpp": {"ext": "cpp", "cmd": "g++"},
#             "c": {"ext": "c", "cmd": "gcc"},
#             "go": {"ext": "go", "cmd": "go"},
#             "rust": {"ext": "rs", "cmd": "rustc"},
#         }

#     async def execute_code(
#         self,
#         problem_id: int,
#         code: str,
#         language: str,
#     ) -> Dict[str, Any]:
#         """Execute code and return result."""
#         lang_info = self.supported_languages.get(language.lower())
#         if not lang_info:
#             return {
#                 "status": "error",
#                 "output": f"Language '{language}' not supported",
#                 "passed": False,
#             }

#         with tempfile.TemporaryDirectory() as tmpdir:
#             ext = lang_info["ext"]
#             cmd = lang_info["cmd"]
#             file_path = os.path.join(tmpdir, f"main.{ext}")

#             with open(file_path, "w") as f:
#                 f.write(code)

#             try:
#                 if language.lower() == "cpp":
#                     compile_result = subprocess.run(
#                         [cmd, "-std=c++17", file_path, "-o", os.path.join(tmpdir, "a.out")],
#                         capture_output=True,
#                         text=True,
#                         timeout=10,
#                     )
#                     if compile_result.returncode != 0:
#                         return {
#                             "status": "error",
#                             "output": compile_result.stderr,
#                             "passed": False,
#                         }
#                     run_cmd = [os.path.join(tmpdir, "a.out")]
#                 elif language.lower() == "c":
#                     compile_result = subprocess.run(
#                         [cmd, file_path, "-o", os.path.join(tmpdir, "a.out")],
#                         capture_output=True,
#                         text=True,
#                         timeout=10,
#                     )
#                     if compile_result.returncode != 0:
#                         return {
#                             "status": "error",
#                             "output": compile_result.stderr,
#                             "passed": False,
#                         }
#                     run_cmd = [os.path.join(tmpdir, "a.out")]
#                 elif language.lower() == "java":
#                     run_cmd = [cmd, "Main"]
#                     os.chdir(tmpdir)
#                     class_file = file_path.replace(".java", ".class")
#                     if os.path.exists(class_file):
#                         run_cmd = ["java", "Main"]
#                 else:
#                     run_cmd = [cmd, file_path]

#                 result = subprocess.run(
#                     run_cmd,
#                     capture_output=True,
#                     text=True,
#                     timeout=30,
#                     cwd=tmpdir,
#                 )

#                 return {
#                     "status": "passed" if result.returncode == 0 else "failed",
#                     "output": result.stdout + result.stderr,
#                     "passed": result.returncode == 0,
#                     "execution_time": result.returncode,
#                     "memory_used": 0,
#                 }
#             except subprocess.TimeoutExpired:
#                 return {
#                     "status": "timeout",
#                     "output": "Execution timed out",
#                     "passed": False,
#                 }
#             except Exception as e:
#                 return {
#                     "status": "error",
#                     "output": str(e),
#                     "passed": False,
#                 }

#     async def generate_coding_problem(
#         self, topic: str, difficulty: str = "medium"
#     ) -> Dict[str, Any]:
#         """Generate a coding problem using AI."""
#         from app.services.llm_service import LLMService
#         llm = LLMService()

#         prompt = f"""
# Generate a coding problem about {topic} at {difficulty} difficulty.
# Include: title, description, starter_code (in Python), test_cases (JSON array), and solution.
# Return as JSON.
# """
#         response = await llm.chat_completion([
#             {"role": "system", "content": "You are a coding problem generator."},
#             {"role": "user", "content": prompt},
#         ])

#         import json
#         try:
#             return json.loads(response.replace("```json", "").replace("```", "").strip())
#         except json.JSONDecodeError:
#             return {"title": topic, "description": response, "starter_code": "", "test_cases": [], "solution": ""}


"""
Coding Service - handles code execution and problem management
"""

import json
import os
import platform
import subprocess
import tempfile
from typing import Any, Dict

from app.core.logger import get_logger


logger = get_logger(__name__)


class CodingService:
    """Service for coding practice and code execution."""

    def __init__(self):
        self.supported_languages = {
            "python": {
                "ext": "py",
                "cmd": "python",
            },
            "javascript": {
                "ext": "js",
                "cmd": "node",
            },
            "java": {
                "ext": "java",
                "cmd": "javac",
            },
            "cpp": {
                "ext": "cpp",
                "cmd": "g++",
            },
            "c": {
                "ext": "c",
                "cmd": "gcc",
            },
            "go": {
                "ext": "go",
                "cmd": "go",
            },
            "rust": {
                "ext": "rs",
                "cmd": "rustc",
            },
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
    ) -> Dict[str, Any]:
        """
        Execute submitted code and return the result.

        This implementation is intended for local development.
        Do not expose direct subprocess execution to untrusted
        users in production without a proper sandbox/container.
        """

        language = language.lower().strip()

        lang_info = self.supported_languages.get(language)

        if not lang_info:
            return {
                "status": "error",
                "output": (
                    f"Language '{language}' is not supported."
                ),
                "passed": False,
                "execution_time": 0,
                "memory_used": 0,
            }

        # Check whether required executable exists
        if not self._command_exists(lang_info["cmd"]):
            return {
                "status": "error",
                "output": (
                    f"Required executable '{lang_info['cmd']}' "
                    f"was not found on this system."
                ),
                "passed": False,
                "execution_time": 0,
                "memory_used": 0,
            }

        with tempfile.TemporaryDirectory() as tmpdir:

            ext = lang_info["ext"]

            file_path = os.path.join(
                tmpdir,
                self._get_source_filename(language, ext),
            )

            try:
                # ------------------------------------------------
                # Write source code
                # ------------------------------------------------

                with open(
                    file_path,
                    "w",
                    encoding="utf-8"
                ) as source_file:
                    source_file.write(code)

                # ------------------------------------------------
                # Java
                # ------------------------------------------------

                if language == "java":

                    compile_result = subprocess.run(
                        [
                            lang_info["cmd"],
                            file_path,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=tmpdir,
                    )

                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": (
                                compile_result.stdout
                                + compile_result.stderr
                            ),
                            "passed": False,
                            "execution_time": 0,
                            "memory_used": 0,
                        }

                    run_cmd = [
                        "java",
                        "Main",
                    ]

                # ------------------------------------------------
                # C++
                # ------------------------------------------------

                elif language == "cpp":

                    executable = os.path.join(
                        tmpdir,
                        "main.exe"
                        if self.is_windows
                        else "main",
                    )

                    compile_result = subprocess.run(
                        [
                            lang_info["cmd"],
                            "-std=c++17",
                            file_path,
                            "-o",
                            executable,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=tmpdir,
                    )

                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": (
                                compile_result.stdout
                                + compile_result.stderr
                            ),
                            "passed": False,
                            "execution_time": 0,
                            "memory_used": 0,
                        }

                    run_cmd = [executable]

                # ------------------------------------------------
                # C
                # ------------------------------------------------

                elif language == "c":

                    executable = os.path.join(
                        tmpdir,
                        "main.exe"
                        if self.is_windows
                        else "main",
                    )

                    compile_result = subprocess.run(
                        [
                            lang_info["cmd"],
                            file_path,
                            "-o",
                            executable,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=tmpdir,
                    )

                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": (
                                compile_result.stdout
                                + compile_result.stderr
                            ),
                            "passed": False,
                            "execution_time": 0,
                            "memory_used": 0,
                        }

                    run_cmd = [executable]

                # ------------------------------------------------
                # Go
                # ------------------------------------------------

                elif language == "go":

                    executable = os.path.join(
                        tmpdir,
                        "main.exe"
                        if self.is_windows
                        else "main",
                    )

                    compile_result = subprocess.run(
                        [
                            lang_info["cmd"],
                            "build",
                            "-o",
                            executable,
                            file_path,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=tmpdir,
                    )

                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": (
                                compile_result.stdout
                                + compile_result.stderr
                            ),
                            "passed": False,
                            "execution_time": 0,
                            "memory_used": 0,
                        }

                    run_cmd = [executable]

                # ------------------------------------------------
                # Rust
                # ------------------------------------------------

                elif language == "rust":

                    executable = os.path.join(
                        tmpdir,
                        "main.exe"
                        if self.is_windows
                        else "main",
                    )

                    compile_result = subprocess.run(
                        [
                            lang_info["cmd"],
                            file_path,
                            "-o",
                            executable,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=tmpdir,
                    )

                    if compile_result.returncode != 0:
                        return {
                            "status": "error",
                            "output": (
                                compile_result.stdout
                                + compile_result.stderr
                            ),
                            "passed": False,
                            "execution_time": 0,
                            "memory_used": 0,
                        }

                    run_cmd = [executable]

                # ------------------------------------------------
                # Python / JavaScript
                # ------------------------------------------------

                else:

                    run_cmd = [
                        lang_info["cmd"],
                        file_path,
                    ]

                # ------------------------------------------------
                # Execute program
                # ------------------------------------------------

                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tmpdir,
                )

                output = (
                    result.stdout
                    + result.stderr
                ).strip()

                return {
                    "status": (
                        "passed"
                        if result.returncode == 0
                        else "failed"
                    ),
                    "output": output,
                    "passed": result.returncode == 0,
                    "execution_time": 0,
                    "memory_used": 0,
                }

            except subprocess.TimeoutExpired:

                logger.warning(
                    "Code execution timed out for "
                    "problem_id=%s, language=%s",
                    problem_id,
                    language,
                )

                return {
                    "status": "timeout",
                    "output": "Execution timed out.",
                    "passed": False,
                    "execution_time": 30,
                    "memory_used": 0,
                }

            except Exception as exc:

                logger.exception(
                    "Code execution failed: %s",
                    exc,
                )

                return {
                    "status": "error",
                    "output": str(exc),
                    "passed": False,
                    "execution_time": 0,
                    "memory_used": 0,
                }

    # ============================================================
    # Helper Methods
    # ============================================================

    @staticmethod
    def _command_exists(command: str) -> bool:
        """Check whether a command is available."""

        from shutil import which

        return which(command) is not None

    @staticmethod
    def _get_source_filename(
        language: str,
        extension: str,
    ) -> str:
        """
        Return the appropriate source filename.

        Java requires Main.java because the code is expected
        to contain a public class named Main.
        """

        if language == "java":
            return "Main.java"

        return f"main.{extension}"

    # ============================================================
    # AI Coding Problem Generation
    # ============================================================

    async def generate_coding_problem(
        self,
        topic: str,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        """
        Generate a coding problem using the LLM service.
        """

        from app.services.llm_service import LLMService

        llm = LLMService()

        prompt = f"""
Generate a coding problem about {topic}
at {difficulty} difficulty.

Return ONLY valid JSON with the following fields:

{{
    "title": "Problem title",
    "description": "Problem description",
    "starter_code": "Python starter code",
    "test_cases": [],
    "solution": "Python solution"
}}

Do not include markdown code fences.
"""

        try:
            response = await llm.generate(prompt)

            cleaned_response = (
                response
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            return json.loads(cleaned_response)

        except json.JSONDecodeError:

            logger.warning(
                "LLM returned invalid JSON for coding problem."
            )

            return {
                "title": topic,
                "description": response,
                "starter_code": "",
                "test_cases": [],
                "solution": "",
            }

        except Exception as exc:

            logger.exception(
                "Failed to generate coding problem: %s",
                exc,
            )

            return {
                "title": topic,
                "description": (
                    "Unable to generate coding problem "
                    "at this time."
                ),
                "starter_code": "",
                "test_cases": [],
                "solution": "",
            }

