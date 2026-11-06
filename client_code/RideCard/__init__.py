from ._anvil_designer import RideCardTemplate
from anvil import *
import anvil.server
import anvil.users
from .. import RideAuth
from ..Components.BookingForm import BookingForm
from ..Components.EditContactForm import EditContactForm


class RideCard(RideCardTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)

    tratta = self.item
    self._ride_id = tratta.get_id()
    self._booking_info = None
    self._driver_phone = ""
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
      tratta["luogo_appuntamento"] or "Punto indicato sulla mappa"
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
      passeggeri = []
      contatti = []
      prenotato = False
      is_driver = False
    else:
      info_chat = anvil.server.call("get_chat_info_tratta", tratta)
      passeggeri = info_chat["passeggeri"]
      contatti = info_chat["contatti"]
      prenotato = info_chat["prenotato"]
      self._booking_info = info_chat.get("prenotazione")
      telefono_conducente = info_chat.get("telefono_conducente") or ""
      self._driver_phone = "+" + telefono_conducente if telefono_conducente else ""
    self.passengers_heading.visible = bool(passeggeri)
    self.passengers_panel.items = passeggeri
    self.chat_contacts_panel.items = contatti
    self.booking_button.visible = (
      tratta["stato"] == "Attiva" and posti_liberi > 0 and not is_driver and not prenotato
    )
    self.edit_booking_button.visible = self._booking_info is not None
    self.edit_ride_button.visible = is_driver

  @handle("booking_button", "click")
  def booking_button_click(self, **event_args):
    user = anvil.users.get_user()
    email_prompt = ""
    if user is None:
      email_prompt = (
        "Inserisci la tua email per ricevere un link di accesso. "
        "La prenotazione verrà completata al rientro."
      )
    form = BookingForm(email_prompt=email_prompt)
    conferma = alert(
      form,
      title="Prenota un posto",
      buttons=[("Prenota", True), ("Annulla", False)],
    )
    if conferma is not True:
      return

    nome = (form.passenger_name or "").strip()
    if not nome:
      alert("Inserisci il tuo nome.", title="Nome richiesto")
      return

    telefono = (form.phone or "").strip()
    if not telefono:
      alert("Inserisci il tuo numero WhatsApp.", title="Numero richiesto")
      return

    if user is None:
      email = (form.email or "").strip().lower()
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

  @handle("edit_booking_button", "click")
  def edit_booking_button_click(self, **event_args):
    booking = self._booking_info
    if booking is None:
      return
    form = EditContactForm(
      contact_name_label="Il tuo nome",
      contact_name=booking.get("nome", ""),
      phone="+" + booking["telefono"] if booking.get("telefono") else "",
    )
    conferma = alert(
      form,
      title="Modifica i dati della prenotazione",
      buttons=[("Salva", True), ("Annulla", False)],
    )
    if conferma is not True:
      return

    nome = (form.contact_name or "").strip()
    telefono = (form.phone or "").strip()
    if not nome or not telefono:
      alert("Inserisci il nome e il numero WhatsApp.", title="Dati mancanti")
      return

    risultato = anvil.server.call(
      "modifica_prenotazione",
      booking["id"],
      nome,
      telefono,
    )
    if not risultato.get("ok"):
      alert(risultato.get("message", "Non è stato possibile aggiornare i dati."))
      return
    alert("Dati della prenotazione aggiornati.", title="Modifica salvata")
    self.parent.raise_event("x-refresh-rides")

  @handle("edit_ride_button", "click")
  def edit_ride_button_click(self, **event_args):
    form = EditContactForm(
      contact_name_label="Nome del conducente",
      contact_name=self.item["nome_conducente"] or "",
      phone=self._driver_phone,
    )
    conferma = alert(
      form,
      title="Modifica nome e contatti dell'auto",
      buttons=[("Salva", True), ("Annulla", False)],
    )
    if conferma is not True:
      return

    nome = (form.contact_name or "").strip()
    telefono = (form.phone or "").strip()
    if not nome or not telefono:
      alert("Inserisci il nome e il numero WhatsApp.", title="Dati mancanti")
      return

    risultato = anvil.server.call(
      "modifica_contatti_tratta",
      self._ride_id,
      nome,
      telefono,
    )
    if not risultato.get("ok"):
      alert(risultato.get("message", "Non è stato possibile aggiornare i dati."))
      return
    alert("Nome e contatti dell'auto aggiornati.", title="Modifica salvata")
    self.parent.raise_event("x-refresh-rides")
