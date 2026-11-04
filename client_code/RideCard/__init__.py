from ._anvil_designer import RideCardTemplate
from anvil import *


class RideCard(RideCardTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
