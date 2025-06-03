#!/usr/bin/env python3

import os
import fnmatch
from pathlib import Path
import argparse

# --- Configuration ---
DEFAULT_CONFIG_FILENAME = ".codegatherignore"
DEFAULT_INIT_SESSION_PROMPT_FILENAME = ".codegather_session_prompt.txt" # For the init command
DEFAULT_OUTPUT_FILENAME = "combined_code.txt"
DEFAULT_NO_HEADER_STATE = False
DEFAULT_ENCODING = 'utf-8'
DEFAULT_SCRIPT_INCLUDE_EXTENSIONS = ["*.js", "*.jsx"] # Fallback if no includes in config
SESSION_PROMPT_CODE_SEPARATOR = "\n\n--> code files combine starts here: <--\n\n"
FILES_COUNT_WARNING_THRESHOLD = 300

DEFAULT_CONFIG_TEMPLATE = """\
# CodeGather Configuration File (.codegatherignore)
# This file defines how codegather processes your project.

# --- General Configuration ---
# These settings can be overridden by command-line arguments.
# Uncomment and set values as needed.

# output_file: combined_project_code.txt
session_prompt_file: .codegather_session_prompt.txt # Default name created by 'init'
# no_header: false
# default_extensions: *.py, *.ts # Alternative: define default extensions here

# --- File Types to Include ---
# Add glob patterns for file extensions you want to include (one per line).
# If any patterns are listed here, they take precedence over 'default_extensions'.
# Examples:
*.js
*.jsx
# *.py
# *.ts
# *.html
# *.css

# --- Files and Directories to Exclude ---
# Add glob patterns for files or directories to exclude (one per line).
# Directory patterns should end with a '/' (e.g., node_modules/).
node_modules/
.git/
dist/
build/
venv/
__pycache__/
*.log
*.tmp
# combined_code.txt # Good practice to exclude the default output file name
# .codegather_session_prompt.txt # Also exclude your session prompt file itself
.DS_Store
"""

DEFAULT_SESSION_PROMPT_TEMPLATE = """\
Hello,

This file consist of combined codebase and configuration files for a project I am working on. Familiarize yourself with its current functionalities, capabilities, configurations, imports, logic, and styling.

Project Context:

Name: [root directory name]
Stack: # e.g., react native, firebase, expo
Configuration: # e.g., developer build, JS files

Please follow below rules for today coding session:
When outputting code, please provide full code files (e.g., App.js) so I can copy-paste directly to my IDE for testing. If a change involves multiple code blocks (render, hooks, imports, etc.), output the full file. For isolated changes, a snippet is fine. Specify any additional implementation steps clearly.

Please maintain existing styling and do not alter current logic unless instructed or necessery for requested functionality. Prompt for any necessary additional information/files. I expect production-ready, clear code and instructions. Keep responses concise unless I request an opinion.
Do not put /cite [number] in code output - I am pasting this code into IDE for testing, and don't want artifacts there.
In chat I will specify my request.
Thank you.
"""

# --- Helper Functions ---

