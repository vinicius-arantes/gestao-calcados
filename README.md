# Passo Firme — Gestão de Estoque e Produção de Calçados

Aplicação web em Django para gestão de estoque e produção de uma fábrica de calçados,
desenvolvida como trabalho prático da disciplina **GAC116 — Programação Web**.

## Integrantes

- Vinícius Souza Arantes
- Mariana Laura Gonçalves Campos Rufo

## Descrição do projeto

O Passo Firme acompanha o caminho do calçado dentro da fábrica, da compra da matéria-prima
até o par pronto no estoque:

1. Os **materiais** entram no estoque por movimentações de compra.
2. Cada **modelo** de calçado tem uma **ficha técnica**, com o consumo de material por par.
3. Uma **ordem de produção** define modelo, cor e grade de tamanhos.
4. Ao iniciar a ordem, os materiais necessários são baixados do estoque automaticamente.
5. A ordem passa pelos **setores** da fábrica, em sequência (corte, pesponto, montagem...).
6. Ao concluir a ordem, os pares entram no estoque de produto acabado, por **SKU**
   (modelo + cor + tamanho).

O sistema tem duas áreas, ambas protegidas por login:

- **Área do usuário** (`/`): telas do dia a dia da fábrica, em que cada perfil vê e faz
  apenas o que lhe cabe.
- **Ambiente administrativo** (`/admin/`): Django Admin com tema Jazzmin e filtros, para a
  equipe de gestão.

## Tecnologias utilizadas

- Python 3.12
- Django 5.2
- django-jazzmin 3.0 (tema do ambiente administrativo)
- Bootstrap 5.3 e Bootstrap Icons (interface da área do usuário, via CDN)
- SQLite (banco de dados relacional)

## Instalação

Pré-requisitos: Python 3.10 ou superior e Git.

```bash
git clone https://github.com/vinicius-arantes/gestao-calcados.git
cd gestao-calcados
python3 -m venv .venv
source .venv/bin/activate        # No Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py popular_dados   # opcional: cria os dados de demonstração
```

No Windows, use `python` no lugar de `python3`.

## Execução

```bash
python manage.py runserver
```

- Área do usuário: <http://localhost:8000/> (sem login, abre a tela de entrada)
- Ambiente administrativo: <http://localhost:8000/admin/>

Para rodar os testes automatizados:

```bash
python manage.py test
```

### Usuários de demonstração

Criados pelo comando `popular_dados`, com a senha `passofirme123`. O comando só funciona com
`DEBUG` ligado, para que esses usuários não sejam criados em produção.

| Usuário | Perfil | O que pode fazer |
|---|---|---|
| `admin` | Administrador | Tudo, nas duas áreas |
| `gerente` | Gerente de Produção | Tudo em catálogo e produção, incluindo iniciar e concluir ordens; consultar estoque e lançar movimentações |
| `estoquista` | Estoquista | Tudo em estoque; consultar catálogo e produção |
| `operador` | Operador | Consultar catálogo, produção e produto acabado; avançar as etapas no painel dos setores. Não acessa o admin |

Quem se cadastra pela tela **Cadastre-se** recebe o perfil Operador. Um administrador pode
trocar o perfil depois, no admin.

Para criar apenas os grupos e as permissões, sem os dados de demonstração, use
`python manage.py criar_grupos`.

## Principais funcionalidades

**Contas e acesso**
- Login, logout, cadastre-se e meu perfil (dados pessoais, matrícula, telefone e setor)
- Perfis de acesso por grupos do Django: os menus e botões mostram só o que o perfil pode
  fazer, e o acesso direto pela URL sem permissão mostra a página 403

**Área do usuário**
- Painel inicial com indicadores do perfil: ordens em produção e atrasadas, pares em estoque,
  materiais a repor, próximas entregas e últimas movimentações
- Catálogo: modelos com busca e filtros, detalhe com custo, margem, ficha técnica e estoque
  por SKU; cadastro de modelos com a ficha técnica no mesmo formulário; categorias
- Estoque: materiais e fornecedores, produto acabado por SKU, histórico e lançamento de
  movimentações
- Produção: ordens com grade de tamanhos, iniciar, concluir e cancelar, avanço das etapas e
  painel com a fila de trabalho de cada setor

**Catálogo**
- Categorias, coleções, cores e tamanhos
- Modelos com ficha técnica, custo de matéria-prima e margem calculados
- Variações (SKU) com saldo em pares e estoque mínimo

