from ._anvil_designer import EventCardTemplate
from anvil import *
from ..Components.EventDetailForm import EventDetailForm


class EventCard(EventCardTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    data_evento = self.item["data_evento"]
    self.date_label.text = (
      data_evento.strftime("%d/%m/%Y") if data_evento is not None else "Data da definire"
    )
    self.outbound_label.text = "Andata: {}".format(
      self.item["orario_andata"] or "non indicata"
    )
    self.return_label.text = "Ritorno: {}".format(
      self.item["orario_ritorno"] or "non indicato"
    )

  @handle("open_button", "click")
  def open_button_click(self, **event_args):
    form = EventDetailForm()
    form.set_event(self.item)
    alert(
      form,
      title=self.item["nome"],
      buttons=[("Chiudi", False)],
      large=True,
    )
