"""Linter de integridade estrutural e de conexões para o ZettelBrain.

Realiza análises estáticas determinísticas na base de conhecimento, incluindo:
- Links mortos (wikilinks apontando para arquivos inexistentes)
- Notas órfãs (notas sem nenhuma referência de entrada no grafo conceitual)
- Ligação mínima (notas permanentes ativas com menos de 2 links de saída no corpo)
- Referências a notas deprecadas
- Padrões emergentes (termos em negrito que aparecem em 3+ notas sem nota correspondente)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config import load_settings
from logger import log_skill_execution


@dataclass
class LintError:
    """Representa um erro crítico de integridade (ex: link morto)."""

    type: str
    file_path: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LintWarning:
    """Representa um aviso de melhoria (ex: órfão, ligação mínima)."""

    type: str
    file_path: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LintResult:
    """Estrutura com os resultados consolidados do linter."""

    errors: list[LintError] = field(default_factory=list)
    warnings: list[LintWarning] = field(default_factory=list)
    emergent_patterns: list[str] = field(default_factory=list)
    total_notes: int = 0
    literature_count: int = 0
    permanent_count: int = 0
    other_count: int = 0


def slugify(text: str) -> str:
    """Converte um texto em um slug amigável para nome de arquivo.

    Args:
        text: Texto de entrada.

    Returns:
        str: Texto slugificado.
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]:
    """Parseia o frontmatter YAML e o corpo de uma nota de forma simples e segura.

    Args:
        content: Conteúdo em texto do arquivo markdown.

    Returns:
        tuple[dict[str, Any], str]: Metadados do frontmatter e o texto do corpo.
    """
    frontmatter: dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_text = parts[1]
            body = parts[2].strip()

            for line in yaml_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()

                # Trata listas tipo [item1, item2] ou [[link1]]
                if val.startswith("[") and val.endswith("]"):
                    list_content = val[1:-1].strip()
                    if list_content.startswith("[") and list_content.endswith("]"):
                        # Lista de wikilinks no frontmatter: [[link1]], [[link2]]
                        items = []
                        for item in list_content.split(","):
                            item = item.strip().strip("[").strip("]")
                            if item:
                                items.append(item)
                        frontmatter[key] = items
                    else:
                        # Lista simples de strings
                        items = []
                        for item in list_content.split(","):
                            item = item.strip().strip('"').strip("'")
                            if item:
                                items.append(item)
                        frontmatter[key] = items
                else:
                    # Valor escalar (string, boolean, int)
                    val = val.strip('"').strip("'")
                    if val.lower() == "true":
                        frontmatter[key] = True
                    elif val.lower() == "false":
                        frontmatter[key] = False
                    else:
                        frontmatter[key] = val
    return frontmatter, body


