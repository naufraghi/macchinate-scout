from ._anvil_designer import BookingFormTemplate


class BookingForm(BookingFormTemplate):
  def __init__(self, **properties):
    self._name = ""
    self._phone = ""
    self._note = ""
    self._email = ""
    self._email_prompt = ""
    self._components_initialized = False
    super().__init__(**properties)
    self._components_initialized = True
    self._apply_values()

  def _apply_values(self):
    self.name_input.text = self._name
    self.phone_input.text = self._phone
    self.note_input.text = self._note
    self.email_input.text = self._email
    self.email_prompt_label.text = self._email_prompt
    self.email_prompt_label.visible = bool(self._email_prompt)
    self.email_label.visible = bool(self._email_prompt)
    self.email_input.visible = bool(self._email_prompt)

  @property
  def passenger_name(self):
    return self.name_input.text or ""

  @passenger_name.setter
  def passenger_name(self, value):
    self._name = "" if value is None else str(value)
    if self._components_initialized:
      self.name_input.text = self._name

  @property
  def phone(self):
    return self.phone_input.text or ""

  @phone.setter
  def phone(self, value):
    self._phone = "" if value is None else str(value)
    if self._components_initialized:
      self.phone_input.text = self._phone

  @property
  def note(self):
    return self.note_input.text or ""

  @note.setter
  def note(self, value):
    self._note = "" if value is None else str(value)
    if self._components_initialized:
      self.note_input.text = self._note

  @property
  def email(self):
    return self.email_input.text or ""

  @email.setter
  def email(self, value):
    self._email = "" if value is None else str(value)
    if self._components_initialized:
      self.email_input.text = self._email

  @property
  def email_prompt(self):
    return self._email_prompt

  @email_prompt.setter
  def email_prompt(self, value):
    self._email_prompt = "" if value is None else str(value)
    if self._components_initialized:
      self.email_prompt_label.text = self._email_prompt
      self.email_prompt_label.visible = bool(self._email_prompt)
      self.email_label.visible = bool(self._email_prompt)
      self.email_input.visible = bool(self._email_prompt)
