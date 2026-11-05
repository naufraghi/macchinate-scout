from ._anvil_designer import EditContactFormTemplate


class EditContactForm(EditContactFormTemplate):
  def __init__(self, **properties):
    self._contact_name = ""
    self._contact_name_label = "Nome"
    self._phone = ""
    self._components_initialized = False
    super().__init__(**properties)
    self._components_initialized = True
    self._apply_values()

  def _apply_values(self):
    self.name_label.text = self._contact_name_label
    self.name_input.text = self._contact_name
    self.phone_input.text = self._phone

  @property
  def contact_name(self):
    return self.name_input.text or ""

  @contact_name.setter
  def contact_name(self, value):
    self._contact_name = "" if value is None else str(value)
    if self._components_initialized:
      self.name_input.text = self._contact_name

  @property
  def contact_name_label(self):
    return self._contact_name_label

  @contact_name_label.setter
  def contact_name_label(self, value):
    self._contact_name_label = "Nome" if value is None else str(value)
    if self._components_initialized:
      self.name_label.text = self._contact_name_label

  @property
  def phone(self):
    return self.phone_input.text or ""

  @phone.setter
  def phone(self, value):
    self._phone = "" if value is None else str(value)
    if self._components_initialized:
      self.phone_input.text = self._phone
