from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users
from .. import RideAuth
from ..Components.CreateRideForm import CreateRideForm
from ..Components.EmailLoginForm import EmailLoginForm
from ..Components.PendingBookingForm import PendingBookingForm


class Form1(Form1Template):
  ZONE_NAMES = [
    "Cenisia",
    "San Donato",
    "Moncalieri",
    "Collegno",
    "Chivasso",
    "Centro",
    "San Salvario",
    "Vanchiglia",
    "Mirafiori",
  ]
  ZONE_COORDINATES = {
    "Cenisia": (45.0739, 7.6523),
    "San Donato": (45.0837, 7.6669),
    "Moncalieri": (44.9995, 7.6820),
    "Collegno": (45.0780, 7.5770),
    "Chivasso": (45.1900, 7.8890),
    "Centro": (45.0703, 7.6869),
    "San Salvario": (45.0530, 7.6820),
    "Vanchiglia": (45.0750, 7.6980),
    "Mirafiori": (45.0190, 7.6350),
  }
  TORINO_CENTER = (45.0703, 7.6869)

  def __init__(self, **properties):
    super().__init__(**properties)

    self.jolly_button.tooltip = (
      "Ti registri come riserva: riceverai un'email quando le auto attive per "
      "zona e tratta avranno esaurito i posti, così potrai attivare la tua."
    )
    self.torino_map.center = GoogleMap.LatLng(45.0703, 7.6869)
    self.torino_map.zoom = 12
    self._map_markers = []

    self.zone_dropdown.items = [
      "Tutte le zone",
      "Cenisia",
      "San Donato",
      "Moncalieri",
      "Collegno",
      "Chivasso",
      "Centro",
      "San Salvario",
      "Vanchiglia",
      "Mirafiori",
    ]
    self.zone_dropdown.selected_value = "Tutte le zone"
    self.rides_panel.items = []
    self._refresh_login_controls()
    self.add_event_handler("show", self.form_show)
    self.add_event_handler("x-refresh-rides", self.refresh_rides_event)

  def form_show(self, **event_args):
    self._refresh_login_controls()
    self._refresh_board()
    self._resume_pending_action()

  def _selected_trip_type(self):
    return "ritorno" if self.return_radio.selected else "andata"

  def _selected_zone(self):
    selected = self.zone_dropdown.selected_value
    return None if selected == "Tutte le zone" else selected

  def _refresh_board(self):
    tratte = list(
      anvil.server.call(
        "get_tratte_disponibili",
        self._selected_trip_type(),
        self._selected_zone(),
      )
    )
    self.rides_panel.items = tratte
    self.empty_state.visible = not tratte
    self._refresh_map_markers(tratte)

  def _refresh_map_markers(self, tratte):
    for marker in self._map_markers:
      marker.remove_from_parent()
    self._map_markers = []

    auto_per_zona = {}
    for tratta in tratte:
      zona = tratta["zona_partenza"]
      auto_per_zona[zona] = auto_per_zona.get(zona, 0) + 1

    for zona, numero_auto in auto_per_zona.items():
      lat, lng = self.ZONE_COORDINATES.get(zona, self.TORINO_CENTER)
      marker = GoogleMap.Marker(
        position=GoogleMap.LatLng(lat, lng),
        title="{} · {} auto".format(zona, numero_auto),
        label=str(numero_auto),
      )
      self.torino_map.add_component(marker)
      self._map_markers.append(marker)

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
    for button in (self.offer_button, self.seek_button, self.jolly_button):
      button.role = (
        "ride-role-button-selected" if button is selected_button else "ride-role-button"
      )

  @handle("offer_button", "click")
  def offer_button_click(self, **event_args):
    self._select_role(self.offer_button)
    self._open_create_ride_dialog(is_jolly=False)

  @handle("seek_button", "click")
  def seek_button_click(self, **event_args):
    self._select_role(self.seek_button)

  @handle("jolly_button", "click")
  def jolly_button_click(self, **event_args):
    self._select_role(self.jolly_button)
    self._open_create_ride_dialog(is_jolly=True)

  def _open_create_ride_dialog(self, is_jolly):
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
      zone_names="|".join(self.ZONE_NAMES),
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

    zona = form.zone
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
      not zona
      or not data_tratta
      or not orario
      or not luogo_appuntamento
      or not tipo_tratta
      or not telefono
    ):
      alert(
        "Compila tutti i campi e indica almeno un posto.",
        title="Dati non validi",
      )
      return

    if user is None:
      email = (form.email or "").strip().lower()
      if "@" not in email:
        alert("Inserisci un indirizzo email valido.", title="Email richiesta")
        return
      action = {
        "kind": "offer",
        "zone": zona,
        "date": data_tratta,
        "time": orario,
        "meeting_place": luogo_appuntamento,
        "seats": posti,
        "trip_type": tipo_tratta,
        "is_jolly": is_jolly,
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
      "zone": zona,
      "date": data_tratta,
      "time": orario,
      "meeting_place": luogo_appuntamento,
      "seats": posti,
      "trip_type": tipo_tratta,
      "is_jolly": is_jolly,
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
      action["zone"],
      action["date"],
      action["time"],
      action["meeting_place"],
      action["seats"],
      action["trip_type"],
      action["is_jolly"],
      nome_conducente,
      action["phone"],
    )
    if isinstance(risultato, dict) and not risultato.get("ok", True):
      alert(risultato.get("message", "Non è stato possibile pubblicare la tratta."))
      return False

    if pending:
      RideAuth.clear_pending_action()

    messaggio = (
      "Auto salvata come Driver Jolly."
      if action["is_jolly"]
      else "Tratta pubblicata nella bacheca."
    )
    alert(messaggio, title="Operazione completata")
    self._refresh_board()
    return True

  @handle("outbound_radio", "change")
  def outbound_radio_change(self, **event_args):
    self._refresh_board()

  @handle("return_radio", "change")
  def return_radio_change(self, **event_args):
    self._refresh_board()

  @handle("zone_dropdown", "change")
  def zone_dropdown_change(self, **event_args):
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
