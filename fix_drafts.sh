gh_token_env_path="${GH_TOKEN_ENV_PATH:-../email-security-pipeline/GH_TOKEN.env}"

# SECURITY: Fail closed if the token env file is missing or unreadable.
if [ ! -r "$gh_token_env_path" ]; then
  echo "Error: GH token env file is missing or unreadable: $gh_token_env_path" >&2
  exit 1
fi

source "$gh_token_env_path"

fix_and_merge() {
  local repo=$1
  local pr=$2
  echo "Marking $repo#$pr ready and merging..."
  gh pr ready $pr -R $repo
  gh pr merge $pr -R $repo --squash --delete-branch
}

fix_and_merge "abhimehro/email-security-pipeline" "632"
fix_and_merge "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project" "102"
fix_and_merge "abhimehro/personal-config" "743"

