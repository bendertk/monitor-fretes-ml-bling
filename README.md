# 🚚 Monitor de Fretes ML ↔ Bling

Sistema de monitoramento de prazos de entrega para pedidos do Mercado Livre (ME1) integrados com o Bling ERP.

## 📋 Funcionalidades

- **Coleta Automática**: Busca pedidos ME1 do ML e pedidos faturados no Bling
- **Correlação**: Cruza dados usando `numeroLoja` do Bling
- **Cálculo de Prazos**: Determina dias restantes e status (No Prazo/Em Risco/Atrasado)
- **Dashboard Interativo**: Visualização completa com filtros e gráficos
- **Atualização Diária**: Executa 2x ao dia via GitHub Actions

## 🏗️ Arquitetura

```
ML API ─────┐
             ├─→ Python Scripts ─→ Google Sheets ─→ Streamlit Dashboard
Bling API ──┘                    (GitHub Actions)
```

## 🚀 Setup

### 1. Criar Planilha Google

1. Acesse [Google Sheets](https://sheets.google.com)
2. Crie uma nova planilha chamada "Monitor de Fretes"
3. Copie o ID da planilha (trecho da URL entre `/d/` e `/edit`)
4. Compartilhe com o email da Service Account do GCP

### 2. Configurar Google Cloud Platform

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto
3. Habilite as APIs:
   - Google Sheets API
   - Google Drive API
4. Crie uma Service Account:
   - IAM & Admin → Service Accounts
   - Crie uma nova com permissão "Editor"
   - Baixe o arquivo JSON da chave
5. Compartilhe a planilha com o email da Service Account

### 3. Configurar GitHub Secrets

Acesse Settings → Secrets and variables → Actions e adicione:

| Secret | Descrição |
|--------|-----------|
| `ML_REFRESH_TOKEN` | Refresh token do ML (conta Sollar Sul) |
| `BLING_REFRESH_TOKEN` | Refresh token do Bling |
| `BLING_CLIENT_ID` | Client ID do Bling |
| `BLING_CLIENT_SECRET` | Client Secret do Bling |
| `GOOGLE_SHEETS_ID` | ID da planilha Google |
| `GOOGLE_SERVICE_ACCOUNT` | JSON completo da Service Account |

### 4. Deploy no Streamlit Community Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Conecte sua conta GitHub
3. Selecione o repositório
4. Configure:
   - Main file path: `app/streamlit_app.py`
   - Python version: `3.11`
5. Adicione os secrets no painel do Streamlit (mesmos do GitHub)
6. Deploy!

### 5. Ativar GitHub Actions

1. Vá para a aba Actions do repositório
2. Clique em "I understand my workflows, go ahead and enable them"
3. O workflow executará automaticamente às 08:00 e 18:00 (horário de Brasília)

## 📊 Dashboard

O dashboard mostra:

- **KPIs**: Total de pedidos, no prazo, em risco, atrasados
- **Gráfico de Status**: Distribuição por status de prazo
- **Gráfico de Transportadora**: Volume por transportadora
- **Tabela Detalhada**: Todos os pedidos com filtros
- **Pedidos por UF**: Distribuição geográfica

### Filtros Disponíveis

- Status do prazo
- Transportadora
- UF de destino
- Busca por NF, ML# ou destinatário

## 🔧 Desenvolvimento Local

```bash
# Clonar repositório
git clone <url>
cd monitor-fretes-ml-bling

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
# Crie um arquivo .env com as credenciais

# Executar sincronização
python src/main.py --days 15

# Executar dashboard
streamlit run app/streamlit_app.py
```

## 📁 Estrutura

```
monitor-fretes-ml-bling/
├── .github/workflows/
│   └── daily_sync.yml      # GitHub Actions
├── .streamlit/
│   └── config.toml         # Configuração Streamlit
├── app/
│   └── streamlit_app.py    # Dashboard
├── config/
│   └── .gitignore          # Ignorar credenciais
├── src/
│   ├── __init__.py
│   ├── ml_api.py           # Funções ML
│   ├── bling_api.py        # Funções Bling
│   ├── sheets_api.py       # Google Sheets
│   ├── correlacao.py       # Match ML ↔ Bling
│   ├── calculo_prazo.py    # Cálculo de prazos
│   └── main.py             # Script principal
├── requirements.txt
└── README.md
```

## ⚠️ Importante

- Os tokens do ML expiram em 6 horas (refresh automático)
- Os tokens do Bling expiram em 6 horas (refresh automático)
- O GitHub Actions roda em UTC (horário de Brasília = UTC-3)
- O Streamlit Community Cloud tem limite de 1GB de memória
- Dados atualizados 2x ao dia (08:00 e 18:00)

## 📈 Próximos Passos

- [ ] Adicionar alertas via Telegram
- [ ] Implementar cache local para reduzir chamadas à API
- [ ] Adicionar métricas de performance por transportadora
- [ ] Implementar exportação de relatórios
- [ ] Adicionar predição de atrasos baseada em histórico