def parse_config(config_file_path: Path, verbose: bool = False):
    loaded_config_settings = {
        "output_file": None,
        "no_header": None,
        "default_extensions_str": None,
        "session_prompt_file": None
    }
    include_extension_patterns = [] # For patterns like *.js directly listed
    exclude_patterns = []

    if config_file_path.is_file():
        if verbose: print(f"⚙️ Reading config file: {config_file_path}")
        with open(config_file_path, 'r', encoding=DEFAULT_ENCODING) as f:
            for line_num, line_content in enumerate(f, 1):
                stripped_line = line_content.strip()
                if not stripped_line or stripped_line.startswith('#'): # Skip full-line comments and empty lines
                    continue
                
                # Handle key-value pairs
                if ':' in stripped_line:
                    key_raw, value_raw = stripped_line.split(':', 1)
                    key = key_raw.strip().lower().replace('-', '_')

                    # Strip inline comments from the value part
                    if '#' in value_raw:
                        value = value_raw.split('#', 1)[0].strip()
                    else:
                        value = value_raw.strip()

                    if key == "output_file":
                        loaded_config_settings["output_file"] = value
                    elif key == "no_header":
                        loaded_config_settings["no_header"] = value.lower() in ['true', 'yes', '1', 'on']
                    elif key == "default_extensions":
                        loaded_config_settings["default_extensions_str"] = value
                    elif key == "session_prompt_file":
                        loaded_config_settings["session_prompt_file"] = value
                    
                    if verbose and key in loaded_config_settings:
                         print(f"  Config: {key} = {loaded_config_settings[key]}")
                    continue # Move to next line after processing key-value

                # If not a key-value (and not comment/empty), treat as include/exclude pattern
                # This assumes simple file extension patterns are for inclusion if they start with *.
                # More complex patterns or directory patterns are treated as exclusions.
                if stripped_line.startswith("*.") and '/' not in stripped_line and '\\' not in stripped_line:
                    ext_part = stripped_line[2:]
                    # A simple check for typical extension characters
                    if ext_part and all(c.isalnum() or c == '.' for c in ext_part):
                        if verbose: print(f"  Config: Adding include extension pattern: {stripped_line}")
                        include_extension_patterns.append(stripped_line)
                    else: # Treat as exclusion if it's like "*.log.*" or other complex pattern
                        if verbose: print(f"  Config: Adding exclusion pattern (complex '*.ext'): {stripped_line}")
                        exclude_patterns.append(stripped_line)
                else: # Treat as exclusion (directory, specific file, complex glob)
                    if verbose: print(f"  Config: Adding exclusion pattern: {stripped_line}")
                    exclude_patterns.append(stripped_line)
    elif verbose:
        print(f"ℹ️ Config file '{config_file_path}' not found or not specified. Using script defaults for includes/excludes.")

    # Determine final include_extension_patterns
    final_include_extensions = []
    if include_extension_patterns: # Explicit *.ext patterns from config take precedence
        final_include_extensions.extend(include_extension_patterns)
        if verbose: print(f"  Config: Using explicit include extension patterns from file: {final_include_extensions}")
    elif loaded_config_settings["default_extensions_str"]: # Then 'default_extensions' key
        ext_list_str = loaded_config_settings["default_extensions_str"]
        raw_ext_list = [ext.strip() for ext in ext_list_str.split(',') if ext.strip()]
        for e in raw_ext_list:
            if e.startswith("*."): final_include_extensions.append(e)
            elif e.startswith("."): final_include_extensions.append(f"*{e}") # .ext -> *.ext
            else: final_include_extensions.append(f"*.{e}") # ext -> *.ext
        if verbose: print(f"  Config: Using 'default_extensions' from config: {final_include_extensions}")
    else: # Fallback to script defaults if no include config found
        final_include_extensions.extend(DEFAULT_SCRIPT_INCLUDE_EXTENSIONS)
        if verbose: print(f"  Config: No specific include patterns in config, using script defaults: {final_include_extensions}")
    
    return loaded_config_settings, final_include_extensions, exclude_patterns


def is_excluded(item_path_abs: Path, root_path_abs: Path, exclude_patterns: list, output_file_path_abs: Path, verbose: bool = False) -> bool:
    if item_path_abs == output_file_path_abs: # pragma: no cover (hard to test this specific scenario reliably)
        if verbose: print(f"DEBUG: Excluding output file itself: {item_path_abs.relative_to(root_path_abs) if item_path_abs.is_relative_to(root_path_abs) else item_path_abs}")
        return True
    try:
        relative_item_path = item_path_abs.relative_to(root_path_abs)
    except ValueError: # pragma: no cover
        if verbose: print(f"DEBUG: Item '{item_path_abs}' is not relative to root '{root_path_abs}'. Treating as excluded.")
        return True
    
    # Normalize path separators for cross-platform pattern matching
    relative_item_path_str_normalized = str(relative_item_path).replace('\\', '/')

    for pattern_idx, pattern_orig in enumerate(exclude_patterns):
        p_stripped = pattern_orig.strip()
        if not p_stripped: continue

        p_normalized = p_stripped.replace('\\', '/') # Normalize pattern separators

        is_dir_specific_pattern = p_normalized.endswith('/')
        
        # Match full path for directory patterns or patterns containing '/'
        if is_dir_specific_pattern or '/' in p_normalized:
            p_to_match = p_normalized.rstrip('/') # For dir match "foo/" against "foo" or "foo/bar"
            if is_dir_specific_pattern:
                 # Match if the path is the directory itself or is inside the directory
                if relative_item_path_str_normalized == p_to_match or \
                   relative_item_path_str_normalized.startswith(p_to_match + '/'):
                    if verbose: print(f"DEBUG: Path '{relative_item_path}' excluded by directory pattern '{pattern_orig}' (rule #{pattern_idx})")
                    return True
            elif fnmatch.fnmatchcase(relative_item_path_str_normalized, p_normalized):
                if verbose: print(f"DEBUG: Path '{relative_item_path}' excluded by full path glob pattern '{pattern_orig}' (rule #{pattern_idx})")
                return True
        # If pattern does not contain path separators, also try matching just the basename
        elif '/' not in p_normalized: # implies also not dir_specific_pattern from above
            if fnmatch.fnmatchcase(item_path_abs.name, p_stripped): # Use original stripped pattern for basename
                if verbose: print(f"DEBUG: File/Dir name '{item_path_abs.name}' (in path '{relative_item_path}') excluded by basename pattern '{pattern_orig}' (rule #{pattern_idx})")
                return True
    return False

