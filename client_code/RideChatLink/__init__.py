from ._anvil_designer import RideChatLinkTemplate
from anvil import *


class RideChatLink(RideChatLinkTemplate):
  def __init__(self, **properties):
    super().__init__(**properties)
