# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sleepless Agent is a 24/7 AI agent daemon that orchestrates autonomous task execution using the Claude Code CLI via Python Agent SDK. It provides a Slack interface for task submission and monitoring, with isolated workspace management, intelligent scheduling, and automated Git integration.

## Common Development Commands

### Installation & Setup
```bash
# Install in development mode
pip install -e .

# Or install from PyPI
pip install sleepless-agent

# Create .env from example
cp .env.example .env
# Edit .env with your Slack tokens (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
```

### Running the Agent
```bash
# Start the daemon
sle daemon

# Run with debug logging
SLEEPLESS_LOG_LEVEL=DEBUG sle daemon

# Start in test mode (dry run)
sle daemon --test

# Start without Slack integration
sle daemon --no-slack
```

### CLI Commands
```bash
# Submit a random thought (THOUGHT priority, auto-commits)
sle think "Explore async patterns in Python"

# Submit a serious task (SERIOUS priority, creates PR)
sle think "Add OAuth2 support" -p backend

# Check system status and queue
sle check

# Show Claude Code Pro plan usage
sle usage

# View task details, daily, or project reports
sle report              # Today's report
sle report 42           # Task #42 details
sle report --list       # List all reports

# Cancel task or move project to trash
sle cancel 42
sle cancel my-project

# Manage trash
sle trash list
sle trash restore my-project
sle trash empty
```

### Database & Workspace Operations
```bash
# View queue status (SQLite query)
sqlite3 workspace/data/tasks.db "SELECT id, description, status, priority FROM tasks LIMIT 10;"

# Reset database (WARNING: deletes all tasks)
make db-reset
# or
rm -f workspace/data/tasks.db workspace/data/*.db

# Follow logs
make logs
# or
tail -f workspace/data/agent.log

# Backup workspace
make backup
```

### Service Installation
```bash
# Linux (systemd)
make install-service
sudo systemctl start sleepless-agent

# macOS (launchd)
make install-launchd
launchctl list | grep sleepless
```

## Architecture

### Directory Structure
```
src/sleepless_agent/
├── core/           # Core engine (daemon, executor, models, queue, task_runtime)
├── interfaces/     # User interfaces (Slack bot, CLI)
├── chat/           # Interactive chat mode (executor, handler, session)
├── scheduling/     # Task scheduling and auto-generation
├── storage/        # Persistence (SQLite, Git, results, workspace)
├── monitoring/     # Logging, health checks, metrics, reports
├── tasks/          # Task utilities and refinement
└── utils/          # Configuration, display helpers, exceptions
workspace/
├── data/           # Database (tasks.db), results, reports, logs
├── tasks/          # Isolated task workspaces (task_1_*/, task_2_*/, ...)
├── projects/       # Shared project workspaces (for -p tasks)
├── shared/         # Shared resources accessible to all tasks
└── trash/          # Soft-deleted projects
```

### Key Components

**Daemon (`core/daemon.py`)**: Main event loop that continuously polls the task queue, dispatches tasks to executors, and manages system resources. Initializes all subsystems (Slack bot, scheduler, auto-generator, Git manager, etc.).

**Executor (`core/executor.py`)**: Wraps Claude Code CLI via Python Agent SDK. Implements multi-agent workflow with three phases:
- **Planner**: Analyzes task, creates TODO list, estimates effort
- **Worker**: Executes the plan with full tool access (Read, Write, Edit, Bash, TodoWrite)
- **Evaluator**: Reviews completion, extracts outstanding items and recommendations

**Scheduler (`scheduling/scheduler.py`)**: Intelligent task scheduling based on priority, Claude usage quotas, time of day (day/night thresholds), and system resources. Manages pause/resume when Pro plan limits are reached.

**Task Queue (`core/queue.py`)**: SQLite-backed persistent queue with atomic operations. Tracks tasks through states: PENDING → IN_PROGRESS → COMPLETED/FAILED.