# --- Command Handler Functions ---

def handle_init_command(args):
    print("🚀 Initializing CodeGather project...")
    try:
        init_root_path = Path(args.root_dir).resolve()
        init_root_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Error: Could not access or create root directory '{args.root_dir}': {e}")
        return

    files_to_create = [
        (init_root_path / DEFAULT_CONFIG_FILENAME, DEFAULT_CONFIG_TEMPLATE, "config"),
        (init_root_path / DEFAULT_INIT_SESSION_PROMPT_FILENAME, DEFAULT_SESSION_PROMPT_TEMPLATE, "session prompt")
    ]

    for file_path, template_content, file_type_label in files_to_create:
        write_file = True
        if file_path.exists() and not args.force:
            try:
                override = input(f"❓ File '{file_path.name}' already exists in '{file_path.parent}'. Override? (y/N): ")
                if override.lower() != 'y':
                    write_file = False
                    print(f"⏭️  Skipped '{file_path.name}'.")
            except Exception as e:
                print(f"❌ Error during override prompt for {file_type_label} file: {e}")
                write_file = False

        if write_file:
            try:
                with open(file_path, 'w', encoding=DEFAULT_ENCODING) as f:
                    f.write(template_content)
                action = "Overwritten" if file_path.exists() and write_file and not args.force else "Created"
                if file_path.exists() and args.force and write_file : action = "Forced overwrite of" # more specific for force
                print(f"✅ {action} {file_type_label} file: '{file_path}'")
            except Exception as e:
                print(f"❌ Error creating {file_type_label} file '{file_path}': {e}")
    print("🎉 Initialization complete. You can now customize the created files and run 'codegather run'.")


