#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import nox

nox.options.sessions = ['lint', 'test']

@nox.session
def lint(session):
    session.run('pip', 'install', 'poetry')
    session.run('pip', 'install', 'pycodestyle')
    session.run('pip', 'install', 'pydocstyle')

    session.run('poetry', 'build')
    session.run('poetry', 'install')
    session.run('poetry', 'shell')

    session.run('pycodestyle', '--max-line-length=100', '--ignore=E741,E743', 'mos6502')
    # session.run('pycodestyle', '--max-line-length=100', '--ignore=E741,E743', 'tests')
    session.run('pydocstyle', 'mos6502')

@nox.session
def test(session):
    session.run('poetry', 'install')
    session.run('poetry', 'shell')
    session.run('pytest')

@nox.session
def release(session: nox.Session) -> None:
    """
    Kicks off an automated release process by creating and pushing a new tag.

    Invokes bump2version with the posarg setting the version.

    Usage:
    $ nox -s release -- [major|minor|patch]
    """
    parser = argparse.ArgumentParser(description="Release a semver version.")
    parser.add_argument(
        "version",
        type=str,
        nargs=1,
        help="The type of semver release to make.",
        choices={"major", "minor", "patch"},
    )
    args: argparse.Namespace = parser.parse_args(args=session.posargs)
    version: str = args.version.pop()

    # If we get here, we should be good to go
    # Let's do a final check for safety
    confirm = input(
        f"You are about to bump the {version!r} version. Are you sure? [y/n]: "
    )

    # Abort on anything other than 'y'
    if confirm.lower().strip() != "y":
        session.error(f"You said no when prompted to bump the {version!r} version.")


    session.install("bump2version")

    session.log(f"Bumping the {version!r} version")
    session.run("bump2version", version)

    session.log("Pushing the new tag")
    session.run("git", "push", external=True)
    session.run("git", "push", "--tags", external=True)