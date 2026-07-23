#!/usr/bin/env bash
set -Eeuo pipefail

# FitPlan AI production updater.
# Designed to be called by a 1Panel "Shell script" scheduled task.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-${APP_DIR}/infra/docker-compose.yml}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/infra/.env}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
LOCK_FILE="${LOCK_FILE:-/tmp/fitplan-ai-deploy.lock}"
FORCE_DEPLOY="${FORCE_DEPLOY:-0}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git is not installed"
command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is unavailable"
command -v flock >/dev/null 2>&1 || fail "flock is not installed"

[[ -d "${APP_DIR}/.git" || -f "${APP_DIR}/.git" ]] || fail "${APP_DIR} is not a Git worktree"
[[ -f "${COMPOSE_FILE}" ]] || fail "Compose file not found: ${COMPOSE_FILE}"
[[ -f "${ENV_FILE}" ]] || fail "Production env file not found: ${ENV_FILE}"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  log "Another deployment is running; skipping this run."
  exit 0
fi

cd "${APP_DIR}"

CURRENT_BRANCH="$(git branch --show-current)"
[[ -n "${CURRENT_BRANCH}" ]] || fail "Detached HEAD is not supported"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-${CURRENT_BRANCH}}"
[[ "${CURRENT_BRANCH}" == "${DEPLOY_BRANCH}" ]] || fail "Current branch is ${CURRENT_BRANCH}, expected ${DEPLOY_BRANCH}"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  fail "Tracked files contain local changes; refusing to overwrite them"
fi

log "Fetching ${GIT_REMOTE}/${DEPLOY_BRANCH}..."
git fetch --prune "${GIT_REMOTE}"

LOCAL_REV="$(git rev-parse HEAD)"
REMOTE_REV="$(git rev-parse "${GIT_REMOTE}/${DEPLOY_BRANCH}")"

if [[ "${LOCAL_REV}" == "${REMOTE_REV}" && "${FORCE_DEPLOY}" != "1" ]]; then
  log "Already up to date (${LOCAL_REV:0:12}); nothing to deploy."
  exit 0
fi

if [[ "${LOCAL_REV}" != "${REMOTE_REV}" ]]; then
  git merge-base --is-ancestor "${LOCAL_REV}" "${REMOTE_REV}" || \
    fail "Remote branch is not a fast-forward of the deployed revision"
  log "Updating ${LOCAL_REV:0:12} -> ${REMOTE_REV:0:12}..."
  git merge --ff-only "${GIT_REMOTE}/${DEPLOY_BRANCH}"
else
  log "FORCE_DEPLOY=1; rebuilding current revision ${LOCAL_REV:0:12}."
fi

log "Validating Compose configuration..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" config --quiet

log "Building and starting FitPlan AI..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build --remove-orphans

log "Current service status:"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps
log "Deployment finished successfully."
