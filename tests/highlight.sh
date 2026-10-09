#!/usr/bin/env bash
# Exercise install/upgrade decisions without downloading or changing user tools.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
mkdir -p "$test_dir/cargo/bin"

cat > "$test_dir/tool" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case ${0##*/} in
  cargo)
    if [[ $1 == --version ]]; then
      echo 'cargo 1.99.0'
    else
      printf '%s\n' "$*" >> "$HIGHLIGHT_TEST_STATE/cargo.log"
      printf '%s\n' "${!#}" > "$HIGHLIGHT_TEST_STATE/cli-version"
    fi
    ;;
  rustc) echo 'rustc 1.99.0' ;;
  rustup)
    case $1 in
      --version) echo 'rustup 1.28.2' ;;
      run) cat "$HIGHLIGHT_TEST_STATE/rust-version" ;;
      update)
        echo 'rustc 1.99.0' > "$HIGHLIGHT_TEST_STATE/rust-version"
        echo update >> "$HIGHLIGHT_TEST_STATE/rustup.log"
        ;;
      *) exit 1 ;;
    esac
    ;;
  tree-sitter)
    [[ -s "$HIGHLIGHT_TEST_STATE/cli-version" ]] || exit 127
    printf 'tree-sitter %s\n' "$(cat "$HIGHLIGHT_TEST_STATE/cli-version")"
    ;;
  nvim) printf '%s\n' "$NVIM_HIGHLIGHT_UPGRADE" >> "$HIGHLIGHT_TEST_STATE/nvim.log" ;;
  *) exit 0 ;;
esac
MOCK
chmod +x "$test_dir/tool"
for tool in cargo rustc rustup tree-sitter nvim git curl tar cc c++ node; do
  ln -s "$test_dir/tool" "$test_dir/cargo/bin/$tool"
done

run_case() {
  local name=$1 installed=$2 upgrade=$3 expected=$4 target=${5:-0.27.1} rust_version=${6:-1.99.0}
  local state="$test_dir/$name"
  mkdir "$state"
  printf '%s' "$installed" > "$state/cli-version"
  printf 'rustc %s\n' "$rust_version" > "$state/rust-version"
  local args=()
  [[ $upgrade == 0 ]] || args=(--upgrade)
  HIGHLIGHT_TEST_STATE="$state" CARGO_HOME="$test_dir/cargo" \
    NVIM_BIN="$test_dir/cargo/bin/nvim" TREE_SITTER_VERSION="$target" \
    bash "$repo_dir/files/nvim/highlight.sh" ${args[@]+"${args[@]}"} > "$state/output"
  if [[ $expected == install ]]; then
    [[ $(cat "$state/cli-version") == "$target" ]]
    [[ $(cat "$state/cargo.log") == *"install --locked tree-sitter-cli --version $target" ]]
  else
    [[ ! -e "$state/cargo.log" ]]
    [[ $(cat "$state/cli-version") == "$installed" ]]
  fi
  if [[ $expected == install || ( $upgrade == 1 && $rust_version != 1.99.0 ) ]]; then
    [[ $(cat "$state/output") == *HIGHLIGHT_CHANGED=1* ]]
  else
    [[ $(cat "$state/output") != *HIGHLIGHT_CHANGED=1* ]]
  fi
  if [[ $upgrade == 1 ]]; then
    [[ -s "$state/rustup.log" ]]
    [[ $(cat "$state/nvim.log") != *0* ]]
  else
    [[ ! -e "$state/rustup.log" ]]
    [[ $(cat "$state/nvim.log") != *1* ]]
  fi
  printf 'PASS: %s\n' "$name"
}

run_case missing '' 0 install
run_case incompatible 0.26.0 0 install
run_case normal-rerun 0.26.1 0 keep
run_case upgrade 0.26.1 1 install
run_case upgrade-rerun 0.27.1 1 keep
run_case newer-patch 0.27.2 1 keep
run_case newer-major 1.0.0 1 keep
run_case explicit-target 0.27.1 1 install 0.27.2
run_case rust-upgrade 0.27.1 1 keep 0.27.1 1.98.0

for version in latest 0.25.0 '0.27.1; exit 0'; do
  if TREE_SITTER_VERSION="$version" bash "$repo_dir/files/nvim/highlight.sh" > /dev/null 2>&1; then
    echo "FAIL: accepted invalid/unsupported version $version" >&2
    exit 1
  fi
done
echo 'PASS: invalid and unsupported versions rejected'
