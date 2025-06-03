# CodeGather

CodeGather is a Python utility designed to concatenate code files from a project into a single text file. This is particularly useful for preparing a project's codebase to be used as context for Large Language Models (LLMs) like Gemini. Gemini can handle large context files, but allows for upload of limited number of files. Uploading code files each session can be cumbersome and lead to incomplete context for coding workflows. This tool bundles all your code files and puts a default "session" prompt on top which allows you to start new conversations/requests with LLM easier and faster. Codegather allows for flexible configuration of included/excluded files for bundling and customization of "session prompt".

## Usefull if
* For any reasosns you don't want to work with LLMs integrated with code editor
* You want to separate you new conversations per features/bugs/requests/sessions
* You experience increased LLM hallucinations and looping errors overtime in single conversation with LLM (it gets tired/used up and you need to start a new one, but a new one doesn't have your code context)

## Features

* **Project Initialization:** Quickly set up default configuration files (`.codegatherignore` and a session prompt template).
* **Selective File Gathering:** Include or exclude files and directories using glob patterns.
* **Custom Session Prompts:** Prepend a configurable text block to the combined code, ideal for providing context and instructions to an AI.
* **Placeholder Support:** The session prompt template supports placeholders like `[root directory name]`.
* **Flexible Configuration:** Uses a `.codegatherignore` file for settings, which can be overridden by command-line arguments.
* **Cross-Platform:** Works on macOS, Linux, and Windows.
* **User-Friendly CLI:** Simple `init` and `run` subcommands.
* **Safety Net:** Warns if an unusually large number of files are about to be processed.

## Requirements

* Python 3.7 or higher.

## Installation & Setup

1.  **Download the Script:**
    Save the script as `codegather.py` (or any name you prefer) in a directory on your system.

2.  **Make it Executable (macOS / Linux):**
    Open your terminal and navigate to the directory where you saved the script. Then run:
    ```bash
    chmod +x codegather.py
    ```

### Making it Easily Accessible (Optional but Recommended)

To run `codegather` from any directory without typing the full path to `codegather.py`, you can:

* **Option A: Add the script's directory to your PATH:**
    1.  Move `codegather.py` to a directory that's already in your PATH (e.g., `~/.local/bin` or `/usr/local/bin`), or add its current directory to your PATH environment variable.
    2.  For example, if you move it to `~/.local/bin`:
        ```bash
        mkdir -p ~/.local/bin
        mv codegather.py ~/.local/bin/codegather
        ```
    3.  Ensure `~/.local/bin` is in your PATH. You might need to add `export PATH="$HOME/.local/bin:$PATH"` to your shell configuration file (e.g., `~/.bashrc`, `~/.zshrc`, `~/.profile`, or `~/.config/fish/config.fish`) and then source it or open a new terminal.

* **Option B: Create an Alias (macOS / Linux):**
    Add an alias to your shell's configuration file (e.g., `~/.bashrc` or `~/.zshrc`):
    ```bash
    alias codegather='/path/to/your/codegather.py'
    ```
    Replace `/path/to/your/codegather.py` with the actual path. Then, source your config file (e.g., `source ~/.zshrc`) or open a new terminal.

* **Option C: For Windows:**
    1.  You can run the script directly using `python codegather.py ...`.
    2.  To make it easier, ensure Python's `Scripts` directory is in your PATH (this is usually done during Python installation). You can then place `codegather.py` in a directory that's in your PATH.
    3.  Alternatively, you can create a `.bat` file (e.g., `codegather.bat`) in a directory that's in your PATH, with the following content:
        ```batch
        @echo off
        python "C:\path\to\your\codegather.py" %*
        ```
        Replace `C:\path\to\your\codegather.py` with the actual path to your script.

After setup, you should be able to run the tool using `codegather` (or `python codegather.py` if not in PATH/aliased).

## Usage

CodeGather uses two main subcommands: `init` and `run`.

### `codegather init [root_dir]`

This command initializes a new or existing project for use with CodeGather.

* `root_dir` (optional): The project directory to initialize. Defaults to the current directory.

It performs the following actions:
1.  Creates a `.codegatherignore` file with default settings and patterns. This file controls which files are included/excluded and other configurations.
2.  Creates a `.codegather_session_prompt.txt` file with a template for your AI session prompt.
3.  If these files already exist, it will ask for confirmation before overwriting them.

**Options:**
* `--force`: Overwrites existing `.codegatherignore` and session prompt files without asking for confirmation.

**Example:**
```bash
codegather init
# or for a specific project directory
codegather init ./my-project
```

### `codegather run [root_dir]`

This command scans the specified project directory (or current directory by default), gathers code files based on the configuration, and combines them into a single output file.

* `root_dir` (optional): The root directory of the project to scan. Defaults to the current directory.

**Common Options:**

* `-o, --output <filepath>`: Specifies the name and path for the combined output file. Overrides the `output_file` setting in `.codegatherignore`. Default: `combined_code.txt`.
* `-c, --config <filepath>`: Specifies a custom path to a configuration file (instead of `.codegatherignore` in the root directory).
* `--session-prompt <filepath>`: Specifies a path to a session prompt file to be prepended to the output. This overrides the `session_prompt_file` setting in `.codegatherignore`.
* `--no-session-prompt`: Disables prepending the session prompt, even if one is configured.
* `--no-header`: Disables the `--- START FILE: ... ---` and `--- END FILE: ... ---` headers between concatenated files.
* `-v, --verbose`: Enables verbose logging, showing detailed processing steps and debug information.

**Example:**
```bash
# Run in the current directory using .codegatherignore
codegather run

# Run for a specific project, output to a custom file
codegather run ./my-app -o ./my-app-context.txt

# Run with verbose output
codegather run -v
```

## Configuration

Configuration is primarily handled through the `.codegatherignore` file located in your project's root directory (created by `codegather init`).

### The `.codegatherignore` File

This file uses a simple text-based format. Lines starting with `#` are comments and are ignored.

#### 1. General Settings (Key-Value Pairs)

These settings control the overall behavior:

* `output_file: <filename>`: Specifies the default name for the output file (e.g., `combined_project_code.txt`). If relative, it's path is relative to the project's root directory.
* `session_prompt_file: <filepath>`: Path to the file containing the session prompt text. If relative, it's path is relative to the project's root directory. The `init` command sets this to `.codegather_session_prompt.txt` by default.
* `no_header: [true|false]`: Set to `true` to disable file headers in the output. `false` (or if the line is commented out) enables headers.
* `default_extensions: <pattern1>, <pattern2>`: A comma-separated list of glob patterns (e.g., `*.ts, *.py`). These are used if no specific `*.ext` patterns are listed under "File Types to Include".

**Important:** For key-value pairs, inline comments (e.g., `session_prompt_file: prompt.txt # This is my prompt`) are supported; the part after `#` will be ignored.

#### 2. File Types to Include

List glob patterns for file extensions you want to include, one per line. If any patterns are listed here, they take precedence over the `default_extensions` setting.
Example:
```
*.js
*.jsx
*.html
```
The `init` command pre-populates this with `*.js` and `*.jsx`.

#### 3. Files and Directories to Exclude

List glob patterns for files or directories to exclude, one per line. Directory patterns should typically end with a `/` (e.g., `node_modules/`). These patterns are matched against paths relative to the project root.
Example:
```
node_modules/
.git/
dist/
build/
venv/
__pycache__/
*.log
*.tmp
combined_code.txt # Exclude the output file itself
.codegather_session_prompt.txt # Exclude the session prompt file
.DS_Store
```

### The Session Prompt File

This file (e.g., `.codegather_session_prompt.txt` by default, as configured by `session_prompt_file` in `.codegatherignore`) contains the text that will be prepended to the combined code output.

It supports a placeholder:
* `[root directory name]`: This will be replaced with the actual name of the root directory being processed.

You can customize this file to give specific instructions or context to an AI model. The `init` command creates a helpful template to get you started.

## Example Workflow

1.  **Navigate to your project directory:**
    ```bash
    cd /path/to/your/project
    ```

2.  **Initialize CodeGather:**
    ```bash
    codegather init
    ```
    This creates `.codegatherignore` and `.codegather_session_prompt.txt`.

3.  **Customize Configuration (Optional):**
    * Edit `.codegatherignore` to adjust included/excluded files, or change `output_file` and other settings.
    * Edit `.codegather_session_prompt.txt` to tailor the AI instructions.

4.  **Run CodeGather:**
    ```bash
    codegather run
    ```
    This will generate the `combined_code.txt` file (or whatever you configured) in your project directory.

5.  **Use the Output:**
    Upload the file into your LLM chat interface and specify your request.


## License

This project is open-source and available under the [MIT License](LICENSE.txt). (Consider adding an MIT License file to your repository).
