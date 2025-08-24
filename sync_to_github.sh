#!/usr/bin/env bash
set -euo pipefail

#############################################
# Configurações (ajuste se necessário)
#############################################
REPO_DIR="${REPO_DIR:-$HOME/projects/trading-bots}"
DEFAULT_BRANCH="main"                       # branch padrão
TREE_DEPTH="${TREE_DEPTH:-3}"               # profundidade do snapshot
SNAPSHOT_FILE="../estrutura_trading_bots.txt"
DRY_RUN="${DRY_RUN:-0}"                     # 1 = não aplica mudanças
GIT_USER_NAME_DEFAULT="Weder VPS"
GIT_USER_EMAIL_DEFAULT="weder@example.com"

#############################################
# Funções utilitárias
#############################################
err() { printf "\033[31m[ERRO]\033[0m %s\n" "$*" >&2; }
ok()  { printf "\033[32m[OK]\033[0m %s\n" "$*"; }
inf() { printf "\033[36m[INFO]\033[0m %s\n" "$*"; }
warn(){ printf "\033[33m[AVISO]\033[0m %s\n" "$*"; }

need() {
  command -v "$1" >/dev/null 2>&1 || { err "comando '$1' não encontrado"; exit 1; }
}

#############################################
# Args
#############################################
COMMIT_MSG=""
BRANCH="$DEFAULT_BRANCH"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message) COMMIT_MSG="$2"; shift 2;;
    -b|--branch)  BRANCH="$2"; shift 2;;
    -h|--help)
      cat <<EOF
Uso: $(basename "$0") [opções]

Opções:
  -m, --message  "mensagem de commit"
  -b, --branch   nome da branch (default: $DEFAULT_BRANCH)

Variáveis de ambiente:
  REPO_DIR=~/projects/trading-bots   (raiz do repositório)
  TREE_DEPTH=3                        (profundidade do 'tree')
  DRY_RUN=1                           (somente simulação; não grava nada)
EOF
      exit 0;;
    *) err "opção desconhecida: $1"; exit 1;;
  esac
done

#############################################
# Pré-checagens
#############################################
need git
need bash

if [[ ! -d "$REPO_DIR/.git" ]]; then
  err "Diretório não parece um repositório git: $REPO_DIR"
  exit 1
fi

cd "$REPO_DIR"

# Remoto
if ! git remote get-url origin >/dev/null 2>&1; then
  err "Remoto 'origin' não configurado. Ex.: git remote add origin git@github.com:SEU-USUARIO/trading-bots.git"
  exit 1
fi
REMOTE_URL="$(git remote get-url origin)"
inf "Remoto origin: $REMOTE_URL"

# Branch atual (ou cria/muda)
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  warn "Branch atual é '$CURRENT_BRANCH', desejada: '$BRANCH'"
  if [[ "$DRY_RUN" == "0" ]]; then
    # cria se não existe; troca para a desejada
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git switch "$BRANCH"
    else
      git switch -c "$BRANCH"
    fi
    ok "Branch ativa: $(git rev-parse --abbrev-ref HEAD)"
  else
    inf "DRY_RUN=1 → não mudando de branch"
  fi
fi

# Config git user (global) se vazio
if [[ -z "$(git config --global user.name || true)" ]]; then
  warn "git user.name global não configurado → usando padrão: $GIT_USER_NAME_DEFAULT"
  [[ "$DRY_RUN" == "0" ]] && git config --global user.name "$GIT_USER_NAME_DEFAULT"
fi
if [[ -z "$(git config --global user.email || true)" ]]; then
  warn "git user.email global não configurado → usando padrão: $GIT_USER_EMAIL_DEFAULT"
  [[ "$DRY_RUN" == "0" ]] && git config --global user.email "$GIT_USER_EMAIL_DEFAULT"
fi

#############################################
# Snapshot da estrutura (tree → arquivo)
#############################################
SNAP_OK=0
if command -v tree >/dev/null 2>&1; then
  inf "Gerando snapshot com 'tree' (profundidade $TREE_DEPTH)"
  if [[ "$DRY_RUN" == "0" ]]; then
    tree -a -L "$TREE_DEPTH" > "$SNAPSHOT_FILE" || true
  fi
  SNAP_OK=1
else
  warn "'tree' não encontrado; instalando é recomendado: sudo apt update && sudo apt install tree -y"
fi

# Fallback com find (menos amigável)
if [[ "$SNAP_OK" -eq 0 ]]; then
  inf "Usando fallback com 'find'"
  if [[ "$DRY_RUN" == "0" ]]; then
    (cd .. && find "$(basename "$REPO_DIR")" -maxdepth "$TREE_DEPTH" -print) > "$SNAPSHOT_FILE"
  fi
fi

[[ "$DRY_RUN" == "0" ]] && ok "Snapshot salvo em: $SNAPSHOT_FILE"

#############################################
# Git add/commit/push
#############################################
# Atualiza índice
inf "git add ."
[[ "$DRY_RUN" == "0" ]] && git add . || true

# Define mensagem de commit
TS="$(date -u +'%Y-%m-%d %H:%M:%SZ')"
if [[ -z "$COMMIT_MSG" ]]; then
  COMMIT_MSG="sync: snapshot + atualizações ($TS)"
fi

# Commit somente se houver alterações
CHANGED="0"
git diff --cached --quiet || CHANGED="1"

if [[ "$CHANGED" == "1" ]]; then
  inf "git commit -m \"$COMMIT_MSG\""
  [[ "$DRY_RUN" == "0" ]] && git commit -m "$COMMIT_MSG" || true
else
  warn "Nenhuma alteração para commit (índice limpo)."
fi

# Push
if [[ "$DRY_RUN" == "0" ]]; then
  inf "git push origin \"$BRANCH\""
  git push origin "$BRANCH"
  ok "Push concluído."
else
  inf "DRY_RUN=1 → não fez push."
fi

#############################################
# Dicas finais
#############################################
ok "Finalizado."
echo "Dica: exporte a variável DRY_RUN=1 para simular, e TREE_DEPTH=N para ajustar profundidade."



