# Atualização e rollback

## Antes

1. confirmar health verde;
2. gerar backup PostgreSQL/corporativo;
3. registrar versões de Servidor/Central/Clientes/Agentes;
4. fechar sessões de manutenção quando necessário;
5. preservar instalador anterior.

## Ordem de update

Servidor → Central → Clientes → Agentes TI. Não deixe clientes novos apontando por longos períodos para servidor incompatível.

## Rollback

Se a atualização falhar antes de mudança de dados, reinstale binário anterior e valide health. Se houve migration compatível, prefira corrigir para frente. Restore de banco é último recurso e deve ser executado somente a partir de backup validado e janela de manutenção.

## Atualização assinada

`core.atualizacoes` aceita apenas manifesto HTTPS assinado com Ed25519 (`DATA_INTELLIGENCE_UPDATE_PUBLIC_KEY`), valida tamanho e SHA-256 e prepara o ZIP fora da instalação. `DataIntelligenceUpdateHelper.exe` é copiado para uma pasta temporária, troca a versão instalada, inicia o componente e consulta health. Se o health não ficar verde, restaura atomicamente a pasta anterior e reinicia a versão conhecida.

Migrations precisam permanecer compatíveis com rollback de binário. Uma migration destrutiva exige plano de migração de dados separado; o helper não reverte banco automaticamente.
