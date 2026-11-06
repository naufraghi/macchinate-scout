from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users
from .. import RideAuth
from ..Components.CreateRideForm import CreateRideForm
from ..Components.EmailLoginForm import EmailLoginForm
from ..Components.LeafletMap import L
from ..Components.PendingBookingForm import PendingBookingForm


class Form1(Form1Template):
  TORINO_CENTER = (45.0703, 7.6869)

  def __init__(self, **properties):
    super().__init__(**properties)

    self._leaflet_map = None
    self._map_markers = []
    self._map_view_initialized = False

    self.rides_panel.items = []
    self._refresh_login_controls()
    self.add_event_handler("show", self.form_show)
    self.add_event_handler("x-refresh-rides", self.refresh_rides_event)

  def form_show(self, **event_args):
    self._ensure_map()
    self._refresh_login_controls()
    self._refresh_board()
    self._resume_pending_action()

  def _ensure_map(self):
    if self._leaflet_map is None:
      self._leaflet_map = L.map(self.torino_map.map_node).setView(
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
      ).addTo(self._leaflet_map)
    else:
      self._leaflet_map.invalidateSize()

  def _selected_trip_type(self):
    return "ritorno" if self.return_radio.selected else "andata"

  def _refresh_board(self):
    tipo_tratta = self._selected_trip_type()
    tratte = list(
      anvil.server.call(
        "get_tratte_disponibili",
        tipo_tratta,
      )
    )
    self.rides_panel.items = tratte
    self.empty_state.visible = not tratte
    self._refresh_map_markers(tratte)

  def _refresh_map_markers(self, tratte):
    for marker in self._map_markers:
      marker.remove()
    self._map_markers = []

    coordinate_partenze = []
    for tratta in tratte:
      lat = tratta["lat_partenza"]
      lng = tratta["lng_partenza"]
      if lat is None or lng is None:
        continue

      coordinate = [lat, lng]
      coordinate_partenze.append(coordinate)
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
      marker.addTo(self._leaflet_map)
      marker.bindTooltip(
        tratta["luogo_appuntamento"] or "Punto di partenza",
        {
          "direction": "top",
          "className": "ride-map-marker-label",
        },
      )
      self._map_markers.append(marker)

    if (
      not self._map_view_initialized
      and self._leaflet_map is not None
      and coordinate_partenze
    ):
      if len(coordinate_partenze) == 1:
        self._leaflet_map.setView(coordinate_partenze[0], 13)
      else:
        self._leaflet_map.fitBounds(
          coordinate_partenze,
          {"padding": [24, 24], "maxZoom": 13},
        )
      self._map_view_initialized = True

  def _refresh_login_controls(self):
    user = anvil.users.get_user()
    if user is None:
      self.user_label.visible = False
      self.login_button.text = "Accedi con email"
    else:
      self.user_label.text = user["email"]
      self.user_label.visible = True
      self.login_button.text = "Esci"

  def _resume_pending_action(self):
    user = anvil.users.get_user()
    if user is None:
      return

    action = RideAuth.load_pending_action()
    if action is None:
      return

    kind = action.get("kind")
    if kind == "offer":
      if (
        action.get("lat_partenza") is None
        or action.get("lng_partenza") is None
      ):
        RideAuth.clear_pending_action()
        alert(
          "La vecchia bozza non contiene il punto sulla mappa. Ripubblica la tratta.",
          title="Bozza da aggiornare",
        )
        return
      self._publish_ride(action, user, pending=True)
    elif kind == "booking":
      nome_passeggero = (action.get("name") or "").strip()
      if not nome_passeggero:
        form = PendingBookingForm()
        conferma = alert(
          form,
          title="Nome richiesto",
          buttons=[("Continua", True), ("Annulla", False)],
        )
        if conferma is not True:
          return
        nome_passeggero = (form.passenger_name or "").strip()
        if not nome_passeggero:
          alert("Inserisci il tuo nome.", title="Nome richiesto")
          return
        action["name"] = nome_passeggero
        RideAuth.save_pending_action(action)

      result = anvil.server.call(
        "prenota_posto_per_id",
        action.get("ride_id"),
        nome_passeggero,
        action.get("phone"),
      )
      if not result.get("ok"):
        alert(result.get("message", "Non è stato possibile prenotare il posto."))
        return
      RideAuth.clear_pending_action()
      alert("Prenotazione confermata.", title="Posto prenotato")
      self._refresh_board()
    else:
      RideAuth.clear_pending_action()

  def _select_role(self, selected_button):
    for button in (self.offer_button, self.seek_button):
      button.role = (
        "ride-role-button-selected" if button is selected_button else "ride-role-button"
      )

  @handle("offer_button", "click")
  def offer_button_click(self, **event_args):
    self._select_role(self.offer_button)
    self._open_create_ride_dialog()

  @handle("seek_button", "click")
  def seek_button_click(self, **event_args):
    self._select_role(self.seek_button)

  def _open_create_ride_dialog(self):
    user = anvil.users.get_user()
    display_name = ""
    if user is not None:
      email = user["email"]
      if email:
        display_name = email.split("@")[0]
    email_prompt = ""
    if user is None:
      email_prompt = (
        "Inserisci la tua email: riceverai un link per accedere o confermare "
        "il nuovo account. Al rientro il passaggio verrà pubblicato."
      )
    form = CreateRideForm(
      driver_name=display_name,
      email_prompt=email_prompt,
    )

    conferma = alert(
      form,
      title="Pubblica una tratta",
      buttons=[("Pubblica", True), ("Annulla", False)],
      large=True,
    )
    if conferma is not True:
      return

    coordinate_partenza = form.get_departure_coordinates()
    nome_conducente = (form.driver_name or "").strip()
    data_tratta = form.date_iso
    orario = (form.time or "").strip()
    luogo_appuntamento = (form.meeting_place or "").strip()
    tipo_tratta = form.trip_type
    telefono = (form.phone or "").strip()
    posti_input = form.seats
    try:
      posti = int(posti_input)
    except (TypeError, ValueError):
      alert("Inserisci un numero intero di posti.", title="Dati non validi")
      return
    if not 1 <= posti <= 8:
      alert("Il numero di posti deve essere compreso tra 1 e 8.", title="Dati non validi")
      return

    if (
      not data_tratta
      or not orario
      or not tipo_tratta
      or not telefono
    ):
      alert(
        "Compila tutti i campi e indica almeno un posto.",
        title="Dati non validi",
      )
      return

    if coordinate_partenza is None:
      alert(
        "Attendi il caricamento della mappa e seleziona il punto d'incontro.",
        title="Punto richiesto",
      )
      return

    lat_partenza, lng_partenza = coordinate_partenza
    if user is None:
      email = (form.email or "").strip().lower()
      if "@" not in email:
        alert("Inserisci un indirizzo email valido.", title="Email richiesta")
        return
      action = {
        "kind": "offer",
        "date": data_tratta,
        "time": orario,
        "meeting_place": luogo_appuntamento,
        "lat_partenza": lat_partenza,
        "lng_partenza": lng_partenza,
        "seats": posti,
        "trip_type": tipo_tratta,
        "driver_name": nome_conducente,
        "phone": telefono,
      }
      result = RideAuth.request_email_access(email, action)
      if not result.get("ok"):
        alert(result.get("message", "Non è stato possibile inviare l'email."))
        return
      alert(
        "Controlla la posta: troverai il link per accedere o confermare "
        "l'account. Al rientro completeremo la pubblicazione.",
        title="Controlla la posta",
      )
      return

    action = {
      "kind": "offer",
      "date": data_tratta,
      "time": orario,
      "meeting_place": luogo_appuntamento,
      "lat_partenza": lat_partenza,
      "lng_partenza": lng_partenza,
      "seats": posti,
      "trip_type": tipo_tratta,
      "driver_name": nome_conducente,
      "phone": telefono,
    }
    self._publish_ride(action, user)

  def _publish_ride(self, action, user, pending=False):
    nome_conducente = action.get("driver_name", "").strip()
    if not nome_conducente:
      email = user["email"]
      if email:
        nome_conducente = email.split("@")[0]
    if not nome_conducente:
      alert("Inserisci il nome del conducente.", title="Nome richiesto")
      return False

    risultato = anvil.server.call(
      "crea_tratta",
      action["date"],
      action["time"],
      action["meeting_place"],
      action["lat_partenza"],
      action["lng_partenza"],
      action["seats"],
      action["trip_type"],
      nome_conducente,
      action["phone"],
    )
    if isinstance(risultato, dict) and not risultato.get("ok", True):
      alert(risultato.get("message", "Non è stato possibile pubblicare la tratta."))
      return False

    if pending:
      RideAuth.clear_pending_action()

    alert("Tratta pubblicata nella bacheca.", title="Operazione completata")
    self._refresh_board()
    return True

  @handle("outbound_radio", "change")
  def outbound_radio_change(self, **event_args):
    self._refresh_board()

  @handle("return_radio", "change")
  def return_radio_change(self, **event_args):
    self._refresh_board()

  def refresh_rides_event(self, **event_args):
    self._refresh_board()

  @handle("login_button", "click")
  def login_button_click(self, **event_args):
    if anvil.users.get_user() is None:
      form = EmailLoginForm()
      conferma = alert(
        form,
        title="Accedi con email",
        buttons=[("Invia link", True), ("Annulla", False)],
      )
      if conferma is not True:
        return
      email = (form.email or "").strip().lower()
      if "@" not in email:
        alert("Inserisci un indirizzo email valido.", title="Email richiesta")
        return
      result = RideAuth.request_email_access(email)
      if not result.get("ok"):
        alert(result.get("message", "Non è stato possibile inviare l'email."))
        return
      alert("Controlla la posta per completare l'accesso.", title="Controlla la posta")
    else:
      anvil.users.logout()
    self._refresh_login_controls()
    self._refresh_board()
