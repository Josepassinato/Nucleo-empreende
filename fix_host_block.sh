#!/bin/bash
# Encontrar e remover o bloqueio de Host
echo "=== Procurando 'Host not allowed' no código ==="
grep -rn "Host not allowed" ~/Nucleo-empreende/ --include="*.py"

echo ""
echo "=== Removendo bloqueio se encontrado ==="
# Remover middleware de TrustedHost se existir
find ~/Nucleo-empreende -name "*.py" -exec grep -l "TrustedHost\|allowed_hosts\|Host not allowed" {} \; | while read f; do
    echo "Encontrado em: $f"
    sed -i '/TrustedHost/d' "$f"
    sed -i '/allowed_hosts/d' "$f"  
    sed -i '/Host not allowed/d' "$f"
    echo "✅ Limpo: $f"
done

echo ""
echo "=== Reiniciando ==="
systemctl restart nucleo-empreende
sleep 3
systemctl is-active nucleo-empreende
echo "✅ Pronto"
