from ._anvil_designer import Form1Template
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users


class Form1(Form1Template):
  def __init__(self, **properties):
    super().__init__(**properties)

    self.torino_map.center = GoogleMap.LatLng(45.0703, 7.6869)
    self.torino_map.zoom = 12

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

  @handle("seek_button", "click")
  def seek_button_click(self, **event_args):
    self._select_role(self.seek_button)

  @handle("jolly_button", "click")
  def jolly_button_click(self, **event_args):
    self._select_role(self.jolly_button)

  @handle("login_button", "click")
  def login_button_click(self, **event_args):
    if anvil.users.get_user() is None:
      anvil.users.login_with_form()
    else:
      anvil.users.logout()
    self._refresh_login_controls()
