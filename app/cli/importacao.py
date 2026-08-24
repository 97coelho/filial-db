from pathlib import Path

import click

from ..services.importacao import ErroImportacao, carregar as carregar_fontes, gerar_relatorio


@click.group()
def importar():
    """Carrega e diagnostica fontes legadas sem publicá-las."""


@importar.command("carregar")
@click.argument("diretorio", type=click.Path(path_type=Path, file_okay=False))
@click.option("--dry-run", is_flag=True, help="Analisa sem gravar no staging.")
def carregar(diretorio: Path, dry_run: bool):
    """Carrega os três CSVs de DIRETORIO em um lote imutável."""
    try:
        resultado = carregar_fontes(diretorio, dry_run=dry_run)
    except ErroImportacao as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Lote: {resultado['lote']}")
    click.echo(f"Linhas: {resultado['linhas']}")
    click.echo(
        f"Diagnóstico: {resultado['erros']} erro(s), "
        f"{resultado['avisos']} aviso(s), "
        f"{resultado['processos_orfaos']} processo(s) sem agenda, "
        f"{resultado['solicitacoes']} solicitação(ões), "
        f"{resultado['registros_excluidos']} registro(s) excluído(s)"
    )
    if dry_run:
        click.echo("Dry-run concluído; nenhum registro foi gravado.")
    elif resultado["reutilizado"]:
        click.echo("O conjunto já existia; o lote foi reutilizado sem duplicação.")
    else:
        click.echo("Staging gravado; nenhuma tabela operacional foi alterada.")


@importar.command("relatorio")
@click.argument("lote")
@click.option(
    "--saida", required=True, type=click.Path(path_type=Path, dir_okay=False),
    help="Caminho do arquivo XLSX local.",
)
def relatorio(lote: str, saida: Path):
    """Gera o diagnóstico XLSX de LOTE."""
    try:
        totais = gerar_relatorio(lote, saida)
    except ErroImportacao as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Relatório: {saida.resolve()}")
    click.echo(
        f"Linhas: {totais['linhas']} | Erros: {totais['erros']} | "
        f"Avisos: {totais['avisos']} | Sem agenda: {totais['processos_orfaos']} | "
        f"Solicitações: {totais['solicitacoes']} | "
        f"Excluídos: {totais['registros_excluidos']}"
    )
