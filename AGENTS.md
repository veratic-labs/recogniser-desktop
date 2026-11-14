# Agent Instructions — recogniser

## 1. Scope and Project Boundaries

The project root is the directory containing this `AGENT.md` and `PLAN.md`. Resolve its absolute path before making changes.

- Read `PLAN.md` before implementation. It defines the product requirements, architecture, milestones, and acceptance criteria.
- Keep all file creation, modification, deletion, and renaming inside the project root and its descendants.
- Do not modify any files outside this boundary, including parent directories, sibling projects, user configuration, global Git configuration, shell configuration, or system files.
- Do not bypass this boundary through symbolic links, junctions, absolute paths, or tools with output locations outside the project.
- Keep virtual environments, temporary files, generated assets, test outputs, logs, and tool caches inside the project. Configure tools accordingly; do not run commands that would write outside the boundary.
- Do not install system-wide packages or change the host environment. If a required operation cannot be completed within the boundary, report the blocker and wait for instructions.
- Reading necessary external documentation or installed dependencies is allowed; writing outside the project is not.

## 2. Git Version Control

- Use Git to manage this project's versions.
- Inspect the existing repository and working tree before making changes. Preserve pre-existing user changes.
- If there is no repository, initialise one inside the project root. If the project is inside a repository rooted outside this boundary, report that situation before performing Git mutations; do not write to the parent repository's metadata.
- Maintain a project-local `.gitignore` for environments, caches, temporary outputs, and other generated files. Preserve intentional model resources.
- Inspect the diff and stage only files belonging to the approved milestone. Do not blindly stage unrelated changes.
- Do not discard user changes, rewrite existing history, amend commits, reset destructively, or delete branches without explicit instructions.
- Git author configuration, if needed, must be repository-local and use user-provided identity. Do not invent an identity or change global configuration.

## 3. Milestone Review and Commit Approval

Work one milestone at a time. Completing implementation or passing checks is not permission to commit.

After each milestone:

1. Complete the milestone's implementation and relevant verification.
2. Review the working-tree diff for scope and correctness.
3. Report the completed work to the user **before committing**.
4. Wait for the user to accept the milestone and explicitly approve the commit.
5. If changes are requested, make them, repeat the relevant checks, and submit an updated report. Continue waiting for acceptance and commit approval.
6. Only after approval, create a commit covering the accepted milestone and report its hash and subject.
7. Wait for the user's instruction before starting the next milestone, unless that instruction was already explicitly given.

Each milestone report must include:

- The milestone name and completed behaviour.
- Files created or changed and their purpose.
- Checks performed and their actual results, including any checks that could not run. Report code and functional checks only; never claim visual or screenshot verification.
- Known limitations, unresolved issues, and the manual verification steps the user should follow, including how to launch the app.
- A proposed commit subject.
- A clear statement that no commit or push has been made and that the work is awaiting acceptance and commit approval.

Do not create checkpoint commits, automatic commits, or intermediate commits to bypass this review. Approval applies only to the reviewed milestone and changes; it is not standing permission for future commits. A status question, silence, or a request to fix something is not commit approval.

If the repository is newly initialised, its first commit follows the same approval process.

## 4. No Autonomous Pushes

- Do not push to GitHub or any other remote on your own.
- Commit approval does not authorise a push.
- Do not run `git push`, enable automatic pushing, or use another tool or API to upload commits or source changes to a remote.
- Do not create remote branches, pull requests, releases, or deployments without a separate explicit user instruction.
- Report accepted local commits to the user; leave remote publication to the user unless they explicitly request it later.

## 5. Implementation Discipline

- Follow confirmed decisions in `PLAN.md`. Treat provisional proposals and open questions as unresolved rather than approved requirements.
- Keep changes focused on the current milestone. Avoid unsolicited refactoring, extra features, and unnecessary frameworks.
- Preserve existing model files, training code, and inference behaviour except for changes required by the agreed integration, such as correcting the model filename in its path.
- Keep the agreed separation between `frontend/`, `backend/`, and `models/`.
- Verify actual model interfaces and dependency behaviour rather than guessing.
- Never fabricate test outcomes or recognition results. Report failures and limitations accurately.
- If requirements conflict or a material product decision is missing, explain the issue and request clarification before making the dependent change.
- Keep `PLAN.md` as the product plan and this file as the agent workflow policy. Do not weaken these rules to bypass a blocker.

## 6. Verification and UI Review

You do not have image-viewing capabilities. Verification must therefore rely on code and functional checks, and visual acceptance belongs to the user.

- Do not capture screenshots, generate visual-review artifacts, or attempt screenshot-based UI inspection. This covers pywebview window captures, headless-browser screenshots, screen grabs, and any image file produced for the purpose of reviewing layout.
- Do not claim to have visually inspected the interface. Do not describe appearance, spacing, alignment, or visual polish as if they had been observed.
- Use appropriate code and functional checks instead, for example:
  - Python syntax and import checks for the backend modules.
  - Backend tests for preprocessing, adapters, and exposed API functions.
  - Frontend syntax checks and DOM state assertions, including interaction checks where the available tooling supports them.
  - Registry, model path, and configuration checks that require no rendering.
- Leave visual appearance, spacing, alignment, and overall UI acceptance to the user. Every milestone report must include concise launch instructions (for example activating `venv` and running `python -m backend.main`) plus short manual verification steps stating what to try and what to expect, so the user can assess the interface.
- After the user inspects the application, make the UI adjustments they ask for, re-run the relevant checks, and report again. Do not treat your own judgement of the rendered interface as acceptance.

These rules apply to all future milestones and to any other change that affects the interface.
