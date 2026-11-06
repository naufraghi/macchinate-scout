from datetime import date

from ._anvil_designer import CreateRideFormTemplate
from anvil import *
import anvil.js
from ..LeafletMap import L


class CreateRideForm(CreateRideFormTemplate):
  TORINO_CENTER = (45.0703, 7.6869)

  def __init__(self, **properties):
    self._driver_name = ""
    self._date_iso = ""
    self._time = ""
    self._meeting_place = ""
    self._seats = ""
    self._trip_type = "andata"
    self._phone = ""
    self._email = ""
    self._email_prompt = ""
    self._map_picker = None
    self._components_initialized = False
    super().__init__(**properties)
    self._components_initialized = True
    self.trip_type_input.items = ["andata", "ritorno"]
    self._apply_values()
    self._set_seat_limits()
    self.add_event_handler("show", self._ensure_picker_map)

  def _apply_values(self):
    self.driver_name_input.text = self._driver_name
    self.date_input.date = self._parse_date(self._date_iso)
    self.time_input.text = self._time
    self.meeting_place_input.text = self._meeting_place
    self.seats_input.text = self._seats
    self.trip_type_input.selected_value = self._trip_type or "andata"
    self.phone_input.text = self._phone
    self.email_input.text = self._email
    self.email_prompt_label.text = self._email_prompt
    self.email_prompt_label.visible = bool(self._email_prompt)
    self.email_label.visible = bool(self._email_prompt)
    self.email_input.visible = bool(self._email_prompt)

  def _ensure_picker_map(self, **event_args):
    if self._map_picker is None:
      self._map_picker = L.map(self.departure_map.map_node).setView(
        list(self.TORINO_CENTER), 13
      )
      L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          "maxZoom": 19,
          "detectRetina": True,
          "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          "referrerPolicy": "strict-origin-when-cross-origin",
        },
      ).addTo(self._map_picker)
    else:
      self._map_picker.invalidateSize()

  def get_departure_coordinates(self):
    if self._map_picker is None:
      return None
    center = self._map_picker.getCenter()
    return float(center.lat), float(center.lng)

  def _parse_date(self, value):
    if not value:
      return None
    year, month, day = [int(part) for part in value.split("-")]
    return date(year, month, day)

  def _set_seat_limits(self):
    seats_input_element = anvil.js.get_dom_node(self.seats_input)
    if seats_input_element.tagName != "INPUT":
      seats_input_element = seats_input_element.querySelector("input")
      if seats_input_element is None:
        raise RuntimeError("Impossibile trovare l'input numerico dei posti.")
    seats_input_element.setAttribute("min", "1")
    seats_input_element.setAttribute("max", "8")
    seats_input_element.setAttribute("step", "1")

  @property
  def driver_name(self):
    return self.driver_name_input.text or ""

  @driver_name.setter
  def driver_name(self, value):
    self._driver_name = "" if value is None else str(value)
    if self._components_initialized:
      self.driver_name_input.text = self._driver_name

  @property
  def date_iso(self):
    selected_date = self.date_input.date
    return selected_date.isoformat() if selected_date else ""

  @date_iso.setter
  def date_iso(self, value):
    self._date_iso = "" if value is None else str(value)
    if self._components_initialized:
      self.date_input.date = self._parse_date(self._date_iso)

  @property
  def time(self):
    return self.time_input.text or ""

  @time.setter
  def time(self, value):
    self._time = "" if value is None else str(value)
    if self._components_initialized:
      self.time_input.text = self._time

  @property
  def meeting_place(self):
    return self.meeting_place_input.text or ""

  @meeting_place.setter
  def meeting_place(self, value):
    self._meeting_place = "" if value is None else str(value)
    if self._components_initialized:
      self.meeting_place_input.text = self._meeting_place

  @property
  def seats(self):
    return self.seats_input.text or ""

  @seats.setter
  def seats(self, value):
    self._seats = "" if value is None else str(value)
    if self._components_initialized:
      self.seats_input.text = self._seats

  @property
  def trip_type(self):
    return self.trip_type_input.selected_value or ""

  @trip_type.setter
  def trip_type(self, value):
    self._trip_type = "andata" if value is None else str(value)
    if self._components_initialized:
      self.trip_type_input.selected_value = self._trip_type

  @property
  def phone(self):
    return self.phone_input.text or ""

  @phone.setter
  def phone(self, value):
    self._phone = "" if value is None else str(value)
    if self._components_initialized:
      self.phone_input.text = self._phone

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