**Estoque**
- Fornecedores e materiais, com saldo e estoque mínimo
- Movimentações de material e de produto acabado, que atualizam o saldo ao criar, editar e
  excluir, e bloqueiam saída maior que o saldo

**Produção**
- Ordens de produção com número automático, prioridade, prazo e grade de tamanhos
- Etapas criadas automaticamente para cada setor ativo, avançando na sequência dos setores
- Iniciar a ordem valida a ficha técnica e o saldo e dá baixa nos materiais
- Concluir a ordem exige todas as etapas concluídas e dá entrada dos pares no estoque

**Ambiente administrativo**
- Tema Jazzmin, com seletor de modo claro/escuro na barra superior
- Filtros personalizados:
  - Modelos: faixa de preço e presença de ficha técnica
  - SKUs e materiais: situação do estoque
  - Movimentações: origem (ordem de produção ou lançamento manual)
  - Ordens: prazo e setor atual
  - Usuários: perfil de acesso
- Ações em massa para iniciar, concluir e cancelar ordens e para ativar e desativar modelos

## Interface

- Bootstrap 5.3 em todas as telas da área do usuário, com layout responsivo: o menu vira
  um menu sanfonado no celular e as tabelas rolam na horizontal em telas estreitas
- **Tema claro e escuro**: o botão de lua/sol na barra superior alterna o tema. Na primeira
  visita, segue o tema do sistema operacional; depois, lembra a escolha no navegador
- O ambiente administrativo tem o seu próprio seletor de claro/escuro, na barra superior do
  Jazzmin
- Formulários, paginação, confirmação de exclusão e páginas de erro (403 e 404) seguem o
  mesmo visual

## Modelagem do banco de dados

```mermaid
erDiagram
    Categoria ||--o{ Modelo : classifica
    Colecao |o--o{ Modelo : agrupa
    Modelo ||--o{ ItemFichaTecnica : consome
    Material ||--o{ ItemFichaTecnica : compoe
    Modelo ||--o{ Variacao : possui
    Cor ||--o{ Variacao : define
    Tamanho ||--o{ Variacao : define
    Fornecedor |o--o{ Material : fornece
    Material ||--o{ MovimentacaoMaterial : movimenta
    Variacao ||--o{ MovimentacaoProduto : movimenta
    Modelo ||--o{ OrdemProducao : produz
    Cor ||--o{ OrdemProducao : define
    OrdemProducao ||--o{ ItemOrdemProducao : grade
    Tamanho ||--o{ ItemOrdemProducao : define
    OrdemProducao ||--o{ EtapaOrdem : acompanha
    Setor ||--o{ EtapaOrdem : executa
    OrdemProducao |o--o{ MovimentacaoMaterial : origina
    OrdemProducao |o--o{ MovimentacaoProduto : origina
    User ||--|| Perfil : complementa
    Setor |o--o{ Perfil : lota
```

## Estrutura do projeto

```text
gestao-calcados/
├── config/              # Configurações do projeto (settings, urls, tema Jazzmin)
│   ├── views.py         # Painel inicial
│   ├── forms.py         # Mixin que aplica o Bootstrap nos formulários
│   └── mixins.py        # Controle de acesso e telas de cadastro reutilizáveis
├── catalogo/            # Categorias, coleções, cores, tamanhos, modelos, ficha técnica e SKUs
├── estoque/             # Fornecedores, materiais e movimentações
├── producao/            # Setores, ordens de produção, grade e etapas
│   ├── services.py      # Regras do fluxo: iniciar, avançar etapa e concluir ordem
│   └── management/commands/popular_dados.py
├── contas/              # Login, cadastro, perfil de usuário e grupos de acesso
│   └── management/commands/criar_grupos.py
├── templates/
│   ├── base.html        # Layout com menu, tema claro/escuro e mensagens
│   ├── includes/        # Menu, campos de formulário, paginação
│   └── contas/ catalogo/ estoque/ producao/   # Telas de cada app
├── static/css/app.css   # Ajustes visuais e cores da marca nos dois temas
├── manage.py
└── requirements.txt
```

Cada app segue a mesma organização: `models.py` (tabelas), `admin.py` (ambiente
administrativo), `views.py`, `forms.py` e `urls.py` (área do usuário) e `tests.py`.

## Fluxo de trabalho no Git

- `main`: versões entregues
- `develop`: integração das funcionalidades
- `feature/*` e `hotfix/*`: uma branch por tarefa, integrada à `develop` por pull request
  revisado pela outra pessoa do grupo
