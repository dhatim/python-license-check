from liccheck.command_line import parse_args, read_strategy, run, Level
import pytest
import sys
import textwrap

def test_parse_arguments():
    args = parse_args(['--sfile', 'my_strategy.ini'])
    assert args.strategy_ini_file == 'my_strategy.ini'
    assert args.requirement_txt_file == './requirements.txt'
    assert args.level is Level.STANDARD
    assert args.no_deps is False
    args = parse_args(['--sfile', 'my_strategy.ini', '--rfile', 'my_requirements.txt', '--level', 'cautious'])
    assert args.strategy_ini_file == 'my_strategy.ini'
    assert args.requirement_txt_file == 'my_requirements.txt'
    assert args.level is Level.CAUTIOUS
    assert args.no_deps is False
    args = parse_args(['--sfile', 'my_strategy.ini', '--rfile', 'my_requirements.txt', '--level', 'cautious', '--no-deps'])
    assert args.strategy_ini_file == 'my_strategy.ini'
    assert args.requirement_txt_file == 'my_requirements.txt'
    assert args.level is Level.CAUTIOUS
    assert args.no_deps is True


def test_read_strategy():
    args = parse_args(['--sfile', 'license_strategy.ini'])
    strategy = read_strategy(args.strategy_ini_file)
    assert len(strategy.AUTHORIZED_LICENSES) > 0
    assert len(strategy.AUTHORIZED_PACKAGES) > 0
    assert len(strategy.UNAUTHORIZED_LICENSES) > 0


@pytest.mark.skipif(sys.version_info[0] < 3, reason='with py2 there are more dependencies')
def test_run(capsys):
    args = parse_args(['--sfile', 'license_strategy.ini', '--rfile', 'requirements.txt'])
    run(args)
    captured = capsys.readouterr().out
    expected = textwrap.dedent(
        '''\
        gathering licenses...
        3 packages and dependencies.
        check authorized packages...
        3 packages.
        '''
    )
    assert captured == expected


@pytest.mark.skipif(sys.version_info[0] < 3, reason='with py2 there are more dependencies')
def test_run_without_deps(capsys):
    args = parse_args(['--sfile', 'license_strategy.ini', '--rfile', 'requirements.txt', '--no-deps'])
    run(args)
    captured = capsys.readouterr().out
    expected = textwrap.dedent(
        '''\
        gathering licenses...
        3 packages.
        check authorized packages...
        3 packages.
        '''
    )
    assert captured == expected
