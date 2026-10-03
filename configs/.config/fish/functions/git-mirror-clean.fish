function git-mirror-clean --description 'Switch to main, prune remotes, and delete all other local branches'
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
    or begin
        echo 'Not inside a Git repository.'
        return 1
    end

    git switch main >/dev/null 2>&1
    or git checkout main
    or return 1

    echo 'Pruning remote branches...'
    git fetch --prune
    or return 1

    set -l branches (git for-each-ref --format='%(refname:short)' refs/heads | string match -v main)
    if test (count $branches) -gt 0
        echo 'Deleting local branches: '(string join ', ' $branches)
        for branch in $branches
            git branch -D -- $branch
            or return 1
        end
    else
        echo 'No extra local branches to delete.'
    end

    echo 'Resetting main to origin/main...'
    git reset --hard origin/main
    or return 1

    git remote set-head origin -a
    or return 1

    echo '✨ Repository is now a perfect mirror of origin/main'
end
