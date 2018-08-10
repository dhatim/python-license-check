from liccheck.command_line import parse_args, read_strategy, run, Level


def test_parse_arguments():
    args = parse_args(['--sfile', 'my_strategy.ini'])
    assert args.strategy_ini_file == 'my_strategy.ini'
    assert args.requirement_txt_file == './requirements.txt'
    assert args.level is Level.STANDARD
    args = parse_args(['--sfile', 'my_strategy.ini', '--rfile', 'my_requirements.txt', '--level', 'cautious'])
    assert args.strategy_ini_file == 'my_strategy.ini'
    assert args.requirement_txt_file == 'my_requirements.txt'
    assert args.level is Level.CAUTIOUS


def test_read_strategy():
    args = parse_args(['--sfile', 'license_strategy.ini'])
    strategy = read_strategy(args.strategy_ini_file)
    assert len(strategy.AUTHORIZED_LICENSES) > 0
    assert len(strategy.AUTHORIZED_PACKAGES) > 0
    assert len(strategy.UNAUTHORIZED_LICENSES) > 0


def test_run():
    args = parse_args(['--sfile', 'license_strategy.ini', '--rfile', 'requirements.txt'])
    run(args)
