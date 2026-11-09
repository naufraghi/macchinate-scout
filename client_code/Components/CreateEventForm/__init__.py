from ._anvil_designer import CreateEventFormTemplate
from anvil import *
from ..LeafletMap import L


class CreateEventForm(CreateEventFormTemplate):
  TORINO_CENTER = (45.0703, 7.6869)

  def __init__(self, **properties):
    email_prompt = properties.pop("email_prompt", "")
    event = properties.pop("event", None)
    super().__init__(**properties)
    self._location_map = None
    self._initial_coordinates = self.TORINO_CENTER
    self.email_prompt_label.text = email_prompt
    self.email_prompt_label.visible = bool(email_prompt)
    self.email_label.visible = bool(email_prompt)
    self.email_input.visible = bool(email_prompt)
    if event is not None:
      self.set_event(event)
    self.add_event_handler("show", self._ensure_location_map)

  def set_event(self, event):
    self.name_input.text = event["nome"] or ""
    self.description_input.text = event["descrizione"] or ""
    self.date_input.date = event["data_evento"]
    self.outbound_time_input.text = event["orario_andata"] or ""
    self.return_time_input.text = event["orario_ritorno"] or ""
    self.event_location_input.text = event["luogo_evento"] or ""

    lat_evento = event["lat_evento"]
    lng_evento = event["lng_evento"]
    if lat_evento is not None and lng_evento is not None:
      self._initial_coordinates = (float(lat_evento), float(lng_evento))
    if self._location_map is not None:
      self._location_map.setView(list(self._initial_coordinates), 12)

  def _ensure_location_map(self, **event_args):
    if self._location_map is None:
      self._location_map = L.map(self.event_location_map.map_node).setView(
        list(self._initial_coordinates), 12
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

  def get_event_values(self):
    nome = (self.name_input.text or "").strip()
    descrizione = (self.description_input.text or "").strip()
    selected_date = self.date_input.date
    orario_andata = (self.outbound_time_input.text or "").strip()
    orario_ritorno = (self.return_time_input.text or "").strip()
    if not nome or not descrizione or selected_date is None:
      alert("Inserisci nome, descrizione e data dell'evento.", title="Dati mancanti")
      return None
    if not orario_andata or not orario_ritorno:
      alert("Inserisci gli orari standard di andata e ritorno.", title="Dati mancanti")
      return None
    luogo_evento = (self.event_location_input.text or "").strip()
    if not luogo_evento:
      alert("Inserisci il luogo dell'evento.", title="Luogo richiesto")
      return None
    coordinate_evento = self.get_location_coordinates()
    if coordinate_evento is None:
      alert(
        "Attendi il caricamento della mappa e scegli la posizione dell'evento.",
        title="Posizione richiesta",
      )
      return None
    lat_evento, lng_evento = coordinate_evento
    return {
      "name": nome,
      "description": descrizione,
      "date": selected_date.isoformat(),
      "outbound_time": orario_andata,
      "return_time": orario_ritorno,
      "event_location": luogo_evento,
      "event_lat": lat_evento,
      "event_lng": lng_evento,
    }
