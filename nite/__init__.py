"""Main module."""
import click
from nite.core import NITECore


def show_version(ctx, value):
    """Print version information and exit."""
    if not value:
        return

    print('NITE (Nigh Impervious Task Executor) 0.0.1 by Kalman Olah')
    ctx.exit()


@click.command()
@click.option('--debug', '-d', is_flag=True, help='Show debug output.')
@click.option('--daemonize', is_flag=True, help='Daemonize the process.')
@click.option('--version', '-v', is_flag=True, help='Print version information and exit.',
              callback=show_version, expose_value=False, is_eager=True)
def nite(debug, daemonize):
    """Start NITE, the Nigh Impervious Task Executor."""
    NITECore(debug, daemonize)