class ZettelLinter:
    """Implementa o motor de linter e validação estática do ZettelBrain."""

    def __init__(self, zettelkasten_path: Path) -> None:
        """Inicializa o linter com o caminho do cofre ZettelBrain.

        Args:
            zettelkasten_path: Caminho da pasta raiz zettelbrain/.
        """
        self.zettelkasten_path = zettelkasten_path
        self.existing_files: dict[str, Path] = {}
        self.notes: dict[str, dict[str, Any]] = {}

    def scan_vault(self) -> None:
        """Varre o cofre para mapear arquivos existentes e ler metadados das notas."""
        # 1. Mapeia todos os arquivos .md no ZettelBrain
        for file in self.zettelkasten_path.rglob("*.md"):
            slug = file.stem
            self.existing_files[slug] = file

            # Apenas analisamos notas em literature/ e permanent/ de forma detalhada
            in_literature = "literature" in file.parts
            in_permanent = "permanent" in file.parts

            if in_literature or in_permanent:
                try:
                    content = file.read_text(encoding="utf-8")
                    frontmatter, body = parse_frontmatter_and_body(content)
                    self.notes[slug] = {
                        "path": file,
                        "relative_path": str(file.relative_to(self.zettelkasten_path)),
                        "type": "literature" if in_literature else "permanent",
                        "frontmatter": frontmatter,
                        "body": body,
                        "wikilinks": self._extract_wikilinks(body, frontmatter),
                        "bold_terms": self._extract_bold_terms(body),
                    }
                except Exception as exc:
                    # Em caso de falha de leitura
                    self.notes[slug] = {
                        "path": file,
                        "relative_path": str(file.relative_to(self.zettelkasten_path)),
                        "type": "literature" if in_literature else "permanent",
                        "error": str(exc),
                    }

    def _extract_wikilinks(self, body: str, frontmatter: dict[str, Any]) -> list[str]:
        """Extrai wikilinks [[link]] únicos do corpo e frontmatter (sources).

        Args:
            body: O corpo em texto do markdown.
            frontmatter: O dicionário do frontmatter.

        Returns:
            list[str]: Lista de slugs linkados de forma única.
        """
        wikilinks = set()

        # Extração de wikilinks do corpo
        body_matches = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", body)
        for match in body_matches:
            wikilinks.add(match.strip())

        # Extração de wikilinks da chave 'sources' do frontmatter
        sources = frontmatter.get("sources", [])
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, str):
                    # Limpa se tiver colchetes residuais
                    cleaned = source.strip().strip("[").strip("]")
                    if cleaned:
                        wikilinks.add(cleaned)
        elif isinstance(sources, str):
            cleaned = sources.strip().strip("[").strip("]")
            if cleaned:
                wikilinks.add(cleaned)

        return sorted(list(wikilinks))

    def _extract_bold_terms(self, body: str) -> list[str]:
        """Extrai termos destacados em **negrito** no corpo da nota.

        Args:
            body: O texto do corpo da nota.

        Returns:
            list[str]: Lista de termos únicos destacados em negrito.
        """
        bold_matches = re.findall(r"\*\*([^*]+)\*\*", body)
        terms = set()
        for match in bold_matches:
            cleaned = match.strip()
            # Descarta termos vazios ou muito curtos para evitar falsos positivos
            if cleaned and len(cleaned) > 2:
                terms.add(cleaned)
        return sorted(list(terms))

    def run(self) -> LintResult:
        """Executa a validação e retorna a estrutura de resultados consolidados.

        Returns:
            LintResult: Resultados do processo de linting.
        """
        result = LintResult(total_notes=len(self.existing_files))

        # Classificação do volume por tipo
        for file in self.existing_files.values():
            if "literature" in file.parts:
                result.literature_count += 1
            elif "permanent" in file.parts:
                result.permanent_count += 1
            else:
                result.other_count += 1

        # Construção de mapas de links de entrada e termos para padrões emergentes
        incoming_links: dict[str, list[str]] = {slug: [] for slug in self.existing_files}
        bold_terms_occurrences: dict[str, list[str]] = {}

        # Mapeamento do grafo
        for source_slug, info in self.notes.items():
            if "error" in info:
                result.errors.append(
                    LintError(
                        type="parsing_error",
                        file_path=info["relative_path"],
                        message=f"Falha ao ler ou parsear o arquivo: {info['error']}",
                    )
                )
                continue

            # Rastreamento de links mortos e conexões
            for target_slug in info["wikilinks"]:
                if target_slug not in self.existing_files:
                    # Link Morto
                    msg = f"Link morto detectado: [[{target_slug}]] aponta para nota inexistente."
                    result.errors.append(
                        LintError(
                            type="dead_link",
                            file_path=info["relative_path"],
                            message=msg,
                            details={"target": target_slug},
                        )
                    )
                else:
                    # Incrementa links de entrada
                    if target_slug not in incoming_links:
                        incoming_links[target_slug] = []
                    incoming_links[target_slug].append(source_slug)

            # Rastreamento de termos para padrões emergentes
            for term in info["bold_terms"]:
                if term not in bold_terms_occurrences:
                    bold_terms_occurrences[term] = []
                bold_terms_occurrences[term].append(source_slug)

        # Validação de regras adicionais
        for slug, info in self.notes.items():
            if "error" in info:
                continue

            frontmatter = info["frontmatter"]
            is_deprecated = frontmatter.get("deprecated", False)

            # 1. Notas Órfãs (grafo conceitual)
            # Uma nota de literatura ou permanente é órfã se não receber nenhum link conceitual
            # (links vindos apenas de permanent/ ou literature/).
            conceptual_incoming = [
                src for src in incoming_links.get(slug, []) if src in self.notes and src != slug
            ]
            if not conceptual_incoming and slug not in {"index", "overview"}:
                msg = (
                    f"Nota órfã detectada: nenhuma outra nota do "
                    f"grafo conceitual aponta para [[{slug}]]."
                )
                result.warnings.append(
                    LintWarning(
                        type="orphan_note",
                        file_path=info["relative_path"],
                        message=msg,
                    )
                )

            # 2. Ligação Mínima ao Grafo (Notas permanentes ativas com < 2 links de saída no corpo)
            if info["type"] == "permanent" and not is_deprecated:
                # Extrai apenas wikilinks detectados no corpo (excluindo frontmatter)
                body_links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", info["body"])
                body_links_unique = {link.strip() for link in body_links}
                if len(body_links_unique) < 2:
                    result.warnings.append(
                        LintWarning(
                            type="minimal_connection",
                            file_path=info["relative_path"],
                            message=(
                                f"Ligação mínima: a nota permanente [[{slug}]] ativa "
                                "possui menos de dois links de saída no corpo "
                                f"({len(body_links_unique)} detectado)."
                            ),
                            details={"outgoing_count": len(body_links_unique)},
                        )
                    )

            # 3. Notas Deprecadas ativas no Grafo
            if is_deprecated:
                # Verifica se alguma nota permanente ou de literatura ativa aponta para ela
                active_referrers = []
                for referrer in conceptual_incoming:
                    ref_info = self.notes.get(referrer)
                    if ref_info and not ref_info["frontmatter"].get("deprecated", False):
                        active_referrers.append(referrer)

                if active_referrers:
                    superseded = frontmatter.get("superseded_by", None)
                    message = (
                        f"Nota deprecada [[{slug}]] ainda é referenciada por notas ativas: "
                        f"{', '.join([f'[[{r}]]' for r in active_referrers])}."
                    )
                    if not superseded:
                        message += (
                            " Nenhuma nota substituta (superseded_by) foi informada no frontmatter."
                        )

                    result.warnings.append(
                        LintWarning(
                            type="deprecated_reference",
                            file_path=info["relative_path"],
                            message=message,
                            details={
                                "active_referrers": active_referrers,
                                "superseded_by": superseded,
                            },
                        )
                    )

        # 4. Padrões Emergentes (termos destacados em 3+ notas que não possuem nota própria)
        for term, occurrences in bold_terms_occurrences.items():
            unique_occurrences = list(set(occurrences))
            if len(unique_occurrences) >= 3:
                term_slug = slugify(term)
                # Verifica se existe nota com o mesmo slug
                exists = term_slug in self.existing_files
                # Verifica também se algum arquivo tem título igual ao termo
                if not exists:
                    for info in self.notes.values():
                        title = info.get("frontmatter", {}).get("title", "")
                        if title.lower().strip() == term.lower().strip():
                            exists = True
                            break

                if not exists:
                    result.emergent_patterns.append(term)

        # Ordenar os resultados para estabilidade de relatórios
        result.errors.sort(key=lambda x: (x.file_path, x.message))
        result.warnings.sort(key=lambda x: (x.file_path, x.message))
        result.emergent_patterns.sort()

        return result


