"""
Jerry's File Operations Tool
Search, read, managed (copy/move/delete), and list files.
"""

import os
import shutil
import logging
import glob
from pathlib import Path
from typing import Optional

from jerry.tools.base import Tool

logger = logging.getLogger("jerry.tools.file_ops")


def _check_sandbox(path: str, sandbox_dir: str) -> bool:
    """Check whether a path is inside the sandbox directory."""
    try:
        resolved = Path(path).resolve()
        sandbox = Path(sandbox_dir).resolve()
        # Check the path starts with (is inside) the sandbox
        return str(resolved).startswith(str(sandbox))
    except Exception:
        return False


def _resolve_sandbox_path(file_path: str, sandbox_dir: str) -> str:
    """If a path is relative or a bare filename, resolve it into the sandbox directory."""
    # Expand ~ to home dir so we can check it properly
    file_path = file_path.replace('~', os.path.expanduser('~'))
    
    # If it's already an absolute path, return as-is (sandbox check happens separately)
    if os.path.isabs(file_path):
        return file_path
    
    # For relative paths, join with sandbox dir
    resolved = str(Path(sandbox_dir) / file_path)
    
    # Guard against double-nesting: if the LLM sent "testFile/tom" and sandbox is
    # ".../testFile", we'd get ".../testFile/testFile/tom". Detect and fix this.
    sandbox_name = Path(sandbox_dir).name  # e.g. "testFile"
    parts = Path(file_path).parts
    if parts and parts[0] == sandbox_name:
        # The LLM already included the sandbox folder name, strip it
        inner = str(Path(*parts[1:])) if len(parts) > 1 else ""
        resolved = str(Path(sandbox_dir) / inner) if inner else sandbox_dir

    return resolved


class SearchFilesTool(Tool):
    """Tool to search for files by name."""

    name = "search_files"
    description = "Search for files on the computer by name or pattern. Returns matching file paths."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "File name or pattern to search for (e.g., '*.py', 'report.docx', 'budget*')",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in. Defaults to user's home directory.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default: 20",
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, directory: str = "", max_results: int = 20) -> str:
        search_dir = directory or os.path.expanduser("~")
        
        if not os.path.exists(search_dir):
            return f"❌ Directory doesn't exist: {search_dir}"

        results = []
        
        try:
            for root, dirs, files in os.walk(search_dir):
                # Skip hidden and system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
                    'node_modules', '__pycache__', '.git', 'AppData', '$Recycle.Bin',
                    'Windows', 'Program Files', 'Program Files (x86)',
                )]
                
                for filename in files:
                    if self._matches(filename, query):
                        filepath = os.path.join(root, filename)
                        try:
                            size = os.path.getsize(filepath)
                            results.append((filepath, size))
                        except OSError:
                            results.append((filepath, 0))
                    
                    if len(results) >= max_results:
                        break
                
                if len(results) >= max_results:
                    break
        except PermissionError:
            pass

        if not results:
            return f"🔍 No files found matching '{query}' in {search_dir}"

        parts = [f"🔍 Found {len(results)} file(s) matching '{query}':"]
        for filepath, size in results:
            size_str = self._format_size(size)
            parts.append(f"  📄 {filepath} ({size_str})")

        return "\n".join(parts)

    def _matches(self, filename: str, query: str) -> bool:
        """Check if filename matches the search query."""
        query_lower = query.lower()
        filename_lower = filename.lower()
        
        # Glob pattern match
        if '*' in query or '?' in query:
            import fnmatch
            return fnmatch.fnmatch(filename_lower, query_lower)
        
        # Substring match
        return query_lower in filename_lower

    def _format_size(self, size: int) -> str:
        """Format file size to human readable."""
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


class ReadFileTool(Tool):
    """Tool to read file contents."""

    name = "read_file"
    description = "Read the contents of a text file. Good for checking file contents, reading configs, viewing code, etc."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full path to the file to read",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read. Default: 100",
                },
            },
            "required": ["file_path"],
        }

    def execute(self, file_path: str, max_lines: int = 100) -> str:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        
        if not os.path.isfile(file_path):
            return f"❌ Not a file: {file_path}"
        
        # Check file size
        size = os.path.getsize(file_path)
        if size > 1_000_000:  # 1MB limit
            return f"⚠️ File is too large ({size / 1_000_000:.1f}MB). I can only read files under 1MB to avoid memory issues."
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            shown_lines = lines[:max_lines]
            content = ''.join(shown_lines)
            
            result = f"📄 **{os.path.basename(file_path)}** ({total_lines} lines)\n"
            result += "```\n" + content + "\n```"
            
            if total_lines > max_lines:
                result += f"\n\n... ({total_lines - max_lines} more lines not shown)"
            
            return result

        except Exception as e:
            return f"❌ Error reading file: {e}"


