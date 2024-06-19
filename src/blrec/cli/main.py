import os
import sys
from copy import deepcopy
from typing import Optional

import typer
import uvicorn
from loguru import logger
from uvicorn.config import LOGGING_CONFIG

from .. import __prog__, __version__
from ..logging import TqdmOutputStream

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
        None, '--config', '-c', help='path of settings.toml file'
    ),
    out_dir: Optional[str] = typer.Option(
        None,
        '--out-dir',
        '-o',
        help='path of directory to store record files (overwrite setting)',
    ),
    log_dir: Optional[str] = typer.Option(
        None,
        '--log-dir',
        help='path of directory to store log files (overwrite setting)',
    ),
    progress: bool = typer.Option(True, help='display progress'),
    host: str = typer.Option('localhost', help='webapp host bind'),
    port: int = typer.Option(2233, help='webapp port bind'),
    open: bool = typer.Option(False, help='open webapp in default browser'),
    ipv4: bool = typer.Option(False, help='use IPv4 only'),
    root_path: str = typer.Option('', help='ASGI root path'),
    key_file: Optional[str] = typer.Option(None, help='SSL key file'),
    cert_file: Optional[str] = typer.Option(None, help='SSL certificate file'),
    api_key: Optional[str] = typer.Option(None, help='web api key'),
) -> None:
    """Bilibili live streaming recorder"""
    if config is not None:
        os.environ['BLREC_CONFIG'] = config
    if api_key is not None:
        os.environ['BLREC_API_KEY'] = api_key
    if out_dir is not None:
        os.environ['BLREC_OUT_DIR'] = out_dir
    if log_dir is not None:
        os.environ['BLREC_LOG_DIR'] = log_dir
    if ipv4 is not None:
        os.environ['BLREC_IPV4'] = '1'

    if not sys.stderr.isatty():
        progress = False
    if progress:
        os.environ['BLREC_PROGRESS'] = '1'
    else:
        os.environ['BLREC_PROGRESS'] = ''

    if root_path:
        if not root_path.startswith('/'):
            root_path = '/' + root_path
        if not root_path.endswith('/'):
            root_path += '/'

    if open:
        typer.launch(f'http://localhost:{port}')

    if not progress:
        logging_config = LOGGING_CONFIG
    else:
        logging_config = deepcopy(LOGGING_CONFIG)
        logging_config['handlers']['default']['stream'] = TqdmOutputStream()

    uvicorn.run(
        'blrec.web:app',
        host=host,
        port=port,
        root_path=root_path,
        proxy_headers=True,
        forwarded_allow_ips='*',
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
