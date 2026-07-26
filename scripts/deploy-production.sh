#!/usr/bin/env bash
set -Eeuo pipefail

# FitPlan AI production updater.
# GitHub Actions can pass a prebuilt frontend archive so the small production
# server never needs to run the Node/Vite build. Manual 1Panel runs without an
# archive retain the original full-build fallback.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-${APP_DIR}/infra/docker-compose.yml}"
PREBUILT_COMPOSE_FILE="${PREBUILT_COMPOSE_FILE:-${APP_DIR}/infra/docker-compose.prebuilt.yml}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/infra/.env}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
LOCK_FILE="${LOCK_FILE:-/tmp/fitplan-ai-deploy.lock}"
FORCE_DEPLOY="${FORCE_DEPLOY:-0}"
COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"
PREBUILT_FRONTEND_ARCHIVE="${PREBUILT_FRONTEND_ARCHIVE:-}"
FRONTEND_DIST_DIR="${APP_DIR}/frontend/dist"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

cleanup_archive() {
  if [[ -n "${PREBUILT_FRONTEND_ARCHIVE}" && -f "${PREBUILT_FRONTEND_ARCHIVE}" ]]; then
    rm -f -- "${PREBUILT_FRONTEND_ARCHIVE}"
  fi
}

command -v git >/dev/null 2>&1 || fail "git is not installed"
command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is unavailable"
command -v flock >/dev/null 2>&1 || fail "flock is not installed"
command -v tar >/dev/null 2>&1 || fail "tar is not installed"

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
  cleanup_archive
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

if [[ -n "${PREBUILT_FRONTEND_ARCHIVE}" ]]; then
  [[ -f "${PREBUILT_FRONTEND_ARCHIVE}" ]] || fail "Prebuilt frontend archive not found: ${PREBUILT_FRONTEND_ARCHIVE}"
  [[ -f "${PREBUILT_COMPOSE_FILE}" ]] || fail "Prebuilt Compose override not found: ${PREBUILT_COMPOSE_FILE}"

  case "${FRONTEND_DIST_DIR}" in
    "${APP_DIR}"/*) ;;
    *) fail "Frontend dist path escaped the application directory" ;;
  esac

  STAGING_DIR="$(mktemp -d "${APP_DIR}/frontend/.dist-deploy.XXXXXX")"
  trap 'rm -rf -- "${STAGING_DIR}"; cleanup_archive' EXIT
  tar -xzf "${PREBUILT_FRONTEND_ARCHIVE}" -C "${STAGING_DIR}"
  [[ -f "${STAGING_DIR}/index.html" ]] || fail "Prebuilt frontend archive does not contain index.html"

  rm -rf -- "${FRONTEND_DIST_DIR}"
  mv -- "${STAGING_DIR}" "${FRONTEND_DIST_DIR}"
  trap cleanup_archive EXIT

  log "Building backend image only..."
  COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT}" \
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" build backend

  log "Packaging the prebuilt frontend into the nginx image..."
  COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT}" \
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" -f "${PREBUILT_COMPOSE_FILE}" build web

  log "Starting FitPlan AI with the newly built images..."
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" -f "${PREBUILT_COMPOSE_FILE}" \
    up -d --no-build --remove-orphans
else
  log "No prebuilt frontend archive supplied; running the full server-side build."
  COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT}" \
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" build

  log "Starting FitPlan AI with the newly built images..."
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --no-build --remove-orphans
fi

log "Current service status:"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps
cleanup_archive
trap - EXIT
log "Deployment finished successfully."
