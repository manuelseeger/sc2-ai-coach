import logging

from jinja2 import Environment, FileSystemLoader, Template
from typing_extensions import Dict

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.DEBUG)


class LoggingTemplate(Template):
    def render(self, *args, **kwargs):
        r = super().render(*args, **kwargs)
        # log.debug(f"Rendered template: {r}")
        return r


class LoggingEnvironment(Environment):
    template_class = LoggingTemplate


class Jinja2Loader:
    env: Environment
    scanner: Template
    tags: Template
    new_replay: Template
    summary: Template
    initial_instructions: Template
    additional_instructions: Template
    scanner_empty: Template

    def __init__(self):
        self.env = LoggingEnvironment(
            loader=FileSystemLoader(searchpath="./aicoach/prompts/")
        )
        self.scanner = self.env.get_template("scanner.jinja2")
        self.tags = self.env.get_template("tags.jinja2")
        self.new_replay = self.env.get_template("new_replay.jinja2")
        self.summary = self.env.get_template("summary.jinja2")
        self.initial_instructions = self.env.get_template("initial_instructions.jinja2")
        self.additional_instructions = self.env.get_template(
            "additional_instructions.jinja2"
        )
        self.scanner_empty = self.env.get_template("scanner_empty.jinja2")

    def render(self, template_name: str, replacements: Dict[str, str]) -> str:
        template = self.env.get_template(template_name)
        return template.render(replacements)


Templates = Jinja2Loader()
