from ._anvil_designer import LeafletMapTemplate
from anvil.js.window import L


class LeafletMap(LeafletMapTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
    self.map_node = self.dom_nodes["map"]
