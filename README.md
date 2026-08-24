# Base gerencial — Filial Brasília

Aplicação local para processos, agenda, ordens de serviço, etapas, equipes, avaliações e pool de comissões. Os arquivos operacionais existentes não são alterados; o banco novo nasce pelas migrations.

## Execução recomendada com Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

O container aplica migrations e cria os cadastros iniciais de forma idempotente antes de iniciar o servidor. A aplicação responde em `http://127.0.0.1:5000` e possui healthcheck em `/health`. Defina obrigatoriamente `SECRET_KEY`, `ADMIN_PASSWORD` e, para integrações, `API_TOKEN` no `.env` antes de uso real.

Para encerrar sem remover o banco persistente:

```bash
docker compose down
```

## Desenvolvimento local opcional

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
export FLASK_APP=wsgi:app
flask db upgrade
flask seed
flask run
```

No primeiro uso local, se as variáveis não forem alteradas, entre com `admin@local` / `admin` e troque as credenciais antes de uso real. Por padrão o SQLite fica em `~/.local/share/filial-bsb`, fora desta pasta sincronizada.

## API

A API fica em `/api/v1`. Ela aceita uma sessão web autenticada ou `Authorization: Bearer <API_TOKEN>`. Datas são ISO 8601, UUIDs são usados como identificadores e erros seguem `{ "error": { "code", "message", "details" } }`.

### Solicitações e processos

Uma solicitação existe antes do número de processo e registra agente, cliente, endereço, volume e intervalos de datas. O fluxo é `recebida → negociacao → confirmada → convertida`: a data inicial é o pedido do agente, a data ofertada registra a negociação e a data final é o intervalo que será usado pelo serviço. Para confirmar, são obrigatórios o intervalo final e a data do e-mail positivo.

O sistema nunca gera o número. Depois que ele chegar por e-mail, crie o processo em `POST /api/v1/processos` informando também `solicitacao_id`; somente uma solicitação confirmada e ainda não vinculada pode ser convertida.

## Backup

```bash
python scripts/backup.py ~/.local/share/filial-bsb/filial_bsb.db /caminho/OneDrive/backups
python scripts/restore_check.py /caminho/OneDrive/backups/filial-bsb-AAAAMMDD-HHMMSS.sqlite3
```

Agende o primeiro comando diariamente no sistema operacional. A rotina mantém até 35 cópias; a política recomendada é sete diárias e quatro semanais no mecanismo de sincronização/retensão do destino.

## Migração de dados

Importações devem passar por `importacao_registros` antes da publicação. Cada linha conserva arquivo, aba, linha, checksum e JSON bruto. O conteúdo operacional anterior não é importado automaticamente e permanece intacto até a matriz de mapeamento ser revisada.

Para criar o primeiro diagnóstico sem tocar no banco persistente, use um SQLite descartável. Os CSVs esperados são `agenda.CSV`, `servicos.CSV` e `avaliacao_bruta.CSV`, separados por `;` e codificados em Latin-1.

```bash
export DATABASE_URL=sqlite:////tmp/filial-bsb-importacao.sqlite3
flask --app wsgi:app db upgrade
flask --app wsgi:app seed
flask --app wsgi:app importar carregar data_old --dry-run
flask --app wsgi:app importar carregar data_old
flask --app wsgi:app importar relatorio UUID-DO-LOTE \
  --saida reports/diagnostico-migracao.xlsx
```

A carga é idempotente: o mesmo conjunto de arquivos reutiliza o lote existente, enquanto qualquer alteração cria um snapshot novo. O relatório local contém os dados brutos e não deve ser enviado ao Git; `data_old/`, `reports/` e bancos SQLite estão ignorados. Esses comandos alimentam somente o staging e nunca publicam registros nas tabelas operacionais.
