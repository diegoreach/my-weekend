import re
import requests


class BookingPage:
  BOOKING_PARAMS = "?checkin=%s&checkout=%s&group_adults=2&group_children=0&no_rooms=1&selected_currency=BRL&lang=en"
  HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
  }

  hotel_url = ""
  html = None
  starting_price = ""
  hotel_name = ""
  image_url = ""

  def __init__(self, checkin, checkout, hotel_url):
    self.hotel_url = hotel_url

    search_params = self.BOOKING_PARAMS % (checkin, checkout)
    r = requests.get(
      hotel_url + search_params, 
      headers = self.HEADERS
    )
    self.html = r.text

    if self.html:
      self._get_starting_price()
      self._get_hotel_name()
      self._get_image_url()

  def _get_starting_price(self):
    try:
      prices = re.findall('Prices start at R\$.?([\d\,]+)\.', self.html, re.MULTILINE + re.DOTALL)
      price = int(prices[0].replace(',', ''))
    except:
      price = 0
    self.starting_price = price

  def _get_hotel_name(self):
    try:
      names = re.findall('"name" : "(.+?)"', self.html, re.MULTILINE + re.DOTALL)
      name = names[0]
    except:
      name = ""
    self.hotel_name = name

  def _get_image_url(self):
    try:
      images = re.findall('name="twitter\:image" content="(.+?)"', self.html, re.MULTILINE + re.DOTALL)
      image_url = images[0]
    except:
      image_url = ""
    self.image_url = image_url