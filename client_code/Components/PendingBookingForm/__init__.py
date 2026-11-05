from ._anvil_designer import PendingBookingFormTemplate


class PendingBookingForm(PendingBookingFormTemplate):
  def __init__(self, **properties):
    self._name = ""
    self._components_initialized = False
    super().__init__(**properties)
    self._components_initialized = True
    self.name_input.text = self._name

  @property
  def passenger_name(self):
    return self.name_input.text or ""

  @passenger_name.setter
  def passenger_name(self, value):
    self._name = "" if value is None else str(value)
    if self._components_initialized:
      self.name_input.text = self._name
