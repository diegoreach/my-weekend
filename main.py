
from datetime import datetime
from datetime import timedelta
import pandas as pd
import streamlit as st
from multiprocessing import Pool
from sources.booking import BookingPage
# Paleta em https://coolors.co/palette/ffbe0b-fb5607-ff006e-8338ec-3a86ff


def all_fridays(start_date, max_date):
  fridays = list(pd.date_range(start_date, max_date, freq='W-FRI'))
  return fridays


def header(container):
  container.write(
    '<h1 style="color: #FB5607;">#MeuFimDeSemana</h1>', 
    unsafe_allow_html=True
  )
  container.write(
    """
      <span style="font-size:1.2rem;">
        Insira ao lado os links dos Resorts / Hotéis do Booking.com e o #MeuFimDeSemana
        encontrará o fim de semana mais barato para você.
      </span>""", 
    unsafe_allow_html=True
  )
  container.write('\n')
  container.write('\n')


def deploy_line_chart(hotel_names):
  chart_data = pd.DataFrame([])

  params = {
    "encoding": {"x": {"field": "Fim de semana", "type": "temporal", "timeunit": "date"}},
    "layer": [
      {
        "encoding": {
          "color": {"field": "Hotel", "type": "nominal"},
          'y': {'field': 'Reais', 'type': 'quantitative'},
        },
        "layer": [
          {
            "mark": {
              "type": "line",
              "interpolate": "monotone",
              "point": {
                "filled": False,
                "fill": "white"
              }
            }
          },
          {"transform": [{"filter": {"param": "hover", "empty": False}}], "mark": "point"}
        ]
      },
      {
        "transform": [{"pivot": "Hotel", "value": "Reais", "groupby": ["Fim de semana"]}],
        "mark": "rule",
        "encoding": {
          "opacity": {
            "condition": {"value": 0.3, "param": "hover", "empty": False},
            "value": 0
          },
          "tooltip": [
            {"field": "Fim de semana", "type": "temporal", "timeunit": "date"}
          ]
        },
        "params": [{
          "name": "hover",
          "select": {
            "type": "point",
            "fields": ["Fim de semana"],
            "nearest": True,
            "on": "mouseover",
            "clear": "mouseout"
          }
        }]
      }
    ]
  }
  for hotel_name in hotel_names:
    params["layer"][1]["encoding"]["tooltip"].append(
      {"field": hotel_name, "type": "quantitative"}
    )

  line_chart = chart_container.vega_lite_chart(chart_data, params, use_container_width=True)
  return line_chart


st.set_page_config(
  page_title='#MeuFimDeSemana', 
  page_icon='hotel'
)

header_container = st.container()
header(header_container)

chart_container = st.container()
main = st.container()

with st.sidebar:
  st.write('<h2 style="color:#FB5607; text-align:center; font-size: 1.4rem;">Seu fim de semana começa aqui</h2>', unsafe_allow_html=True)

  with st.form("my_form"):
    today = datetime.now()
    starting_day = st.date_input(
      "De", 
      today, 
      min_value=today
    )
    maximum_day = st.date_input(
      "Até", 
      value = today + timedelta(days=90), 
      min_value = today + timedelta(days=1)
    )
    hotels_urls = st.text_area(
      "Links do Booking.com",
      value="https://www.booking.com/hotel/br/fasano-boa-vista-porto-feliz.html\nhttps://www.booking.com/hotel/br/unique-garden-amp-spa.html",
      help = "One URL per line", 
      height = 190, 
      placeholder = "https://www.booking.com/hotel/...\nhttps://www.booking.com/hotel/..."
    )
    submitted = st.form_submit_button("Partiu!")

if submitted:
  hotel_url_list = [hotel_url.strip() for hotel_url in hotels_urls.splitlines()]
  columns=['Reais', 'Fim de semana', 'Hotel']
  line_chart = None
  loading_bar = chart_container.progress(0)
  cheapest_fares = {}
  expensive_fares = {}
  metric_cols = {}
  i = 0

  fridays = all_fridays(starting_day, maximum_day)
  for friday in fridays:
    checkin = friday.to_pydatetime().date()
    checkout = checkin + timedelta(days=2)
    checkin_tz = "%sT00:00:00" % str(checkin)

    pool = Pool(2)
    params = [(checkin, checkout, hotel_url) for hotel_url in hotel_url_list]
    hotels_bp = pool.starmap(BookingPage, params)

    if i == 0:
      line_chart = deploy_line_chart([hbp.hotel_name for hbp in hotels_bp])

    for bp in hotels_bp:
      if i == 0:
        main.write('<h3><a href="' + bp.hotel_url + '" target="_blank" style="color:#3A86FF;">' + bp.hotel_name + '</a></h3>', unsafe_allow_html=True)
        main.image(bp.image_url, width=600)

        metric_cols[bp.hotel_url] = main.columns(1)[0]
        metric_cols[bp.hotel_url] = metric_cols[bp.hotel_url].empty()
        cheapest_fares[bp.hotel_url] = None
        expensive_fares[bp.hotel_url] = None
        if bp.starting_price:
          cheapest_fares[bp.hotel_url] = bp.starting_price
          expensive_fares[bp.hotel_url] = bp.starting_price

          metric_cols[bp.hotel_url].metric("Fim de Semana Mais Barato", "R$ %i" % cheapest_fares[bp.hotel_url])
      else:
        if bp.starting_price:
          if cheapest_fares[bp.hotel_url] is None or bp.starting_price < cheapest_fares[bp.hotel_url]:
            cheapest_fares[bp.hotel_url] = bp.starting_price
          if expensive_fares[bp.hotel_url] is None or bp.starting_price > expensive_fares[bp.hotel_url]:
            expensive_fares[bp.hotel_url] = bp.starting_price

          delta = expensive_fares[bp.hotel_url] - cheapest_fares[bp.hotel_url]
          if delta:
            metric_cols[bp.hotel_url].metric(
              "Fim de Semana Mais Barato", "R$ %i" % cheapest_fares[bp.hotel_url], 
              "-R$ %i" % delta,
              delta_color="inverse"
            )
          else:
            metric_cols[bp.hotel_url].metric(
              "Mais barato", "R$ %i" % cheapest_fares[bp.hotel_url]
            )
            

      data = [(bp.starting_price, checkin_tz, bp.hotel_name)]
      df_incremental = pd.DataFrame(data, columns=columns)
      line_chart.add_rows(df_incremental)

    i += 1
    loading_bar.progress(i/len(fridays))

  loading_bar.empty()
  st.balloons()