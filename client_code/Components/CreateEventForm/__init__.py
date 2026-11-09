from ._anvil_designer import CreateEventFormTemplate
from anvil import *
from ..LeafletMap import L


class CreateEventForm(CreateEventFormTemplate):
  TORINO_CENTER = (45.0703, 7.6869)

  def __init__(self, **properties):
    email_prompt = properties.pop("email_prompt", "")
    super().__init__(**properties)
    self._location_map = None
    self.email_prompt_label.text = email_prompt
    self.email_prompt_label.visible = bool(email_prompt)
    self.email_label.visible = bool(email_prompt)
    self.email_input.visible = bool(email_prompt)
    self.add_event_handler("show", self._ensure_location_map)

  def _ensure_location_map(self, **event_args):
    if self._location_map is None:
      self._location_map = L.map(self.event_location_map.map_node).setView(
        list(self.TORINO_CENTER), 12
      )
      L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          "maxZoom": 19,
          "detectRetina": True,
          "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          "referrerPolicy": "strict-origin-when-cross-origin",
        },
      ).addTo(self._location_map)
    else:
      self._location_map.invalidateSize()

  def get_location_coordinates(self):
    if self._location_map is None:
      return None
    center = self._location_map.getCenter()
    return float(center.lat), float(center.lng)
