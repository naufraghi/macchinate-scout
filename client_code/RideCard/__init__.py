from ._anvil_designer import RideCardTemplate
from anvil import *
import anvil.server
import anvil.users


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
    info_chat = anvil.server.call("get_chat_info_tratta", tratta)
    self.chat_contacts_panel.items = info_chat["contatti"]
    self.booking_button.visible = (
      posti_liberi > 0 and not is_driver and not info_chat["prenotato"]
    )

  @handle("booking_button", "click")
  def booking_button_click(self, **event_args):
    if anvil.users.get_user() is None:
      anvil.users.login_with_form()
      if anvil.users.get_user() is None:
        return

    phone_input = TextBox(placeholder="es. +39 333 1234567")
    content = ColumnPanel()
    content.add_component(Label(text="Telefono WhatsApp per la prenotazione"))
    content.add_component(phone_input)
    conferma = alert(
      content,
      title="Prenota un posto",
      buttons=[("Prenota", True), ("Annulla", False)],
    )
    if conferma is not True:
      return

    telefono = (phone_input.text or "").strip()
    if not telefono:
      alert("Inserisci il tuo numero WhatsApp.", title="Numero richiesto")
      return

    risultato = anvil.server.call("prenota_posto", self.item, telefono)
    if not risultato.get("ok"):
      alert(risultato.get("message", "Non è stato possibile prenotare il posto."))
      return

    alert("Prenotazione confermata.", title="Posto prenotato")
    self.parent.raise_event("x-refresh-rides")
