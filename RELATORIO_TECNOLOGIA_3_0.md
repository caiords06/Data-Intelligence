# Tecnologia 3.0 — Remodelação de interface e operação de rede

## Objetivo

Esta entrega remodela o módulo de Tecnologia para que ele deixe de ser uma cópia do padrão usado pelos demais departamentos. A nova experiência é uma central de suporte e operações de TI, com navegação própria, rede explícita, inventário interativo, diagnóstico, telemetria e acesso remoto auditado.

A remodelação mantém as regras empresariais existentes, mas muda a interpretação visual e operacional do módulo.

## 1. Dois níveis de experiência

### Portal de suporte

Qualquer usuário autenticado pode entrar em Tecnologia mesmo sem possuir permissão operacional de TI. Nesse caso, ele vê somente:

- Início do suporte;
- Abrir chamado;
- Meus chamados.

O backend também foi endurecido: um usuário comum não consegue forjar o `solicitante_id`, escolher outro técnico ou associar arbitrariamente ativos/sistemas ao criar chamado pelo portal. O solicitante é sempre o próprio usuário autenticado.

### Operação técnica

Perfis com permissão de TI recebem a central completa:

- Cockpit de TI;
- Rede ao vivo;
- Ativos gerenciados;
- Service Desk;
- Acesso remoto;
- Segmentos / firewall;
- Monitoramento;
- Sistemas;
- Manutenções;
- Licenças;
- Contratos;
- Base de conhecimento;
- Mudanças;
- Problemas;
- Segurança;
- Alertas;
- Relatórios;
- Auditoria.

## 2. Rede não é mais presumida

A plataforma não cadastra automaticamente a rede atual do computador e não escolhe a LAN como padrão.

O fluxo passa a ser:

1. operador abre **Rede ao vivo**;
2. cadastra explicitamente o CIDR privado desejado;
3. autoriza a descoberta daquele segmento;
4. opcionalmente prepara a regra local do Firewall do Windows;
5. executa a descoberta.

Sem segmento cadastrado, a interface informa explicitamente que nenhuma rede foi escolhida.

## 3. CRUD completo de segmentos

Na própria tela de Rede ao vivo agora existem:

- `+ SEGMENTO`;
- `EDITAR`;
- `REMOVER`;
- `AUTORIZAR DESCOBERTA` / `REVOGAR AUTORIZAÇÃO`;
- `PREPARAR FIREWALL`;
- `REMOVER REGRA`.

A remoção é lógica/auditável. Um CIDR digitado incorretamente não precisa permanecer na operação, mas sua trilha histórica não é destruída.

## 4. Firewall do Windows

O pedido de “liberar o firewall” foi implementado de forma restrita e segura.

A plataforma **não desativa o Windows Firewall** e não abre portas administrativas genéricas. Quando o operador confirma, é criada somente uma regra:

- entrada;
- ICMPv4 Echo Request;
- perfil `Private`;
- origem limitada ao CIDR privado cadastrado;
- nomeada por segmento para poder ser removida depois.

O primeiro segmento oferece um fluxo guiado de autorização e preparação do firewall. A criação da regra exige privilégios administrativos do Windows.

## 5. Descoberta real e conservadora

Foi criada uma camada `enterprise/rede_ti.py`.

Ela permite descobrir presença em segmentos privados explicitamente autorizados usando:

- ICMP;
- resolução reversa de hostname;
- cache ARP local;
- concorrência limitada;
- limite rígido de 1.024 hosts por descoberta interativa.

Não são executados:

- port scan;
- exploração;
- autenticação remota;
- captura de pacotes;
- comandos em máquinas encontradas.

Equipamentos encontrados via ARP mas que não respondem ICMP aparecem como **Detectado**, e não como Online. Isso evita falsa certeza sobre disponibilidade.

## 6. Diagnóstico de conectividade

A tela permite testar:

- gateway configurado;
- resolução DNS do computador;
- conectividade de saída com a Internet;
- latência aproximada.

O resultado é apresentado ao operador sem alterar a configuração da rede.

## 7. Rede ao vivo

A nova tela mostra:

- segmento ativo;
- CIDR;
- gateway;
- autorização;
- estado da regra de firewall;
- última descoberta;
- dispositivos conhecidos;
- quantidade online.

A tabela contém IP, hostname, MAC, estado, patrimônio, tipo e última detecção.

Ao selecionar um dispositivo, o painel lateral consolida dados de descoberta, ativo e telemetria quando disponíveis, incluindo:

- IP;
- hostname;
- MAC;
- segmento;
- ping;
- patrimônio;
- responsável;
- usuário da sessão;
- sistema operacional;
- versão do SO;
- processador;
- RAM;
- armazenamento;
- CPU atual;
- memória atual;
- disco atual;
- latência do agente;
- versão do agente;
- provedor remoto;
- status remoto.

## 8. Dispositivo → ativo

Um equipamento descoberto pode ser:

- identificado manualmente;
- vinculado a ativo existente;
- convertido em novo ativo;
- removido da visão operacional.