class ListDirectoryTool(Tool):
    """Tool to list directory contents."""

    name = "list_directory"
    description = "List the contents of a directory (files and folders). Good for exploring the file system."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the directory to list. Defaults to user's home directory.",
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Whether to show hidden files. Default: false",
                },
            },
            "required": [],
        }

    def execute(self, directory: str = "", show_hidden: bool = False) -> str:
        dir_path = directory or os.path.expanduser("~")
        
        if not os.path.exists(dir_path):
            return f"❌ Directory doesn't exist: {dir_path}"
        
        if not os.path.isdir(dir_path):
            return f"❌ Not a directory: {dir_path}"

        try:
            entries = sorted(os.listdir(dir_path))
            
            if not show_hidden:
                entries = [e for e in entries if not e.startswith('.')]
            
            folders = []
            files = []
            
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                try:
                    if os.path.isdir(full_path):
                        count = len(os.listdir(full_path))
                        folders.append(f"  📁 {entry}/ ({count} items)")
                    else:
                        size = os.path.getsize(full_path)
                        size_str = self._format_size(size)
                        folders_or_files_icon = "📄"
                        # Pick icon by extension
                        ext = os.path.splitext(entry)[1].lower()
                        if ext in ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs'):
                            folders_or_files_icon = "💻"
                        elif ext in ('.jpg', '.png', '.gif', '.bmp', '.svg'):
                            folders_or_files_icon = "🖼️"
                        elif ext in ('.mp3', '.wav', '.flac', '.m4a'):
                            folders_or_files_icon = "🎵"
                        elif ext in ('.mp4', '.mkv', '.avi', '.mov'):
                            folders_or_files_icon = "🎬"
                        elif ext in ('.zip', '.rar', '.7z', '.tar', '.gz'):
                            folders_or_files_icon = "📦"
                        elif ext in ('.pdf',):
                            folders_or_files_icon = "📕"
                        elif ext in ('.doc', '.docx', '.txt', '.md'):
                            folders_or_files_icon = "📝"
                            
                        files.append(f"  {folders_or_files_icon} {entry} ({size_str})")
                except PermissionError:
                    files.append(f"  🔒 {entry} (access denied)")

            parts = [f"📂 **{dir_path}** ({len(folders)} folders, {len(files)} files)"]
            if folders:
                parts.append("\n  **Folders:**")
                parts.extend(folders[:50])
            if files:
                parts.append("\n  **Files:**")
                parts.extend(files[:50])
            
            total = len(folders) + len(files)
            if total > 100:
                parts.append(f"\n  ... and {total - 100} more items")

            return "\n".join(parts)

        except PermissionError:
            return f"🔒 Access denied to: {dir_path}"
        except Exception as e:
            return f"❌ Error: {e}"

    def _format_size(self, size: int) -> str:
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


class CopyFileTool(Tool):
    """Tool to copy files or directories."""

    name = "copy_file"
    description = "Copy a file or directory to a new location. Destination must be inside the sandbox."

    def __init__(self, sandbox_dir: str = ""):
        self.sandbox_dir = sandbox_dir

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Path to source file/folder",
                },
                "destination": {
                    "type": "string",
                    "description": "Path to destination",
                },
            },
            "required": ["source", "destination"],
        }

    def execute(self, source: str, destination: str) -> str:
        if self.sandbox_dir:
            destination = _resolve_sandbox_path(destination, self.sandbox_dir)
            if not _check_sandbox(destination, self.sandbox_dir):
                return f"🚫 Blocked: I can only copy files into my sandbox folder ({self.sandbox_dir}). Destination '{destination}' is outside the sandbox."

        if not os.path.exists(source):
            return f"❌ Source not found: {source}"
        
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
                return f"✅ Directory copied from {source} to {destination}"
            else:
                shutil.copy2(source, destination)
                return f"✅ File copied from {source} to {destination}"
        except Exception as e:
            return f"❌ Copy failed: {e}"