def handle_run_command(args):
    try:
        root_path = Path(args.root_dir).resolve(strict=True)
    except FileNotFoundError:
        print(f"❌ Error: Root directory '{args.root_dir}' not found.")
        return
    if not root_path.is_dir():
        print(f"❌ Error: Root path '{root_path}' is not a directory.")
        return

    if args.config:
        config_file_path = Path(args.config).resolve()
        if not config_file_path.is_file():
            print(f"⚠️ Warning: Custom config file '{config_file_path}' specified but not found. Using script defaults for includes/excludes.")
    else:
        config_file_path = root_path / DEFAULT_CONFIG_FILENAME
        if not config_file_path.is_file() and args.verbose:
            print(f"ℹ️ Default config file '{config_file_path.name}' not found in '{root_path}'. Using script defaults for includes/excludes.")

    loaded_cfg_settings, final_include_extensions, final_exclude_patterns = parse_config(config_file_path, args.verbose)

    output_source_log = "script_default"
    final_output_path_str = DEFAULT_OUTPUT_FILENAME
    if loaded_cfg_settings.get("output_file"):
        final_output_path_str = loaded_cfg_settings["output_file"]
        output_source_log = "config_file"
    if args.output:
        final_output_path_str = args.output
        output_source_log = "cli"

    temp_output_path = Path(final_output_path_str)
    if output_source_log == "config_file" and not temp_output_path.is_absolute():
        final_output_path = (root_path / temp_output_path).resolve()
    else:
        final_output_path = temp_output_path.resolve()

    final_no_header = DEFAULT_NO_HEADER_STATE
    if loaded_cfg_settings.get("no_header") is not None:
        final_no_header = loaded_cfg_settings["no_header"]
    if args.no_header is not None:
        final_no_header = args.no_header

    session_prompt_file_path_str_from_config = loaded_cfg_settings.get("session_prompt_file")
    final_session_prompt_path = None
    session_prompt_source_log = "none"

    if args.session_prompt_file_cli:
        final_session_prompt_path_str = args.session_prompt_file_cli
        session_prompt_source_log = "cli"
        final_session_prompt_path = Path(final_session_prompt_path_str).resolve()
    elif session_prompt_file_path_str_from_config:
        final_session_prompt_path_str = session_prompt_file_path_str_from_config
        session_prompt_source_log = "config_file"
        temp_prompt_path = Path(final_session_prompt_path_str)
        if not temp_prompt_path.is_absolute():
            final_session_prompt_path = (root_path / temp_prompt_path).resolve()
        else:
            final_session_prompt_path = temp_prompt_path
            
    use_session_prompt = not args.no_session_prompt and final_session_prompt_path is not None
    
    print(f"\nCodeGather: Running")
    print(f"---------------------------------")
    print(f"🌳 Project Root: {root_path}")
    
    if config_file_path.is_file():
        print(f"⚙️ Config File: {config_file_path}")
    elif args.config :
        print(f"⚙️ Config File: {config_file_path} (Specified but not found, using script defaults)")
    else:
        print(f"⚙️ Config File: Not found (Using script defaults for patterns)")
        
    if args.no_session_prompt:
        print(f"🎙️ Session Prompt: Disabled (via --no-session-prompt)")
    elif use_session_prompt and final_session_prompt_path:
        if final_session_prompt_path.is_file():
            print(f"🎙️ Session Prompt: {final_session_prompt_path}")
        else:
            print(f"🎙️ Session Prompt: {final_session_prompt_path} (File not found!)")
    else:
        print(f"🎙️ Session Prompt: Not configured or file not specified")
        
    print(f"📄 Output File: {final_output_path}")
    print(f"📝 File Headers: {'Disabled' if final_no_header else 'Enabled'}")
    print(f"---------------------------------")

    if args.verbose:
        print(f"Additional Details (Verbose Mode):")
        print(f"  Output Source: {output_source_log}")
        if final_session_prompt_path: # Only print source if a path was determined
            print(f"  Session Prompt Source: {session_prompt_source_log}")
        print(f"  Effective Include Patterns: {final_include_extensions}")
        print(f"  Effective Exclude Patterns: {final_exclude_patterns}")
        print(f"---------------------------------")

    session_prompt_content = ""
    if use_session_prompt and final_session_prompt_path:
        if final_session_prompt_path.is_file():
            try:
                with open(final_session_prompt_path, 'r', encoding=DEFAULT_ENCODING) as pf:
                    session_prompt_content = pf.read()
                session_prompt_content = session_prompt_content.replace("[root directory name]", root_path.name)
                if args.verbose: print(f"ℹ️ Session prompt loaded from '{final_session_prompt_path}'.")
            except Exception as e:
                print(f"⚠️ Warning: Could not read session prompt file '{final_session_prompt_path}': {e}")
        else:
            print(f"⚠️ Warning: Session prompt file '{final_session_prompt_path}' was specified but not found. No session prompt will be prepended.")

    try:
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Error: Could not create directory for output file '{final_output_path}': {e}")
        return

    print(f"🔎 Scanning for files to include...")
    files_to_process = []
    for item_abs_path in root_path.rglob("*"):
        if final_session_prompt_path and item_abs_path == final_session_prompt_path:
            if args.verbose: print(f"DEBUG: Excluding session prompt file itself: {final_session_prompt_path.relative_to(root_path) if final_session_prompt_path.is_relative_to(root_path) else final_session_prompt_path}")
            continue
        if is_excluded(item_abs_path, root_path, final_exclude_patterns, final_output_path, args.verbose):
            continue
        if item_abs_path.is_file():
            matched_extension = False
            for ext_pattern in final_include_extensions:
                if fnmatch.fnmatchcase(item_abs_path.name, ext_pattern):
                    matched_extension = True
                    break
            if matched_extension:
                files_to_process.append(item_abs_path)
                if args.verbose: print(f"  ➕ Will include: {item_abs_path.relative_to(root_path)}")

    if not files_to_process:
        print("🤷 No files found matching the criteria.")
    else:
        print(f"Found {len(files_to_process)} file(s) to combine.")
        if len(files_to_process) > FILES_COUNT_WARNING_THRESHOLD:
            print(f"⚠️ Warning: Processing {len(files_to_process)} files, which is a large number.")
            print(f"   Please ensure large directories (like 'node_modules/', 'build/', '.git/') are correctly excluded in '{config_file_path.name if config_file_path.is_file() else DEFAULT_CONFIG_FILENAME}'.")
            try:
                confirm_large_run = input("   Continue with this many files? (y/N): ")
                if confirm_large_run.lower() != 'y':
                    print("🛑 Aborted by user.")
                    return
            except Exception:
                print("🛑 Aborted due to input error.")
                return

    if args.verbose and files_to_process:
        print(f"\n✍️ Starting to write {len(files_to_process)} files to {final_output_path}...")

    try:
        with open(final_output_path, 'w', encoding=DEFAULT_ENCODING) as outfile:
            if session_prompt_content:
                outfile.write(session_prompt_content)
                outfile.write(SESSION_PROMPT_CODE_SEPARATOR)
            
            if not files_to_process:
                if not session_prompt_content and not final_no_header:
                     outfile.write(f"# No code files found matching criteria in '{root_path}'\n")
                     outfile.write(f"# Include Extensions: {final_include_extensions}\n")
                     outfile.write(f"# Exclude Patterns: {final_exclude_patterns}\n")
                elif session_prompt_content and not final_no_header:
                     outfile.write(f"\n# No code files found matching criteria in '{root_path}' (after session prompt)\n")
                print(f"Output file '{final_output_path}' created (contains session prompt and/or info header).")
                return

            for i, file_path_abs in enumerate(files_to_process):
                relative_file_path = file_path_abs.relative_to(root_path)
                if args.verbose: print(f"  Appending content of: {relative_file_path}")
                if not final_no_header:
                    outfile.write(f"--- START FILE: {relative_file_path} ---\n")
                try:
                    with open(file_path_abs, 'r', encoding=DEFAULT_ENCODING, errors='replace') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    error_message = f"[Error reading file {relative_file_path}: {e}]"
                    if args.verbose: print(f"    ⚠️ {error_message}")
                    outfile.write(f"{error_message}\n" if not final_no_header else f"\n\n'''{error_message}'''\n\n")
                
                if not final_no_header:
                    outfile.write(f"\n--- END FILE: {relative_file_path} ---")
                
                if i < len(files_to_process) - 1:
                    outfile.write("\n\n")
                elif not final_no_header :
                    outfile.write("\n")

            num_files = len(files_to_process)
            prompt_msg = "session prompt and " if session_prompt_content else ""
            print(f"\n✅ Successfully combined {prompt_msg}{num_files} file{'s' if num_files != 1 else ''} into '{final_output_path}'.")

    except IOError as e:
        print(f"❌ Error: Could not write to output file '{final_output_path}': {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred during file writing: {e}")


