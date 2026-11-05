from ._anvil_designer import EmailLoginFormTemplate


class EmailLoginForm(EmailLoginFormTemplate):
  def __init__(self, **properties):
    self._email = ""
    self._components_initialized = False
    super().__init__(**properties)
    self._components_initialized = True
    self.email_input.text = self._email

  @property
  def email(self):
    return self.email_input.text or ""

  @email.setter
  def email(self, value):
    self._email = "" if value is None else str(value)
    if self._components_initialized:
      self.email_input.text = self._email