**Workspace Isolation**: Each task executes in an isolated directory (`workspace/tasks/task_<id>_<slug>/` or `workspace/projects/<project_id>/`). Tasks can only access their own workspace and `workspace/shared/`. System directories (`workspace/data/`) are protected.

**Git Manager (`storage/git.py`)**: Automated version control. Random thoughts auto-commit to `thought-ideas` branch. Serious tasks create feature branches (`feature/<project>-<id>`) and PRs.

**Chat Mode (`chat/`)**: Real-time conversational sessions with Claude in Slack threads. Maintains conversation history, allows file read/write/edit in project workspace.

### Multi-Agent Workflow

Task execution follows a three-phase pattern configurable in `config.yaml`:

```yaml
multi_agent_workflow:
  planner:
    enabled: true
    max_turns: 10    # Planning complexity
  worker:
    enabled: true
    max_turns: 30    # Execution depth
  evaluator:
    enabled: true
    max_turns: 10    # Review thoroughness
```

Each agent can be independently enabled/disabled. The executor updates the workspace README.md with plan, status, outstanding items, and recommendations.

### Task Types & Priority

- **THOUGHT** (`/think` without `-p`): Random ideas, auto-commits to `thought-ideas` branch
- **SERIOUS** (`/think -p project`): Production tasks, creates feature branch and PR
- **GENERATED**: Auto-generated tasks during idle time

### Usage Management

The agent monitors Claude Code Pro plan usage and pauses task generation at configurable thresholds:
- **Nighttime** (1 AM - 9 AM): 80% threshold (works while you sleep)
- **Daytime** (9 AM - 1 AM): 20% threshold (preserves capacity)

Configure in `config.yaml` via `claude_code.threshold_day`, `claude_code.threshold_night`, `night_start_hour`, `night_end_hour`.

### Configuration

Primary config is `src/sleepless_agent/config.yaml`:
- `claude_code`: CLI path, model, thresholds, usage command
- `git`: Enable/disable, remote repo URL, auto-create
- `agent`: Workspace root, task timeout
- `multi_agent_workflow`: Phase enablement and turn limits
- `auto_generation`: Task auto-generation prompts and weights

Environment variables (`.env`):
- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`: Required for Slack integration
- `AGENT_WORKSPACE_ROOT`: Workspace location (default: `./workspace`)

### Important Implementation Details

**Workspace Access Control**: The executor uses `add_dirs` in `ClaudeAgentOptions` to restrict file access. Each task gets `cwd=workspace` and may access additional directories like `shared/` and project workspace. System paths are explicitly excluded.

**Live Status**: The daemon writes `workspace/data/live_status.json` with real-time executor state (current phase, prompt preview, answer preview). The CLI `check` command reads this for the "Live Status" panel.

**Chat Mode Sessions**: Managed by `ChatSessionManager`. Each user gets one active session. Messages must be sent inside the Slack thread, not the main channel. Sessions auto-timeout after 30 minutes of inactivity.

**Task Context**: Tasks carry a `context` JSON field storing metadata like `refines_task_id` for REFINE tasks that reuse existing workspaces.

**README Templates**: The executor generates/updates workspace README.md with sections for summary, plan, TODO list, status, outstanding items, recommendations, and execution history.

### Testing

No formal test suite currently exists. Use `make test` for basic import validation. Manual testing via Slack CLI commands is the primary verification method.

---

## Single Project Focus Configuration

This section documents the configuration for running Sleepless Agent in "single project mode" - continuously improving one specific git repository (e.g., `py38-cc-ds`) with automatic task generation.

### Configuration Setup

For single project focus, configure `config.yaml` with:

```yaml
git:
  enabled: true
  remote_repo_url: git@github.com:crowluya/py38-cc-ds.git

auto_generation:
  enabled: true
  prompts:
    - name: refine_focused
      weight: 0.9  # 90% - focus on refining existing project
    - name: balanced
      weight: 0.1  # 10% - balance between new and refine
    - name: new_friendly
      weight: 0.0  # 0% - disable new projects