# --- Main Entry Point ---
def main():
    parser = argparse.ArgumentParser(
        description="CodeGather: Concatenates code files for easy AI prompting. Use 'init' or 'run' subcommands.",
        formatter_class=argparse.RawTextHelpFormatter # Shows newlines in help messages
    )
    # parser.add_argument('--version', action='version', version='%(prog)s 1.1') # Example version

    subparsers = parser.add_subparsers(dest="command", title="Available commands", metavar="<command>")
    subparsers.required = True

    # --- Init Subparser ---
    parser_init = subparsers.add_parser(
        "init",
        help="Initialize a project with default config and session prompt files.",
        description="Creates a '.codegatherignore' and a '.codegather_session_prompt.txt' file in the specified directory. These files provide templates for configuring file inclusion/exclusion and the AI session prompt."
    )
    parser_init.add_argument(
        "root_dir", nargs='?', type=str, default='.',
        help="The directory to initialize (default: current directory)."
    )
    parser_init.add_argument(
        "--force", action="store_true",
        help="Override existing config files without asking."
    )
    parser_init.set_defaults(func=handle_init_command)

    # --- Run Subparser ---
    parser_run = subparsers.add_parser(
        "run",
        help="Gather and combine code files based on configuration.",
        description="Scans the project directory, filters files based on '.codegatherignore' rules (or defaults), and concatenates their content into a single output file. An optional session prompt can be prepended."
        )
    parser_run.add_argument(
        "root_dir", nargs='?', type=str, default='.',
        help="The root directory of your project to scan (default: current directory)."
    )
    parser_run.add_argument(
        "-o", "--output", type=str,
        help=f"Name/path for the output file. Overrides config. Default: {DEFAULT_OUTPUT_FILENAME}"
    )
    parser_run.add_argument(
        "-c", "--config", type=str,
        help=f"Path to a custom config file. Default: <root_dir>/{DEFAULT_CONFIG_FILENAME}"
    )
    parser_run.add_argument(
        "--no-header", action="store_true", default=None,
        help="Disable '--- START FILE: ... ---' headers. Overrides config."
    )
    parser_run.add_argument(
        "--session-prompt", type=str, dest="session_prompt_file_cli",
        help="Path to a session prompt file to prepend. Overrides config."
    )
    parser_run.add_argument(
        "--no-session-prompt", action="store_true",
        help="Disable prepending of session prompt, even if specified in config."
    )
    parser_run.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging for detailed processing information."
    )
    parser_run.set_defaults(func=handle_run_command)

    try:
        args = parser.parse_args()
        args.func(args) # Call the function associated with the chosen subparser
    except Exception as e: # pragma: no cover
        print(f"❌ An unexpected error occurred: {e}")
        # Optionally, print more detailed traceback for debugging if needed
        # import traceback
        # traceback.print_exc()


if __name__ == "__main__":
    main()
