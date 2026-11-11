---
name: gitea-tea
description: Work with Gitea repositories, issues, comments, and pull requests using the configured tea CLI, including saved-login troubleshooting in Windows Codex sessions. Use for Gitea links and tea commands; GitHub work uses its own tools.
---

# Gitea with tea

Use the installed `tea` CLI and its saved authentication for Gitea work. Read
the relevant repository instructions and preserve the user's task scope and
existing authorization for publication, comments, merges, and other changes.
Loading this skill does not grant permission to post or change remote state.

## Machine configuration

Verified on this Windows machine on 2026-11-11:

- `tea` is on PATH, installed at
  `C:/Users/shaun/AppData/Local/Programs/tea/tea.exe` (version 0.16.0).
- Saved login `lan` targets `https://git.shaun-husain.com` as user `shaun`.
- Shared saved config: `C:/Users/shaun/.config/tea/config.yml`.
- Stable PowerShell entry point:
  `C:/Users/shaun/AppData/Local/Programs/tea/gitea.ps1`, also on PATH as `gitea`.
- City Sim VR repository: `CitySimVR/citysim`.
- This skill's source repository: `shaun/ai-agent-skills`.

**On this machine, use `gitea` for every tea operation.** It is the existing
wrapper around `tea.exe`, setting `XDG_CONFIG_HOME` to
`C:/Users/shaun/.config` for that call and restoring it afterwards. All
command examples below use this wrapper. If PATH resolves `gitea` elsewhere,
invoke the full `.ps1` path with PowerShell's `&` operator. On another machine,
use its installed tea executable and locally configured profile.

The maintained wrapper source is [scripts/gitea.ps1](scripts/gitea.ps1); keep the
installed copy aligned when changing it. The shared profile is private machine
configuration, outside this repository. Its original AppData copy was preserved
on 2026-11-11; the `.config/tea` profile is authoritative for wrapper operations.

Prefer the configured login over ad hoc HTTP clients, token discovery, or browser
automation. Do not print the tea credential file, tokens, or authentication
headers. `gitea logins list --output json` lists login metadata without the token.

### Empty login list or missing `lan`

An empty list or `login name 'lan' does not exist` means the selected local
configuration has no such profile; it does not establish that the saved token
is invalid. First retry through the existing wrapper in the same tool execution:

```powershell
& 'C:/Users/shaun/AppData/Local/Programs/tea/gitea.ps1' logins list --output json
& 'C:/Users/shaun/AppData/Local/Programs/tea/gitea.ps1' issues 343 --comments --repo CitySimVR/citysim --login lan --output json
```

Codex shells can have a different configuration root. A manually assigned
`XDG_CONFIG_HOME` in one shell need not persist into the next tool call; the
wrapper pins it on every invocation. Microsoft Store PowerShell 7.7 was verified
to hide the original AppData profile despite Full Access in Codex. A wrapper
pointing into AppData still returned `[]`. The shared `.config/tea` directory
avoids that redirection; changing PowerShell versions is unnecessary.

If the wrapper also returns `[]`, stop assuming a configuration-root fix is
sufficient. Run [scripts/Test-TeaLogin.ps1](scripts/Test-TeaLogin.ps1) **in the
failing session**. It reports identity, executable ancestry, environment paths,
config readability/length, and login names without reading config contents or
making a remote request. A successful host-shell check does not establish
access from another session.

Microsoft Store PowerShell and Python can redirect LocalAppData access for child
processes; Windows sandbox permissions can also affect profile visibility. Use the probe
to distinguish these cases before recommending a remedy. For sandbox access
failures, inspect the affected CLI's `/status` and `/debug-config` and follow
its permitted access/approval workflow. Do not disable the sandbox, loosen ACLs,
or copy credentials into a workspace to make the test pass. Report the specific
remaining failure without replacing credentials or extracting browser secrets.

Confirm the target from the user's link, repository instructions, or Git remote;
do not apply CitySim's repository slug to unrelated work. Pass `--login` and
`--repo` explicitly, especially in worktrees or repositories with multiple
remotes. Use the long `--repo` spelling: some subcommands reuse short flags.

```powershell
Get-Command gitea,tea
gitea --version
gitea logins list --output json
git remote -v
$giteaLogin = 'lan'
$giteaRepo = 'CitySimVR/citysim' # Change to the task's actual owner/repository.
```

## Inspect before acting

Read the exact command's `--help` before using it. Flags differ by tea version
and subcommand; do not substitute `gh` flags such as `--body-file`.

