from ._anvil_designer import EventDetailFormTemplate
from anvil import *
import anvil.server
import anvil.users
from ... import RideAuth
from ..CreateRideForm import CreateRideForm
from ..LeafletMap import L


class EventDetailForm(EventDetailFormTemplate):
  TORINO_CENTER = (45.0703, 7.6869)

  def __init__(self, **properties):
    super().__init__(**properties)
    self._event = None
    self._map = None
    self._map_markers = []
    self._map_view_initialized = False
    self.rides_panel.items = []
    self.empty_state.visible = False
    self.add_event_handler("show", self.form_show)
    self.add_event_handler("x-refresh-rides", self.refresh_rides_event)

  def set_event(self, event):
    self._event = event
    self.name_label.text = event["nome"]
    self.description_label.text = event["descrizione"] or ""
    self.description_label.visible = bool(event["descrizione"])
    data_evento = event["data_evento"]
    self.date_label.text = (
      data_evento.strftime("%d/%m/%Y") if data_evento is not None else "Data da definire"
    )
    self.outbound_default_label.text = "Andata standard: {}".format(
      event["orario_andata"] or "non indicata"
    )
    self.return_default_label.text = "Ritorno standard: {}".format(
      event["orario_ritorno"] or "non indicato"
    )
    luogo_evento = event["luogo_evento"] or ""
    self.event_location_label.text = "Luogo dell'evento: {}".format(luogo_evento)
    self.event_location_label.visible = bool(luogo_evento)

  def form_show(self, **event_args):
    self._ensure_map()
    self._refresh_rides()

  def _ensure_map(self):
    if self._map is None:
      self._map = L.map(self.event_map.map_node).setView(
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
      ).addTo(self._map)
    else:
      self._map.invalidateSize()

  def _refresh_rides(self):
    if self._event is None:
      return
    tratte = list(anvil.server.call("get_tratte_evento", self._event.get_id()))
    self.rides_panel.items = tratte
    self.empty_state.visible = not tratte
    self._refresh_map_markers(tratte)

  def _refresh_map_markers(self, tratte):
    evento = self._event
    if self._map is None or evento is None:
      return
    for marker in self._map_markers:
      marker.remove()
    self._map_markers = []
    coordinate_mappa = []
    lat_evento = evento["lat_evento"]
    lng_evento = evento["lng_evento"]
    if lat_evento is not None and lng_evento is not None:
      coordinate_evento = [lat_evento, lng_evento]
      coordinate_mappa.append(coordinate_evento)
      marker_evento = L.marker(coordinate_evento)
      marker_evento.addTo(self._map)
      marker_evento.bindTooltip(
        "Evento: {}".format(evento["luogo_evento"] or evento["nome"]),
        {"direction": "top", "className": "ride-map-marker-label"},
      )
      self._map_markers.append(marker_evento)
    for tratta in tratte:
      lat = tratta["lat_partenza"]
      lng = tratta["lng_partenza"]
      if lat is None or lng is None:
        continue
      coordinate = [lat, lng]
      coordinate_mappa.append(coordinate)
      marker = L.circleMarker(
        coordinate,
        {
          "radius": 11,
          "color": "#2e7d32",
          "fillColor": "#2e7d32",
          "fillOpacity": 0.9,
          "weight": 2,
        },
      )
      marker.addTo(self._map)
      marker.bindTooltip(
        tratta["luogo_appuntamento"] or "Punto di partenza",
        {"direction": "top", "className": "ride-map-marker-label"},
      )
      self._map_markers.append(marker)
    if not self._map_view_initialized and coordinate_mappa:
      if len(coordinate_mappa) == 1:
        self._map.setView(coordinate_mappa[0], 13)
      else:
        self._map.fitBounds(
          coordinate_mappa,
          {"padding": [24, 24], "maxZoom": 13},
        )
      self._map_view_initialized = True

  def _open_offer(self, extra, tipo_tratta=None):
    evento = self._event
    if evento is None:
      return
    user = anvil.users.get_user()
    display_name = ""
    if user is not None and user["email"]:
      display_name = user["email"].split("@")[0]
    email_prompt = ""
    if user is None:
      email_prompt = (
        "Inserisci la tua email: riceverai un link per accedere. "
        "Al rientro completeremo la pubblicazione."
      )
    form = CreateRideForm(
      driver_name=display_name,
      email_prompt=email_prompt,
      is_extra="true" if extra else "false",
    )
    if tipo_tratta is not None:
      form.trip_type = tipo_tratta
      form.time = evento["orario_" + tipo_tratta] or ""
    while True:
      conferma = alert(
        form,
        title="Aggiungi tratta extra" if extra else "Offri {}".format(tipo_tratta),
        buttons=[("Pubblica", True), ("Annulla", False)],
        large=True,
      )
      if conferma is not True:
        return
      if self._submit_offer(form, user, extra):
        return

  def _submit_offer(self, form, user, extra):
    evento = self._event
    if evento is None:
      return False
    coordinate_partenza = form.get_departure_coordinates()
    nome_conducente = (form.driver_name or "").strip()
    orario = (form.time or "").strip()
    luogo_appuntamento = (form.meeting_place or "").strip()
    note = (form.note or "").strip()
    tipo_tratta = form.trip_type
    telefono = (form.phone or "").strip()
    try:
      posti = int(form.seats)
    except (TypeError, ValueError):
      alert("Inserisci un numero intero di posti.", title="Dati non validi")
      return False
    if not 1 <= posti <= 8:
      alert("Il numero di posti deve essere compreso tra 1 e 8.", title="Dati non validi")
      return False
    if not orario or not tipo_tratta or not telefono:
      alert("Compila orario e telefono e indica almeno un posto.", title="Dati non validi")
      return False
    if coordinate_partenza is None:
      alert(
        "Attendi il caricamento della mappa e seleziona il punto d'incontro.",
        title="Punto richiesto",
      )
      return False

    lat_partenza, lng_partenza = coordinate_partenza
    action = {
      "kind": "offer",
      "event_id": evento.get_id(),
      "time": orario,
      "meeting_place": luogo_appuntamento,
      "note": note,
      "lat_partenza": lat_partenza,
      "lng_partenza": lng_partenza,
      "seats": posti,
      "trip_type": tipo_tratta,
      "extra": bool(extra),
      "driver_name": nome_conducente,
      "phone": telefono,
    }
    if user is None:
      email = (form.email or "").strip().lower()
      if "@" not in email:
        alert("Inserisci un indirizzo email valido.", title="Email richiesta")
        return False
      result = RideAuth.request_email_access(email, action)
      if not result.get("ok"):
        alert(result.get("message", "Non è stato possibile inviare l'email."))
        return False
      alert(
        "Controlla la posta: al rientro completeremo la pubblicazione nell'evento.",
        title="Controlla la posta",
      )
      return True

    return self._publish_ride(action)

  def _publish_ride(self, action):
    nome_conducente = (action.get("driver_name") or "").strip()
    if not nome_conducente:
      user = anvil.users.get_user()
      if user is not None and user["email"]:
        nome_conducente = user["email"].split("@")[0]
    if not nome_conducente:
      alert("Inserisci il nome del conducente.", title="Nome richiesto")
      return False
    risultato = anvil.server.call(
      "crea_tratta",
      action["event_id"],
      action["time"],
      action["meeting_place"],
      action["lat_partenza"],
      action["lng_partenza"],
      action["seats"],
      action["trip_type"],
      action["extra"],
      nome_conducente,
      action["phone"],
      action.get("note", ""),
    )
    if isinstance(risultato, dict) and not risultato.get("ok", True):
      alert(risultato.get("message", "Non è stato possibile pubblicare la tratta."))
      return False
    alert("Tratta pubblicata nell'evento.", title="Operazione completata")
    self._refresh_rides()
    return True

  @handle("outbound_button", "click")
  def outbound_button_click(self, **event_args):
    self._open_offer(False, "andata")

  @handle("return_button", "click")
  def return_button_click(self, **event_args):
    self._open_offer(False, "ritorno")

  @handle("extra_button", "click")
  def extra_button_click(self, **event_args):
    self._open_offer(True)

  def refresh_rides_event(self, **event_args):
    self._refresh_rides()
