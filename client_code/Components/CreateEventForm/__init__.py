from ._anvil_designer import CreateEventFormTemplate
from anvil import *


class CreateEventForm(CreateEventFormTemplate):
  def __init__(self, **properties):
    email_prompt = properties.pop("email_prompt", "")
    super().__init__(**properties)
    self.email_prompt_label.text = email_prompt
    self.email_prompt_label.visible = bool(email_prompt)
    self.email_label.visible = bool(email_prompt)
    self.email_input.visible = bool(email_prompt)
