from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users
from .. import RideAuth
from ..Components.CreateEventForm import CreateEventForm
from ..Components.EmailLoginForm import EmailLoginForm
from ..Components.EventDetailForm import EventDetailForm
from ..Components.PendingBookingForm import PendingBookingForm


class Form1(Form1Template):
  def __init__(self, **properties):
    super().__init__(**properties)
    self.events_panel.items = []
    self._refresh_login_controls()
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    self._refresh_login_controls()
    self._refresh_events()
    self._resume_pending_action()

  def _refresh_events(self):
    risultati = anvil.server.call("get_eventi")
    eventi = risultati["eventi"]
    modificabili = set(risultati["modificabili"])
    self.events_panel.items = [
      {"evento": evento, "can_edit": evento.get_id() in modificabili}
      for evento in eventi
    ]
    self.empty_state.visible = not eventi

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
    if kind == "create_event":
      if (
        not action.get("event_location")
        or action.get("event_lat") is None
        or action.get("event_lng") is None
      ):
        RideAuth.clear_pending_action()
        alert(
          "La bozza dell'evento non contiene il luogo. Ricrea l'evento scegliendo la posizione sulla mappa.",
          title="Bozza da aggiornare",
        )
        return
      self._publish_event(action, pending=True)
    elif kind == "offer":
      if not action.get("event_id"):
        RideAuth.clear_pending_action()
        alert(
          "La bozza precedente non è collegata a un evento. Apri o crea un evento e ripubblica la tratta.",
          title="Bozza da aggiornare",
        )
        return
      self._publish_ride(action, pending=True)
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
        action.get("note", ""),
      )
      if not result.get("ok"):
        alert(result.get("message", "Non è stato possibile prenotare il posto."))
        return
      RideAuth.clear_pending_action()
      alert("Prenotazione confermata.", title="Posto prenotato")
      self._refresh_events()
    else:
      RideAuth.clear_pending_action()

  def _open_event(self, event):
    form = EventDetailForm()
    form.set_event(event)
    alert(
      form,
      title=event["nome"],
      buttons=[("Chiudi", False)],
      large=True,
    )

  @handle("create_event_button", "click")
  def create_event_button_click(self, **event_args):
    user = anvil.users.get_user()
    email_prompt = ""
    if user is None:
      email_prompt = (
        "Inserisci la tua email: riceverai un link per accedere. "
        "Al rientro completeremo la creazione dell'evento."
      )
    form = CreateEventForm(email_prompt=email_prompt)
    while True:
      conferma = alert(
        form,
        title="Crea un evento",
        buttons=[("Crea evento", True), ("Annulla", False)],
        large=True,
      )
      if conferma is not True:
        return
      action = self._read_event_form(form)
      if action is None:
        continue
      if user is None:
        email = (form.email_input.text or "").strip().lower()
        if "@" not in email:
          alert("Inserisci un indirizzo email valido.", title="Email richiesta")
          continue
        action["kind"] = "create_event"
        result = RideAuth.request_email_access(email, action)
        if not result.get("ok"):
          alert(result.get("message", "Non è stato possibile inviare l'email."))
          continue
        alert(
          "Controlla la posta. Al rientro l'evento verrà creato.",
          title="Controlla la posta",
        )
        return
      if self._publish_event(action):
        return

  def _read_event_form(self, form):
    return form.get_event_values()

  def _publish_event(self, action, pending=False):
    evento = anvil.server.call(
      "crea_evento",
      action["name"],
      action["description"],
      action["date"],
      action["outbound_time"],
      action["return_time"],
      action.get("event_location"),
      action.get("event_lat"),
      action.get("event_lng"),
    )
    if isinstance(evento, dict) and not evento.get("ok", True):
      alert(evento.get("message", "Non è stato possibile creare l'evento."))
      return False
    if pending:
      RideAuth.clear_pending_action()
    self._refresh_events()
    alert("Evento creato.", title="Operazione completata")
    self._open_event(evento)
    return True

  def _publish_ride(self, action, pending=False):
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
    if pending:
      RideAuth.clear_pending_action()
    self._refresh_events()
    alert("Tratta pubblicata nell'evento.", title="Operazione completata")
    return True

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
    self._refresh_events()