```

### Critical Prompt Format Requirement

Auto-generated tasks MUST include `-p <project_id>` at the end of the description. The prompt should specify:

```
## CRITICAL Format Requirement
Your response MUST follow this EXACT format:
[REFINE] <description> -p py38-cc-ds
```

This ensures:
1. Tasks are routed to the correct project workspace (`workspace/projects/py38-cc-ds/`)
2. Git commits go to the correct repository
3. Tasks inherit project context and dependencies

### Code Fixes Applied

**1. Empty Queue Handling (`auto_generator.py:109-124`)**

When the task queue is empty, the system now returns "refine_focused" instead of "new_friendly" to prevent generation failures when new_friendly weight is 0:

```python
def _determine_generation_mode(self, task_count: int) -> str:
    if task_count >= 5:
        return "refine_focused"
    elif task_count >= 2:
        return "balanced"
    else:
        # When queue is empty, use refine_focused (new_friendly is disabled with weight=0)
        return "refine_focused"
```

**2. Project ID Parsing (`auto_generator.py:461-485`)**

Added method to extract `-p <project>` flag from AI-generated task descriptions:

```python
@staticmethod
def _parse_project_id(task_desc: str) -> tuple[str, Optional[str]]:
    """Parse project ID from task description (e.g., "-p py38-cc-ds")"""
    import re
    task_desc = task_desc.strip()

    # Search for -p project_id pattern (at end of description)
    project_match = re.search(r'\s+-p\s+(\S+)(?:\s|$)', task_desc)
    if project_match:
        project_id = project_match.group(1)
        clean_desc = task_desc[:project_match.start()].strip()
        return (clean_desc, project_id)

    return (task_desc, None)
```

**3. Project Assignment (`auto_generator.py:317-341`)**

Set project_id when flag is present:

```python
# Parse project ID from description (e.g., "-p py38-cc-ds")
clean_desc, project_id = self._parse_project_id(clean_desc)

# Set project_id if parsed from description
if project_id:
    task.project_id = project_id
```

### Project Workspace Setup

For the target project (`py38-cc-ds`):

1. Clone the repository to `workspace/projects/py38-cc-ds/`
2. Set up Python environment (e.g., Python 3.8.10 via pyenv)
3. Install project dependencies
4. Configure API credentials in `.env.local`
5. Add project-specific documentation (e.g., `plan_018_pycode_quality_improvement.md`)

### .gitignore Configuration

Prevent nested git repository issues:

```
# Sleepless Agent managed ignores
data/

# Ignore cloned projects (they have their own git repos)
projects/

# Ignore task directories that contain nested git repos
tasks/**/.git/

# Logs directory
.logs/
```

### Model Configuration

For GLM Coding (智谱方案) with Opus 4.5:

```yaml
claude_code:
  model: claude-opus-4-5-20250929
```

### Continuous Improvement Loop

Once configured, the system operates as follows:

1. **Check Usage**: Monitor Claude Code Pro plan usage against thresholds
2. **Generate Task**: When usage below threshold, auto-generate task using weighted prompts
3. **Route to Workspace**: Tasks with `-p py38-cc-ds` execute in `workspace/projects/py38-cc-ds/`
4. **Multi-Agent Execution**: Planner → Worker → Evaluator phases
5. **Git Integration**: Auto-commit changes to feature branch
6. **Repeat**: Loop continues 24/7

### Troubleshooting

**Symptom**: `autogen.no_prompts_available`
- **Cause**: Queue empty + new_friendly weight = 0 → empty weighted_list
- **Fix**: Modify `_determine_generation_mode()` to return "refine_focused" when queue empty

**Symptom**: Tasks executing in wrong workspace
- **Cause**: AI didn't include `-p <project>` flag, project_id is None
- **Fix**: Update prompt to require EXACT format with examples

**Symptom**: Git workflow fails with nested repo error
- **Cause**: `.git` directories in task workspaces or projects/
- **Fix**: Update `.gitignore` to exclude `projects/` and nested `.git` dirs
