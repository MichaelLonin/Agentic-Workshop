---
name: run-team
description: Run the whole workshop team from one session - read every tasks/*/status.yaml, hand each turn to the matching role agent (product-ba, architect, developer, qa, scrum-master), ask the human only for Product Owner decisions and acceptance, and repeat until every task is closed or needs a facilitator. Use when the user says "run the team", "run TASK-001", or /run-team.
---

# Run the team

You are the **coordinator**, not a role. You never write requirements, designs, code, tests, QA results or routing decisions yourself, and you never edit `status.yaml` or `events.jsonl`. Every turn is done by a role agent, which follows `AGENTS.md`, `WORKFLOW.md` and its own `roles/*.md` file. Do not read `facilitator/`.

Optional argument: a wish card text (for an empty `TASK-001`), or `scrum-master` to switch the team to Stage 3 first.

## 1. Before the first turn

1. Check this is a Git repository with a remote you can push to: `git rev-parse --is-inside-work-tree` and `git remote -v`. If not, stop and tell the user: the role agents hand work over through `git pull` and `git push`, so the team's repository must be cloned here first.
2. Run `git pull --rebase`.
3. If `tasks/TASK-001/task.md` still has the placeholder `_(type the wish card here)_`, the task hasn't started. Ask the user for the wish card text, word for word, unless it was given as the argument. Then start the `product-ba` agent with: "Here is our wish card from Business: \"<text>\". Put it in tasks/TASK-001/task.md word for word, commit and push it. Then do your PRODUCT_BA turn."
4. If the argument was `scrum-master`, start the `scrum-master` agent with: "Switch the team to Scrum Master mode, then check for work."

## 2. The loop

Repeat, at most 15 turns in total:

1. `git pull --rebase`, then read every `tasks/*/status.yaml`.
2. Pick whose turn it is, using `WORKFLOW.md`, section 4:
   - `status` is `ACCEPTED` or `REJECTED`: closed, skip it.
   - `routing_mode: SCRUM_MASTER` and `updated_by` is not `SCRUM_MASTER`: the `scrum-master` agent's turn.
   - otherwise `assigned_to` names the role, if `updated_by` is a different role:

     | `assigned_to` | Agent |
     |---|---|
     | `PRODUCT_BA`, `PRODUCT_OWNER` | `product-ba` |
     | `ARCHITECT`, `SECURITY` | `architect` |
     | `DEVELOPER` | `developer` |
     | `QA` | `qa` |
     | `HUMAN_FACILITATOR`, `HUMAN_SUPPORT` | stop the loop: tell the user it needs a facilitator, with `issue` and `routing_reason` |
3. Start that agent with the prompt "Check for work." plus the task ID. Run one agent at a time: they all commit and push to the same branch.
4. **Product Owner turns need the human.** Before starting `product-ba` for a `PRODUCT_OWNER` turn, read `requirements.md` (and `qa.md` when it's an acceptance) and ask the user the open questions or "Accept, request changes, or reject?" with a two-line summary of the QA evidence. Pass their answers to the agent quoted word for word: "The Product Owner says: \"...\"". If a `product-ba` agent returns `QUESTIONS FOR THE PRODUCT OWNER`, ask the user those and start it again with the answers.
5. After the agent returns, check its turn really happened: `git log -1 --oneline` shows its commit, and `status.yaml` changed. If nothing changed, stop the loop and tell the user what the agent said.
6. Tell the user in one line what happened (role, result, who's next).

Stop when every task is closed, when a turn needs a facilitator, when the user stops answering a Product Owner question, or at 15 turns.

## 3. At the end

Run `python scripts/events.py` (or `py scripts/events.py` on Windows) and give the user its timeline, plus each task's final `status` and `result`, and anything still waiting on them.
