# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- Create an issue: `gh issue create --title "..." --body "..."`
- Read an issue: `gh issue view <number> --comments`
- List issues: `gh issue list --state open --json number,title,body,labels,comments`
- Comment on an issue: `gh issue comment <number> --body "..."`
- Apply or remove labels: `gh issue edit <number> --add-label "..."` and `gh issue edit <number> --remove-label "..."`
- Close an issue: `gh issue close <number> --comment "..."`

## Sub-issues

GitHub CLI does not expose sub-issue linking through `gh issue create` or `gh issue edit` in this repo. Create the issue first, then link it to the parent issue with `gh api graphql`.

Example flow:

1. Create the child issue:
	`gh issue create --title "Child title" --body "..."`
2. Resolve the parent and child node ids:
	`gh issue view <parent-number> --json id --jq .id`
	`gh issue view <child-number> --json id --jq .id`
3. Link the child under the parent:

	```sh
	gh api graphql -f query='mutation($issueId: ID!, $subIssueId: ID!) {
	  addSubIssue(input: { issueId: $issueId, subIssueId: $subIssueId }) {
		 issue { number }
		 subIssue { number title }
	  }
	}' -f issueId='<parent-node-id>' -f subIssueId='<child-node-id>'
	```

Use `addSubIssue`, not `addSubIssues`.

Infer the repo from `git remote -v`. Running `gh` inside this clone should target `manuelseeger/sc2-ai-coach`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.