class MoveFileTool(Tool):
    """Tool to move or rename files."""

    name = "move_file"
    description = "Move or rename a file or directory. Both source and destination must be inside the sandbox."

    def __init__(self, sandbox_dir: str = ""):
        self.sandbox_dir = sandbox_dir

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Path to source file/folder",
                },
                "destination": {
                    "type": "string",
                    "description": "Path to destination (new path or name)",
                },
            },
            "required": ["source", "destination"],
        }

    def execute(self, source: str, destination: str) -> str:
        if self.sandbox_dir:
            source = _resolve_sandbox_path(source, self.sandbox_dir)
            destination = _resolve_sandbox_path(destination, self.sandbox_dir)
            if not _check_sandbox(source, self.sandbox_dir):
                return f"🚫 Blocked: I can only move files within my sandbox folder ({self.sandbox_dir}). Source '{source}' is outside the sandbox."
            if not _check_sandbox(destination, self.sandbox_dir):
                return f"🚫 Blocked: I can only move files within my sandbox folder ({self.sandbox_dir}). Destination '{destination}' is outside the sandbox."

        if not os.path.exists(source):
            return f"❌ Source not found: {source}"
        
        try:
            shutil.move(source, destination)
            return f"✅ Moved/Renamed {source} to {destination}"
        except Exception as e:
            return f"❌ Move failed: {e}"


class DeleteFileTool(Tool):
    """Tool to delete files or directories."""

    name = "delete_file"
    description = "Delete a file or directory. Only works inside the sandbox. WARNING: This action is permanent."

    def __init__(self, sandbox_dir: str = ""):
        self.sandbox_dir = sandbox_dir

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Path to file or folder to delete",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to proceed with deletion",
                },
            },
            "required": ["target", "confirm"],
        }

    def execute(self, target: str, confirm: bool = False) -> str:
        # Handle LLM sending confirm as string instead of bool
        if isinstance(confirm, str):
            confirm = confirm.lower() in ('true', '1', 'yes')
        if not confirm:
            return "⚠️ Deletion cancelled. You must set 'confirm' to true."

        if self.sandbox_dir:
            target = _resolve_sandbox_path(target, self.sandbox_dir)
            if not _check_sandbox(target, self.sandbox_dir):
                return f"🚫 Blocked: I can only delete files inside my sandbox folder ({self.sandbox_dir}). Target '{target}' is outside the sandbox."
            
        if not os.path.exists(target):
            return f"❌ Target not found: {target}"
        
        # Safety check for root or obvious system paths
        target_abs = os.path.abspath(target)
        if target_abs.count(os.sep) < 3:
            return f"🚫 Blocked: Deleting '{target}' seems too dangerous via AI tool."
            
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
                return f"🗑️ Directory deleted: {target}"
            else:
                os.remove(target)
                return f"🗑️ File deleted: {target}"
        except Exception as e:
            return f"❌ Deletion failed: {e}"


class CreateFileTool(Tool):
    """Tool to create a new file with content."""

    name = "create_file"
    description = "Create a new file with the given content. Only works inside the sandbox directory."

    def __init__(self, sandbox_dir: str = ""):
        self.sandbox_dir = sandbox_dir

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path for the new file (can be just a filename — it will be created inside the sandbox)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    def execute(self, file_path: str, content: str = "") -> str:
        # If the user gives just a filename (no directory), place it in the sandbox
        if not os.path.isabs(file_path) and os.sep not in file_path and '/' not in file_path:
            file_path = os.path.join(self.sandbox_dir, file_path)

        if self.sandbox_dir and not _check_sandbox(file_path, self.sandbox_dir):
            return f"🚫 Blocked: I can only create files inside my sandbox folder ({self.sandbox_dir}). Path '{file_path}' is outside the sandbox."

        try:
            # Create parent directories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ File created: {file_path}"
        except Exception as e:
            return f"❌ Failed to create file: {e}"


class WriteFileTool(Tool):
    """Tool to write/edit content in an existing file."""

    name = "write_file"
    description = "Write or append content to a file. Only works inside the sandbox directory."

    def __init__(self, sandbox_dir: str = ""):
        self.sandbox_dir = sandbox_dir

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write to",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write",
                },
                "mode": {
                    "type": "string",
                    "description": "Write mode: 'overwrite' replaces the file, 'append' adds to the end. Default: 'overwrite'",
                },
            },
            "required": ["file_path", "content"],
        }

    def execute(self, file_path: str, content: str, mode: str = "overwrite") -> str:
        # If the user gives just a filename, place it in the sandbox
        if not os.path.isabs(file_path) and os.sep not in file_path and '/' not in file_path:
            file_path = os.path.join(self.sandbox_dir, file_path)

        if self.sandbox_dir and not _check_sandbox(file_path, self.sandbox_dir):
            return f"🚫 Blocked: I can only write to files inside my sandbox folder ({self.sandbox_dir}). Path '{file_path}' is outside the sandbox."

        try:
            write_mode = 'a' if mode == "append" else 'w'
            with open(file_path, write_mode, encoding='utf-8') as f:
                f.write(content)
            action = "appended to" if mode == "append" else "written to"
            return f"✅ Content {action}: {file_path}"
        except Exception as e:
            return f"❌ Failed to write file: {e}"

