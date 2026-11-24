#!/usr/bin/env python3
"""A pytest futtatasa a "nincs mit futtatni" eset kivételevel.

**Miért kell:** a `pytest` exit kódjai:
- 0 = siker
- 1 = **teszthiba** (a CI-ban BUKJON)
- 2 = megszakitas
- 3 = belső hiba (a pytest-asyncio INTERNALERROR, a coverage config-hiba)
- 4 = CLI hiba (a nem letezo utvonal: "file or directory not found")
- 5 = **nem gyujtott teszt** (a repoban meg nincs alkalmazaskod)

A korábbi `|| echo "..."` maszkolta a 3-as (belső hiba) esetet is ->
**a CI "zold" volt, mikozben a tesztek egyaltalan nem futottak.**
Ez a wrapper **csak a "nincs mit futtatni" esetet nyeli el**, a
többi hibakod atmegy.

**A sorrend:**
1. a nem letezo utvonalak kiszuresenek (a 4-es exit elkerulese);
2. ha nem maradt egy utvonal -> a lepes kihagyva (exit 0);
3. a pytest futtatasa -> **csak az 5-ot nyeljuk el**, a tobbi atmegy.

Hasznalat (a justfile-ban):
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/unit
"""

import pathlib
import subprocess
import sys

# a pytest exit kodok
EXIT_NO_TESTS_COLLECTED = 5

# az opciok, amelyek egy erteket fogyasztanak (a kovetkezo argumentum
# nem egy utvonal)
_VALUE_FLAGS = {
    "-k",
    "-m",
    "-p",
    "--cov",
    "--cov-report",
    "--cov-fail-under",
    "--rootdir",
    "-c",
}


def _split_args(args: list[str]) -> tuple[list[str], list[str]]:
    """A flag-ek es az utvonalak szetvalasztasa.

    Visszaadja: (a flag-ek a veluk egyutt argv-et, a letezo utvonalak).
    A nem letezo utvonalak a masodik elem listajabol hannak el.
    """
    flags: list[str] = []
    paths: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _VALUE_FLAGS:
            flags.append(arg)
            if i + 1 < len(args):
                flags.append(args[i + 1])
                i += 2
                continue
            i += 1
            continue
        if arg.startswith("-"):
            flags.append(arg)
            i += 1
            continue
        # egy utvonal
        if pathlib.Path(arg).exists():
            paths.append(arg)
        else:
            print(f"a pytest utvonal nem letezik, kihagyva: {arg}")
        i += 1
    return flags, paths


def _default_paths() -> list[str]:
    """A pytest `testpaths` beallitasa a pyproject.toml-bol.

    A `-k reversible` (a 07 §8.1 8. lepese) utvonal nelkul jonne ->
    a wrapper a teljes teszt-konyvtarat hasznalja -> **a szures
    a `-k` flagre kerul**.
    """
    pyproject = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject.exists():
        return []
    import tomllib

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:
        return []
    testpaths = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths", [])
    return [str(p) for p in testpaths if pathlib.Path(p).exists()]


def main() -> int:
    flags, paths = _split_args(sys.argv[1:])
    if not paths:
        # a `-k reversible` (a 07 §8.1 8. lepese) utvonal nelkul jonne ->
        # a pytest `testpaths` beallitasat hasznaljuk
        paths = _default_paths()
        if paths:
            print(f"a pytest utvonal nem volt megadva -> a testpaths hasznalata: {paths}")
        else:
            print("nincs futtathato tesztutvonal -> a lepes kihagyva")
            return 0

    proc = subprocess.run([sys.executable, "-m", "pytest", *flags, *paths])
    if proc.returncode == EXIT_NO_TESTS_COLLECTED:
        print(
            "a pytest nem gyujtott tesztet (exit 5) -> a lepes kihagyva "
            "(az alkalmazaskod meg nincs a repoban)"
        )
        return 0
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