```powershell
gitea issues --help
gitea issues --repo $giteaRepo --login $giteaLogin --state open --page 1 --limit 30 --output json
gitea issues 343 --comments --repo $giteaRepo --login $giteaLogin --output json
gitea pulls --help
gitea pulls 446 --comments --repo $giteaRepo --login $giteaLogin --output json
```

Issue and PR numbers are repository-local indices, not API object IDs. Read the
body, discussion, linked dependencies, and relevant evidence before changing
status. `--output json` selects a format; it does not guarantee every field is
present or unabridged. Use `--fields` where the command supports field selection.

For discussions, prefer detail reads with `--comments`. The installed
`tea comments list --output json` abbreviates comment bodies, so do not use its
body previews as complete acceptance or handoff records. Use it to find comment
IDs, or use `tea api` for full API bodies. PR inline review comments are separate:
inspect `tea pulls review-comments --help` when reviewing a PR.

For long lists or threads, inspect pagination and collect all relevant pages.
Do not assume a requested page size was honored. During this machine's smoke
check, comment API requests with different page parameters returned identical
IDs. Detect repeated pages and stop; use the detail response or another verified
tea read path, and disclose any unresolved completeness limitation instead of
looping or claiming the entire thread was read.

## Descriptions and comments

These are examples for changes already within the user's authorized task.
Substitute actual indices, branches, titles, and file paths. Store temporary
bodies in a task-owned scratch directory, ignored when inside a repository.

Use UTF-8 files with real newlines for substantial Markdown. In PowerShell,
literal single-quoted here-strings preserve Markdown backticks and `$` characters.
Avoid constructing shell commands from issue text or treating
`JSON.stringify()` as shell escaping.

```powershell
gitea issues create --help
gitea issues create --repo $giteaRepo --login $giteaLogin --title 'Focused task title' --description-file $issueBodyPath
gitea issues edit --help
gitea issues edit --repo $giteaRepo --login $giteaLogin --description-file $issueBodyPath 343
```

`--description-file` is supported on installed issue/PR create and edit commands;
it replaces the description on edits. Preserve unrelated content. Comment-add
does not have that flag. A short authorized comment can use the native command:

```powershell
gitea comments add --help
gitea comments add --repo $giteaRepo --login $giteaLogin 343 'Reviewed the identified evidence; next action recorded.'
```

For a multiline comment file, use tea's authenticated API rather than manually
handling a token:

```powershell
gitea api --help
gitea api --login $giteaLogin --method POST "repos/$giteaRepo/issues/343/comments" --Field "body=@$commentBodyPath"
```

## Pull requests

Before publishing, inspect Git status, the complete proposed base-to-head diff,
and required LFS inputs. Push only the scoped branch when authorized by the task
or standing repository instructions. Preserve unrelated work and shared history.
Then create or update the matching PR rather than creating duplicates.

```powershell
gitea pulls create --help
gitea pulls create --repo $giteaRepo --login $giteaLogin --head 'codex/task-branch' --base main --draft --title 'Focused change' --description-file $prBodyPath
gitea pulls edit --help
gitea pulls edit --repo $giteaRepo --login $giteaLogin --description-file $prBodyPath 446
```

Installed `--draft` uses a `WIP: ` title prefix. `tea pulls edit --ready` removes
the draft prefix. Select draft/readiness according to the owning workflow;
creating a validation PR does not establish acceptance or authorize merging.
Consult the relevant command help and task's merge authorization before merging,
closing issues, deleting branches, or publishing releases.

## Authenticated API fallback

Use `tea api` when a native command lacks a needed operation or full response.
It reuses saved authentication; relative endpoints are prefixed with `/api/v1/`.
For example, this reads full discussion bodies:

```powershell
gitea api --login $giteaLogin --method GET "repos/$giteaRepo/issues/343/comments"
```

Quote endpoints containing query strings. Check returned page contents as above.
Specify `--method` explicitly: adding `--field`, `--Field`, or `--data` otherwise
defaults the method to POST. `--field` sends a string; `--Field` supports typed
values and `@file` input. For a complete JSON payload, use `--data "@$payloadPath"`;
do not combine it with field flags. API `--output` is a destination filename,
unlike native commands' `--output json` format selection.

Check exit status and the returned target/state after mutations. If a write
times out, read the target to determine whether it succeeded before retrying;
avoid duplicate comments, issues, or PRs. Report the actual issue/PR URL, changed
state, checks/evidence, and remaining action without presenting queued CI or
unobserved playtests as passed.
