import click
import json
import six

from .verifier import verify


@click.group()
def cli():
    pass


@click.command(name='verify')
@click.argument(u'input_file', type=click.File('rb'), required=False)
@click.argument(u'output_file', type=click.File('wb'), required=False)
@click.option(u'--data', type=str, default=None,
              help=u'Open Badges URL, JSON, or JWS-signed string input to verify')
@click.option(u'--recipient', type=str, prompt=False,
              help=u'Open Badges Profile JSON trusted to describe to the recipient')
def verify_badge_input(input_file, output_file, data, recipient):
    """
    This command takes Open Badges input in several formats and returns validation results.

    Positional Arguments:

    \b
      Input filename:    File must exist.
    \b
      Output filename:   If file exists, it will be overwritten.
    """
    if recipient is not None:
        try:
            recipient = json.loads(recipient)
        except Exception:
            raise click.Abort("Could not interpret profile input (expected JSON).")

    if data is not None and not isinstance(data, six.string_types):
        raise click.Abort("Expected data to be input as a string")

    results = verify(data, recipient_profile=recipient)
    is_valid = "Badge input is valid." if results['report'].get('valid') else "Badge input is not valid."

    click.echo(json.dumps(results, indent=4), file=output_file)
    click.echo(is_valid)


cli.add_command(verify_badge_input)


if __name__ == '__main__':
    cli()