O vínculo atualiza IP, MAC, hostname e conectividade do ativo sem destruir seu patrimônio/histórico.

## 9. Ativos gerenciados

A tela de ativos foi separada do inventário genérico. Ela possui busca, CRUD e painel de diagnóstico lateral.

Dados exibidos quando conhecidos:

- patrimônio;
- hostname e FQDN;
- IP e MAC;
- usuário responsável;
- usuário logado na estação;
- SO e versão;
- processador;
- RAM e disco;
- CPU, memória e disco percentuais;
- latência;
- versão do agente;
- último contato;
- AnyDesk/TeamViewer/RustDesk e status relacionado.

O primeiro ativo da lista é selecionado automaticamente para evitar painel vazio sem necessidade.

## 10. Agente TI

O projeto já possuía `agente_ti`. A Tecnologia 3.0 adiciona no domínio a função `registrar_snapshot_agente()`, capaz de transformar o payload existente do agente em:

- inventário do ativo;
- estado online;
- telemetria;
- usuário da sessão;
- versão detalhada do SO;
- identidade do AnyDesk;
- última comunicação.

### Limite atual

O **receptor HTTP/HTTPS central do agente ainda não foi implementado**. O `agente_ti.transport` já possui contrato, assinatura HMAC e endpoint esperado, mas ainda falta o serviço servidor que valide e encaminhe o heartbeat para `registrar_snapshot_agente()`.

Portanto, descoberta de rede e CRUD já são operacionais; o inventário avançado distribuído fica completo quando esse receptor central for adicionado.

## 11. Acesso remoto

Foi preservada a trilha empresarial já existente:

1. selecionar ativo vinculado;
2. confirmar permissão;
3. informar justificativa;
4. confirmar consentimento/autorização;
5. registrar a sessão;
6. abrir AnyDesk, TeamViewer ou RustDesk pelo destino configurado;
7. registrar o resultado ao encerrar.

Nenhuma senha de acesso remoto é armazenada na tela ou adicionada automaticamente ao ativo.

## 12. Contexto de threads corrigido

Descoberta e diagnóstico rodam fora da thread principal do Tkinter para evitar congelamento da interface.

Antes de iniciar o worker, empresa e filial são congeladas no ator da operação. Assim, troca de contexto da sessão durante uma descoberta não faz o trabalho terminar em outra filial.

## 13. Migração 011

Nova migração:

`enterprise/migrations/011_tecnologia_operacoes_rede.py`

Principais campos adicionados:

### `ti_segmentos_rede`
- `firewall_status`;
- `firewall_regra`;
- `ultima_varredura_em`;
- `ultima_varredura_total`;
- `ultima_varredura_online`.

### `ti_dispositivos_rede`
- `ativo`;
- `ultimo_ping_ms`;
- `observacao`.

### `ti_ativos`
- `agent_id`;
- `fqdn`;
- `versao_sistema`;
- `arquitetura`;
- `usuario_sessao`;
- `remote_alias`;
- `remote_status`;
- `remote_versao`.

## 14. Roteamento e permissões

O catálogo de módulos agora trata Tecnologia de forma especial:

- usuário com TI: `ABRIR PAINEL`;
- usuário sem TI: `SUPORTE DISPONÍVEL` / `ABRIR SUPORTE`.

O router central permite entrar em Tecnologia mesmo sem `ti.ler`, mas a própria tela rebaixa qualquer tentativa de seção operacional para o portal público.

## 15. Testes

Após a remodelação:

- `149` testes foram coletados e exercitados em lotes;
- todos os arquivos de teste passaram;
- `9` smoke tests Tkinter passaram;
- `52` subtests gráficos do smoke passaram;
- compilação Python passou;
- `tabnanny` passou;
- banco incluído passou `PRAGMA integrity_check = ok`;
- `PRAGMA foreign_key_check` retornou zero violações;
- migração `enterprise_011_tecnologia_operacoes_rede` foi aplicada ao banco incluído.

Foram adicionadas regressões específicas em `tests/test_tecnologia_3_0.py` para portal público, isolamento de chamados, CRUD de rede, firewall mockado, descoberta, vínculo de ativos, snapshot do agente e limites do scanner.

## 16. Arquivos principais alterados/criados

- `interface/tecnologia.py`
- `interface/catalogo_modulos.py`
- `main.py`
- `enterprise/tecnologia.py`
- `enterprise/rede_ti.py`
- `enterprise/firewall_ti.py`
- `enterprise/migrations/011_tecnologia_operacoes_rede.py`
- `enterprise/migrations/__init__.py`
- `tests/test_tecnologia_3_0.py`
- `tests/test_interface_smoke_v8_2.py`
- `README.md`

## 17. Pré-visualizações reais

Capturas geradas a partir da interface Tkinter desta entrega:

- `assets/previews/tecnologia_3_0/portal_suporte.png`
- `assets/previews/tecnologia_3_0/cockpit_ti.png`
- `assets/previews/tecnologia_3_0/rede_ao_vivo.png`
- `assets/previews/tecnologia_3_0/ativos_gerenciados.png`
