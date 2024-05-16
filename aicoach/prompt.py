from jinja2 import Environment, FileSystemLoader, Template
from typing_extensions import Dict


class Jinja2Loader:
    env: Environment
    scanner: Template
    tags: Template
    new_replay: Template
    summary: Template
    initial_instructions: Template

    def __init__(self):
        self.env = Environment(loader=FileSystemLoader(searchpath="./aicoach/prompts/"))
        self.scanner = self.env.get_template("scanner.jinja2")
        self.tags = self.env.get_template("tags.jinja2")
        self.new_replay = self.env.get_template("new_replay.jinja2")
        self.summary = self.env.get_template("summary.jinja2")
        self.initial_instructions = self.env.get_template("initial_instructions.jinja2")

    def render(self, template: str, replacements: Dict[str, str]) -> str:
        template = self.env.get_template(template)
        return template.render(replacements)


Templates = Jinja2Loader()
