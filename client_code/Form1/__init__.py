from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users


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
      self.login_button.text = "Accedi"
    else:
      self.user_label.text = user["email"]
      self.user_label.visible = True
      self.login_button.text = "Esci"

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
    zone_input = DropDown(items=self.ZONE_NAMES)
    zone_input.selected_value = self.ZONE_NAMES[0]
    name_input = TextBox()
    user = anvil.users.get_user()
    display_name = ""
    if user is not None:
      email = user["email"]
      if email:
        display_name = email.split("@")[0]
    name_input.text = display_name
    time_input = TextBox(placeholder="es. 09:30")
    seats_input = TextBox(placeholder="Numero di posti")
    trip_type_input = DropDown(items=["andata", "ritorno"])
    trip_type_input.selected_value = "andata"
    phone_input = TextBox(placeholder="es. +39 333 1234567")

    content = ColumnPanel()
    content.add_component(
      Label(text="Per pubblicare, ti chiederemo di accedere dopo aver premuto Pubblica.")
    )
    content.add_component(Label(text="Nome conducente"))
    content.add_component(name_input)
    content.add_component(Label(text="Zona di partenza"))
    content.add_component(zone_input)
    content.add_component(Label(text="Orario"))
    content.add_component(time_input)
    content.add_component(Label(text="Posti totali"))
    content.add_component(seats_input)
    content.add_component(Label(text="Tipo tratta"))
    content.add_component(trip_type_input)
    content.add_component(Label(text="Telefono WhatsApp del conducente"))
    content.add_component(phone_input)

    conferma = alert(
      content,
      title="Pubblica una tratta",
      buttons=[("Pubblica", True), ("Annulla", False)],
      large=True,
    )
    if conferma is not True:
      return

    zona = zone_input.selected_value
    nome_conducente = (name_input.text or "").strip()
    orario = (time_input.text or "").strip()
    tipo_tratta = trip_type_input.selected_value
    telefono = (phone_input.text or "").strip()
    try:
      posti = int((seats_input.text or "").strip())
    except (TypeError, ValueError):
      alert("Inserisci un numero intero di posti.", title="Dati non validi")
      return

    if (
      not zona
      or not orario
      or not tipo_tratta
      or not telefono
      or posti < 1
    ):
      alert(
        "Compila tutti i campi e indica almeno un posto.",
        title="Dati non validi",
      )
      return

    user = anvil.users.get_user()
    if user is None:
      anvil.users.login_with_form()
      self._refresh_login_controls()
      user = anvil.users.get_user()
      if user is None:
        return

    if not nome_conducente:
      email = user["email"]
      if email:
        nome_conducente = email.split("@")[0]
    if not nome_conducente:
      alert("Inserisci il nome del conducente.", title="Nome richiesto")
      return

    risultato = anvil.server.call(
      "crea_tratta",
      zona,
      orario,
      posti,
      tipo_tratta,
      is_jolly,
      nome_conducente,
      telefono,
    )
    if isinstance(risultato, dict) and not risultato.get("ok", True):
      alert(risultato.get("message", "Non è stato possibile pubblicare la tratta."))
      return

    messaggio = (
      "Auto salvata come Driver Jolly."
      if is_jolly
      else "Tratta pubblicata nella bacheca."
    )
    alert(messaggio, title="Operazione completata")
    self._refresh_board()

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
      anvil.users.login_with_form()
    else:
      anvil.users.logout()
    self._refresh_login_controls()
    self._refresh_board()
