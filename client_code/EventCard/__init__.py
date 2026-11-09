from ._anvil_designer import EventCardTemplate
from anvil import *
import anvil.server
from ..Components.EventDetailForm import EventDetailForm
from ..Components.CreateEventForm import CreateEventForm


class EventCard(EventCardTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    self.edit_event_button.visible = self.item["can_edit"]
    self._show_event(self.item["evento"])

  def _show_event(self, event):
    self.name_label.text = event["nome"] or ""
    self.description_label.text = event["descrizione"] or ""
    self.description_label.visible = bool(event["descrizione"])
    data_evento = event["data_evento"]
    self.date_label.text = (
      data_evento.strftime("%d/%m/%Y") if data_evento is not None else "Data da definire"
    )
    self.outbound_label.text = "Andata: {}".format(
      event["orario_andata"] or "non indicata"
    )
    self.return_label.text = "Ritorno: {}".format(
      event["orario_ritorno"] or "non indicato"
    )

  @handle("open_button", "click")
  def open_button_click(self, **event_args):
    form = EventDetailForm()
    form.set_event(self.item["evento"])
    alert(
      form,
      title=self.item["evento"]["nome"],
      buttons=[("Chiudi", False)],
      large=True,
    )

  @handle("edit_event_button", "click")
  def edit_event_button_click(self, **event_args):
    event = self.item["evento"]
    form = CreateEventForm(event=event)
    while True:
      conferma = alert(
        form,
        title="Modifica evento",
        buttons=[("Salva modifiche", True), ("Annulla", False)],
        large=True,
      )
      if conferma is not True:
        return
      values = form.get_event_values()
      if values is None:
        continue
      updated_event = anvil.server.call(
        "modifica_evento",
        event.get_id(),
        values["name"],
        values["description"],
        values["date"],
        values["outbound_time"],
        values["return_time"],
        values["event_location"],
        values["event_lat"],
        values["event_lng"],
      )
      if isinstance(updated_event, dict) and not updated_event.get("ok", True):
        alert(updated_event.get("message", "Non è stato possibile modificare l'evento."))
        return
      self.item["evento"] = updated_event
      self._show_event(updated_event)
      alert("Evento aggiornato.", title="Operazione completata")
      return
