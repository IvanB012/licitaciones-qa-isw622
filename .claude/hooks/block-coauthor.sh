#!/bin/sh
# Hook PreToolUse (Bash): bloquea "git commit" cuyo mensaje contenga "Co-Authored-By" o "Claude".
# Entrada: JSON del tool call por stdin. Salida: exit 2 = bloquear (stderr se muestra a Claude).
input=$(cat)

case "$input" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

# Solo la parte posterior a "git commit"; se quita ".claude" (rutas) para evitar falsos positivos.
rest="${input#*git commit}"
rest=$(printf '%s' "$rest" | sed 's/\.claude//g')

if printf '%s' "$rest" | grep -qiE 'co-authored-by|claude'; then
  echo "BLOQUEADO: el mensaje de commit no puede contener 'Co-Authored-By' ni 'Claude'. Los commits salen solo a nombre del humano." >&2
  exit 2
fi
exit 0
