import os
import logging
from copy import deepcopy
from typing import Optional

import uvicorn
from uvicorn.config import LOGGING_CONFIG
import typer

from .. import __prog__, __version__
from ..logging import TqdmOutputStream
from ..setting import DEFAULT_SETTINGS_PATH


logger = logging.getLogger(__name__)

cli = typer.Typer()


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f'Bilibili live streaming recorder {__version__}')
        raise typer.Exit()


@cli.command()
def cli_main(
    version: Optional[bool] = typer.Option(
        None,
        '--version',
        callback=version_callback,
        is_eager=True,
        help=f"show {__prog__}'s version and exit",
    ),
    config: str = typer.Option(
        '~/.blrec/settings.toml',
        '--config',
        '-c',
        help='path of setting file',
    ),
    out_dir: Optional[str] = typer.Option(
        None,
        '--out-dir',
        '-o',
        help='path of directory to save files (overwrite setting)'
    ),
    host: str = typer.Option('127.0.0.1', help='webapp host bind'),
    port: int = typer.Option(2233, help='webapp port bind'),
    open: bool = typer.Option(False, help='open webapp in default browser'),
    key_file: Optional[str] = typer.Option(None, help='SSL key file'),
    cert_file: Optional[str] = typer.Option(None, help='SSL certificate file'),
    api_key: Optional[str] = typer.Option(None, help='web api key'),
) -> None:
    """Bilibili live streaming recorder"""
    if config != DEFAULT_SETTINGS_PATH:
        os.environ['config'] = config
    if api_key is not None:
        os.environ['api_key'] = api_key
    if out_dir is not None:
        os.environ['out_dir'] = out_dir

    if open:
        typer.launch(f'http://{host}:{port}')

    logging_config = deepcopy(LOGGING_CONFIG)
    logging_config['handlers']['default']['stream'] = TqdmOutputStream
    logging_config['handlers']['access']['stream'] = TqdmOutputStream

    uvicorn.run(
        'blrec.web:app',
        host=host,
        port=port,
        ssl_keyfile=key_file,
        ssl_certfile=cert_file,
        log_config=logging_config,
        log_level='info',
        access_log=False,
    )


def main() -> int:
    try:
        cli()
    except KeyboardInterrupt:
        return 1
    except SystemExit:
        return 1
    except BaseException as e:
        logger.exception(e)
        return 2
    else:
        return 0
    finally:
        logger.info('Exit')


if __name__ == '__main__':
    main()
