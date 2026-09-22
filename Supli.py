#!/usr/bin/env python3
import json
import platform
import subprocess
import sys
from pathlib import Path
import requests

MODEL = "hf.co/saidutta69/Qwen2.5-Coder-7B-Instruct-heretic:Q4_K_M"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
WORKSPACE = Path.home() / "Supli"
SKILL_FILE = WORKSPACE / "Agent" / "SKILL.md"

def load_skill():
    try:
        return SKILL_FILE.read_text(encoding="utf-8")
    except Exception as exc:
        return f"SKILL.md not found: {exc}"

def is_inside_workspace(path):
    try:
        Path(path).expanduser().resolve().relative_to(WORKSPACE.resolve())
        return True
    except ValueError:
        return False

def list_directory(path="."):
    p = Path(path).expanduser()
    if not is_inside_workspace(p):
        return {"error": "Access denied: path is outside the Supli workspace."}
    if not p.exists():
        return {"error": f"Path does not exist: {p}"}
    if not p.is_dir():
        return {"error": f"Not a directory: {p}"}
    return {"path": str(p.resolve()), "entries": [
        {"name": x.name, "type": "directory" if x.is_dir() else "file"}
        for x in sorted(p.iterdir(), key=lambda x: x.name.lower())
    ]}

def read_file(path):
    p = Path(path).expanduser()
    if not is_inside_workspace(p):
        return {"error": "Access denied: path is outside the Supli workspace."}
    if not p.is_file():
        return {"error": f"File does not exist: {p}"}
    try:
        return {"path": str(p.resolve()), "content": p.read_text(encoding="utf-8")}
    except Exception as exc:
        return {"error": f"Could not read file: {exc}"}

def diff_file(path, new_content):
    p = Path(path).expanduser()
    if not is_inside_workspace(p):
        return {"error": "Access denied: path is outside the Supli workspace."}
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    import difflib
    return {"path": str(p.resolve()), "diff": "".join(difflib.unified_diff(
        old.splitlines(True), new_content.splitlines(True),
        fromfile=str(p), tofile=str(p) + " (proposed)"
    ))}

def write_file(path, content):
    p = Path(path).expanduser()
    if not is_inside_workspace(p):
        return {"error": "Access denied: path is outside the Supli workspace."}
    if p.exists() and p.is_dir():
        return {"error": f"Cannot write to a directory: {p}"}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p.resolve()), "written": True}
    except Exception as exc:
        return {"error": f"Could not write file: {exc}"}

def run_command(command):
    command = command.strip()
    if not command:
        return {"error": "No command provided."}
    low = command.lower()
    if "git push" in low or "git pull" in low:
        return {"error": "Blocked command: git push/git pull"}
    if any(x in low for x in (" xcode-select", " sudo ", "sudo ", "cd ", "pushd ", "popd ")):
        return {"error": "Blocked command by Supli safety policy."}
    try:
        r = subprocess.run(command, shell=True, cwd=WORKSPACE,
                           capture_output=True, text=True, timeout=300)
        return {"command": command, "returncode": r.returncode,
                "stdout": r.stdout, "stderr": r.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 300 seconds."}
    except Exception as exc:
        return {"error": f"Could not run command: {exc}"}

def get_platform_info():
    return {"system": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "python": platform.python_version()}

def platform_home():
    return str(Path.home())

def platform_shell():
    import os
    return os.environ.get("SHELL") or ("cmd.exe" if platform.system() == "Windows" else "/bin/sh")

def platform_summary():
    info = get_platform_info()
    info.update({"home": platform_home(), "shell": platform_shell()})
    return info

def ask_qwen(messages, tools=None):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    response = requests.post(OLLAMA_URL, json=payload, timeout=600)
    response.raise_for_status()
    return response.json()

def run_agent(user_request, max_steps=8):
    messages = [
        {"role": "system", "content":
         "You are Supli, a careful local coding agent. Inspect real files before changing them. "
         "Never invent tool results. Workspace is " + str(WORKSPACE) + "\n\n" + load_skill()},
        {"role": "user", "content": user_request},
    ]
    tools = [
        {"type":"function","function":{"name":"list_directory","description":"Inspect a workspace directory.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"read_file","description":"Read a workspace file.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"Write a workspace file. Use only after required approval.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"run_command","description":"Run a controlled workspace command.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
        {"type":"function","function":{"name":"get_platform_info","description":"Return actual platform information.","parameters":{"type":"object","properties":{}}}},
    ]
    for _ in range(max_steps):
        result = ask_qwen(messages, tools)
        message = result.get("message", {})
        calls = message.get("tool_calls", [])
        if not calls:
            return message.get("content", "").strip()
        messages.append(message)
        for call in calls:
            fn = call.get("function", {})
            name, args = fn.get("name"), fn.get("arguments", {})
            if name == "list_directory": out = list_directory(args.get("path", "."))
            elif name == "read_file": out = read_file(args.get("path", ""))
            elif name == "write_file": out = write_file(args.get("path", ""), args.get("content", ""))
            elif name == "run_command": out = run_command(args.get("command", ""))
            elif name == "get_platform_info": out = platform_summary()
            else: out = {"error": f"Unknown tool: {name}"}
            messages.append({"role":"tool","content":json.dumps(out, ensure_ascii=False)})
    return "Supli stopped: maximum tool steps reached."

if __name__ == "__main__":
    print("Supli")
    print(f"Model: {MODEL}")
    print(f"Workspace: {WORKSPACE}")
    if len(sys.argv) > 1:
        print(run_agent(" ".join(sys.argv[1:])))
