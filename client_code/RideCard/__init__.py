from ._anvil_designer import RideCardTemplate
from anvil import *
import anvil.server
import anvil.users
from .. import RideAuth


class RideCard(RideCardTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)

    tratta = self.item
    conducente = tratta["conducente"]
    self.driver_label.text = (
      tratta["nome_conducente"]
      or (conducente["email"] if conducente is not None else "Conducente non specificato")
    )
    data_tratta = tratta["data_tratta"]
    self.date_label.text = (
      data_tratta.strftime("%d/%m/%Y") if data_tratta is not None else "Data non indicata"
    )
    self.meeting_place_label.text = (
      tratta["luogo_appuntamento"] or "Luogo non specificato"
    )
    posti_liberi = max(0, tratta["posti_totali"] - tratta["posti_occupati"])
    self.free_seats_label.text = str(posti_liberi)

    utente = anvil.users.get_user()
    is_driver = (
      utente is not None
      and conducente is not None
      and utente.get_id() == conducente.get_id()
    )
    if utente is None:
      contatti = []
      prenotato = False
    else:
      info_chat = anvil.server.call("get_chat_info_tratta", tratta)
      contatti = info_chat["contatti"]
      prenotato = info_chat["prenotato"]
    self.chat_contacts_panel.items = contatti
    self.booking_button.visible = (
      posti_liberi > 0 and not is_driver and not prenotato
    )

  @handle("booking_button", "click")
  def booking_button_click(self, **event_args):
    user = anvil.users.get_user()

    name_input = TextBox(placeholder="es. Maria Rossi")
    phone_input = TextBox(placeholder="es. +39 333 1234567")
    content = ColumnPanel()
    content.add_component(Label(text="Il tuo nome"))
    content.add_component(name_input)
    content.add_component(Label(text="Telefono WhatsApp per la prenotazione"))
    content.add_component(phone_input)
    email_input = TextBox(placeholder="nome@esempio.it")
    if user is None:
      content.add_component(
        Label(
          text=(
            "Inserisci la tua email per ricevere un link di accesso. "
            "La prenotazione verrà completata al rientro."
          )
        )
      )
      content.add_component(Label(text="Email"))
      content.add_component(email_input)
    conferma = alert(
      content,
      title="Prenota un posto",
      buttons=[("Prenota", True), ("Annulla", False)],
    )
    if conferma is not True:
      return

    nome = (name_input.text or "").strip()
    if not nome:
      alert("Inserisci il tuo nome.", title="Nome richiesto")
      return

    telefono = (phone_input.text or "").strip()
    if not telefono:
      alert("Inserisci il tuo numero WhatsApp.", title="Numero richiesto")
      return

    if user is None:
      email = (email_input.text or "").strip().lower()
      if "@" not in email:
        alert("Inserisci un indirizzo email valido.", title="Email richiesta")
        return
      action = {
        "kind": "booking",
        "ride_id": self.item.get_id(),
        "name": nome,
        "phone": telefono,
      }
      result = RideAuth.request_email_access(email, action)
      if not result.get("ok"):
        alert(result.get("message", "Non è stato possibile inviare l'email."))
        return
      alert(
        "Controlla la posta per accedere o confermare l'account. "
        "Al rientro completeremo la prenotazione.",
        title="Controlla la posta",
      )
      return

    risultato = anvil.server.call("prenota_posto", self.item, nome, telefono)
    if not risultato.get("ok"):
      alert(risultato.get("message", "Non è stato possibile prenotare il posto."))
      return

    alert("Prenotazione confermata.", title="Posto prenotato")
    self.parent.raise_event("x-refresh-rides")
