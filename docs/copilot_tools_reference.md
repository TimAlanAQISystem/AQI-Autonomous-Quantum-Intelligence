# VS Code Copilot Tooling Reference

## Chat Variables and Tools

| Chat Variable / Tool | Description |
| --- | --- |
| #changes | List of source control changes. |
| #codebase | Perform a code search in the current workspace to automatically find relevant context for the chat prompt. |
| #createAndRunTask | Create and run a new task in the workspace. |
| #createDirectory | Create a new directory in the workspace. |
| #createFile | Create a new file in the workspace. |
| #edit (tool set) | Enable modifications in the workspace. |
| #editFiles | Apply edits to files in the workspace. |
| #editNotebook | Make edits to a notebook. |
| #extensions | Search for and ask about VS Code extensions. |
| #fetch | Fetch the content from a given web page. |
| #fileSearch | Search for files in the workspace by using glob patterns and return their path. |
| #getNotebookSummary | Get the list of notebook cells and their details. |
| #getProjectSetupInfo | Provide instructions and configuration for scaffolding different types of projects. |
| #getTaskOutput | Get the output from running a task in the workspace. |
| #getTerminalOutput | Get the output from running a terminal command in the workspace. |
| #githubRepo | Perform a code search in a GitHub repo. |
| #installExtension | Install a VS Code extension. |
| #listDirectory | List files in a directory in the workspace. |
| #new | Scaffold a new VS Code workspace, preconfigured with debug and run configurations. |
| #newJupyterNotebook | Scaffold a new Jupyter notebook given a description. |
| #newWorkspace | Create a new workspace. |
| #openSimpleBrowser | Open the built-in Simple Browser and preview a locally-deployed web app. |
| #problems | Add workspace issues and problems from the Problems panel as context. |
| #readFile | Read the content of a file in the workspace. |
| #readNotebookCellOutput | Read the output from a notebook cell execution. |
| #runCell | Run a notebook cell. |
| #runCommands (tool set) | Enable running commands in the terminal and reading the output. |
| #runInTerminal | Run a shell command in the integrated terminal. |
| #runNotebooks (tool set) | Enable running notebook cells. |
| #runTask | Run an existing task in the workspace. |
| #runTasks (tool set) | Enable running tasks in the workspace and reading the output. |
| #runSubagent (Insiders) | Run a task in an isolated subagent context. |
| #runTests | Run unit tests in the workspace. |
| #runVscodeCommand | Run a VS Code command. |
| #search (tool set) | Enable searching for files in the current workspace. |
| #searchResults | Get the search results from the Search view. |
| #selection | Get the current editor selection. |
| #terminalLastCommand | Get the last run terminal command and its output. |
| #terminalSelection | Get the current terminal selection. |
| #testFailure | Get unit test failure information. |
| #textSearch | Find text in files. |
| #todos | Track implementation and progress of a chat request with a todo list. |
| #usages | Combination of "Find All References", "Find Implementation", and "Go to Definition". |
| #VSCodeAPI | Ask about VS Code functionality and extension development. |

## Slash Commands

| Command | Description |
| --- | --- |
| /doc | Generate code documentation comments from editor inline chat. |
| /explain | Explain a code block, file, or programming concept. |
| /fix | Ask to fix a code block or resolve compiler or linting errors. |
| /tests | Generate tests for selected methods and functions. |
| /setupTests | Help set up a testing framework. |
| /clear | Start a new chat session. |
| /new | Scaffold a new VS Code workspace or file. |
| /newNotebook | Scaffold a new Jupyter notebook. |
| /search | Generate a search query for the Search view. |
| /startDebugging | Generate a `launch.json` and start debugging. |
| /<prompt name> | Run a reusable prompt in chat. |

## Chat Participants

| Participant | Description |
| --- | --- |
| @github | Ask about GitHub issues, PRs, and repo activity. |
| @terminal | Ask about terminal usage or shell commands. |
| @vscode | Ask about VS Code features, settings, and APIs. |
| @workspace | Ask about the current workspace. |

## Agent Mode Highlights

- Switch to agent mode with **Ctrl+Shift+I**.
- Configure available tools, MCP servers, and auto-approve settings in the agent-mode toolbar.
- Useful for autonomous task execution with iterative edits and tool invocations.

## Planning Support

- Use the Plan agent to draft implementation plans before coding complex tasks.
- Enable the **todos** tool to track progress on multi-step work.

## Customization Tips

- Custom instructions: set coding or review guidelines.
- Reusable prompt files: store common prompts for repeated use.
- Chat modes: define tool access and instructions per mode.
- Share instructions or prompt files with the team for consistent workflows.

## Editor AI Features

- Code completions and inline hints adapt to existing code style.
- Inline Chat (**Ctrl+I**) helps generate code, tests, or explanations in place.
- Context menu offers AI actions such as explain, test, or review.
- Rename suggestions powered by AI via **F2**.

## Source Control and Issues

- Use `#changes` for context on current diffs.
- Generate commit messages, PR descriptions, or analyze history directly in chat.
- Experimental merge-conflict assistance available.

## Code Review Support

- Review a selection via context-menu > Generate Code > Review.
- Comprehensive uncommitted change review available from Source Control view.

## Search and Settings

- Semantic search in Settings and project search (Preview feature).
- Use chat to craft precise search queries.

## Testing and Debugging

- `/tests` to auto-generate tests for selected code.
- `/setupTests` for framework recommendations and setup guidance.
- `/fixTestFailure` for troubleshooting failing tests.
- `/startDebugging` to scaffold and run a launch configuration (experimental).

## Scaffolding Projects

- Agent mode or `/new` to scaffold entire projects or files.
- `/newNotebook` to create Jupyter notebooks based on natural language prompts.

## Terminal Assistance

- @terminal participant or **Ctrl+I** within the terminal for inline help.
- `copilot-debug` command to start instrumented debug sessions.

## Python and Notebook Support

- Inline Chat available in notebooks and the native Python REPL.
- Attach kernel variables with `#` in notebook chat prompts for context-aware help.
- Use `/newNotebook` for instant notebook scaffolding.

## Next-Step Shortcuts

| Action | Shortcut |
| --- | --- |
| Generate inline chat in notebooks | Ctrl+I |
| Attach notebook variables in prompts | Prefix with `#` |
| Inline Chat in native Python REPL | Native REPL + Ctrl+I |
| Open Chat view for notebook edits | Ctrl+Alt+I |
| Scaffold new notebook | /newNotebook |
