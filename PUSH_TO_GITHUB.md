# Publish this repository to your GitHub account

The connected GitHub integration cannot create a new repository in this session. These steps finish that part without changing any other project.

## Method A: GitHub browser + Git

1. Open https://github.com/new and sign in.
2. Name the repository **`ukiyora-character-database`**. Choose **Private** initially so you can inspect imported research data; you can make it public later if rights are in order.
3. Do **not** initialize it with a README, license or `.gitignore` (all project files are already included).
4. Extract `ukiyora-character-database.zip` into a folder. Open a PowerShell terminal in that folder.
5. Run:

```powershell
git init -b main
git add .
git commit -m "Initial Ukiyora character catalogue and D1 search API"
git remote add origin https://github.com/hack975/ukiyora-character-database.git
git push -u origin main
```

Sign in when Git prompts for GitHub authentication. **Never put a GitHub personal access token into the website or chat.**

## Method B: GitHub CLI

If you have the GitHub CLI installed and logged in (`gh auth login`):

```powershell
git init -b main
git add .
git commit -m "Initial Ukiyora character catalogue and D1 search API"
gh repo create hack975/ukiyora-character-database --private --source . --remote origin --push
```

## Important

GitHub stores the version-controlled data. The live website should query the D1 Worker described in README rather than GitHub's API for every keystroke. Publishing this repository does not automatically deploy its Worker or update the existing Ukiyora site.
