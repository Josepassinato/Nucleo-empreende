#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   RESET PARA ONBOARDING — Fase 0                            ║
║   Limpa todos os dados da empresa atual                     ║
║   Preserva: estrutura do banco, código, configurações       ║
║   Remove: conversas, memórias, dados empresa, tarefas       ║
╚══════════════════════════════════════════════════════════════╝
"""
import sqlite3, json, os, shutil
from pathlib import Path
from datetime import datetime

DB_PATH = Path("nucleo/data/nucleo.db")

def reset():
    print("\n🧹 INICIANDO RESET PARA ONBOARDING...")
    print("=" * 50)

    if not DB_PATH.exists():
        print("⚠️  Banco não encontrado. Nada a limpar.")
        return

    # Backup antes de limpar
    backup = DB_PATH.parent / f"nucleo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_PATH, backup)
    print(f"✅ Backup criado: {backup}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Limpar conversas
    c.execute("DELETE FROM conversas")
    print(f"✅ Conversas removidas: {c.rowcount} registros")

    # 2. Limpar memórias e contexto dos agentes (resetar, não deletar)
    c.execute("""
        UPDATE agentes SET
            memoria = '{}',
            contexto = '',
            score = 7.0,
            atualizado_em = ?
    """, (datetime.now().isoformat(),))
    print(f"✅ Memória dos agentes zerada: {c.rowcount} agentes")

    # 3. Limpar dados da empresa
    c.execute("DELETE FROM empresa")
    print(f"✅ Configuração da empresa removida: {c.rowcount} registros")

    # 4. Limpar ações executadas
    c.execute("DELETE FROM acoes")
    print(f"✅ Histórico de ações removido: {c.rowcount} registros")

    # 5. Limpar transações financeiras
    c.execute("DELETE FROM transacoes")
    print(f"✅ Transações removidas: {c.rowcount} registros")

    # 6. Limpar campanhas
    c.execute("DELETE FROM campanhas")
    print(f"✅ Campanhas removidas: {c.rowcount} registros")

    # 7. Limpar tarefas
    c.execute("DELETE FROM tarefas")
    print(f"✅ Tarefas removidas: {c.rowcount} registros")

    # 8. Limpar memorias (tabela separada se existir)
    try:
        c.execute("DELETE FROM memorias")
        print(f"✅ Memórias removidas: {c.rowcount} registros")
    except:
        pass

    # 9. Limpar equipe
    try:
        c.execute("DELETE FROM equipe")
        print(f"✅ Equipe removida: {c.rowcount} registros")
    except:
        pass

    # 10. Limpar contratos
    try:
        c.execute("DELETE FROM contratos")
        print(f"✅ Contratos removidos: {c.rowcount} registros")
    except:
        pass

    # 11. Limpar fornecedores
    try:
        c.execute("DELETE FROM fornecedores")
        print(f"✅ Fornecedores removidos: {c.rowcount} registros")
    except:
        pass

    # 12. Limpar relatórios
    try:
        c.execute("DELETE FROM relatorios")
        print(f"✅ Relatórios removidos: {c.rowcount} registros")
    except:
        pass

    conn.commit()
    conn.close()

    # Limpar contexto_dono.json
    dono_path = Path("contexto_dono.json")
    if dono_path.exists():
        with open(dono_path, 'w') as f:
            json.dump({}, f)
        print("✅ contexto_dono.json zerado")

    # Limpar Redis se disponível
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
        keys = r.keys("nucleo:*")
        if keys:
            r.delete(*keys)
            print(f"✅ Redis limpo: {len(keys)} chaves removidas")
    except:
        print("ℹ️  Redis não disponível (normal se não configurado)")

    print("\n" + "=" * 50)
    print("🎉 RESET COMPLETO!")
    print("📋 Sistema pronto para onboarding de nova empresa")
    print("🔐 Próximo passo: configure autenticação e faça login como cliente")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    reset()