def print_text_report(result: LintResult) -> None:
    """Imprime um relatório legível no console em formato texto.

    Args:
        result: Estrutura consolidada de resultados.
    """
    print("=" * 60)
    print("RELATÓRIO DE SAÚDE E INTEGRIDADE DO ZETTELBRAIN")
    print("=" * 60)
    print(f"Total de notas catalogadas: {result.total_notes}")
    print(f"  - Notas de Literatura: {result.literature_count}")
    print(f"  - Notas Permanentes:   {result.permanent_count}")
    print(f"  - Outros arquivos:     {result.other_count}")
    print("-" * 60)

    if result.errors:
        print(f"\n[ERROS CRÍTICOS] Encontrados {len(result.errors)} erros:")
        for err in result.errors:
            print(f"  - [{err.type.upper()}] em {err.file_path}:")
            print(f"    {err.message}")
    else:
        print("\n[OK] Nenhum erro crítico de integridade estrutural encontrado.")

    if result.warnings:
        print(f"\n[AVISOS DE MELHORIA] Encontrados {len(result.warnings)} avisos:")
        for warn in result.warnings:
            print(f"  - [{warn.type.upper()}] em {warn.file_path}:")
            print(f"    {warn.message}")
    else:
        print("\n[OK] Nenhum aviso de melhoria pendente.")

    if result.emergent_patterns:
        print(
            "\n[PADRÕES EMERGENTES] Candidatos a Nota Permanente (presente em 3+ notas distintas):"
        )
        for pattern in result.emergent_patterns:
            print(f"  - **{pattern}**")
    else:
        print("\n[OK] Nenhum padrão emergente identificado.")

    print("=" * 60)


@log_skill_execution
def run_lint_logic() -> dict[str, Any]:
    """Executa a lógica de linting coletando dados do cofre configurado.

    Returns:
        dict[str, Any]: Representação em dicionário contendo os dados do lint.
    """
    settings = load_settings()
    linter = ZettelLinter(settings.zettelkasten_path)
    linter.scan_vault()
    result = linter.run()

    return {
        "total_notes": result.total_notes,
        "literature_count": result.literature_count,
        "permanent_count": result.permanent_count,
        "other_count": result.other_count,
        "errors": [asdict(e) for e in result.errors],
        "warnings": [asdict(w) for w in result.warnings],
        "emergent_patterns": result.emergent_patterns,
    }


def main() -> None:
    """Função de entrada da interface de linha de comando CLI.

    Executa o linting, formata a saída conforme argumentos e define o código de
    retorno do sistema operacional apropriado (não-zero em caso de erros críticos).
    """
    parser = argparse.ArgumentParser(description="Linter de integridade estática do ZettelBrain.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Retorna o resultado em formato JSON compacto.",
    )
    args = parser.parse_args()

    try:
        settings = load_settings()
        linter = ZettelLinter(settings.zettelkasten_path)
        linter.scan_vault()
        result = linter.run()

        if args.json:
            output = {
                "total_notes": result.total_notes,
                "literature_count": result.literature_count,
                "permanent_count": result.permanent_count,
                "other_count": result.other_count,
                "errors": [asdict(e) for e in result.errors],
                "warnings": [asdict(w) for w in result.warnings],
                "emergent_patterns": result.emergent_patterns,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print_text_report(result)

        # Se houver erros críticos (como links mortos ou erros de parsing), retorna status 1
        if result.errors:
            sys.exit(1)
        sys.exit(0)

    except Exception as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"[ERRO CRÍTICO] Falha na execução do linter: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
