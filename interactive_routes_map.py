import streamlit as st
import pandas as pd
import folium
from folium import plugins
import requests
import time
from streamlit_folium import st_folium

@st.cache_data
def load_data():
    return pd.read_csv('unique_routes_avg_price.csv')

@st.cache_data
def geocode_city(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{city_name}, Russia",
            'format': 'json',
            'limit': 1,
            'countrycodes': 'RU'
        }
        headers = {'User-Agent': 'RouteMapper/1.0'}
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
        time.sleep(0.1)
        return None, None
    except:
        return None, None

@st.cache_data
def geocode_all_cities(df):
    cities = set(df['from_city'].tolist() + df['to_city'].tolist())
    coordinates = {}
    
    progress_bar = st.progress(0)
    total_cities = len(cities)
    
    for i, city in enumerate(cities):
        lat, lon = geocode_city(city)
        if lat and lon:
            coordinates[city] = (lat, lon)
        progress_bar.progress((i + 1) / total_cities)
    
    progress_bar.empty()
    return coordinates

def create_map(filtered_df, coordinates):
    m = folium.Map(
        location=[55.7558, 37.6176],
        zoom_start=5,
        tiles='OpenStreetMap'
    )
    
    added_cities = set()
    
    for _, row in filtered_df.iterrows():
        from_coords = coordinates.get(row['from_city'])
        to_coords = coordinates.get(row['to_city'])
        
        if from_coords and to_coords:
            tooltip_text = f"""
            <b>Маршрут:</b> {row['route']}<br>
            <b>Цена:</b> {row['avg_price']} руб.<br>
            <b>Откуда:</b> {row['from_city']}<br>
            <b>Куда:</b> {row['to_city']}
            """
            
            folium.PolyLine(
                locations=[from_coords, to_coords],
                weight=2,
                color='blue',
                opacity=0.8,
                tooltip=tooltip_text
            ).add_to(m)
            
            if row['from_city'] not in added_cities:
                folium.CircleMarker(
                    location=from_coords,
                    radius=4,
                    tooltip=f"<b>{row['from_city']}</b>",
                    color='green',
                    fillColor='lightgreen',
                    fillOpacity=0.8
                ).add_to(m)
                added_cities.add(row['from_city'])
            
            if row['to_city'] not in added_cities:
                folium.CircleMarker(
                    location=to_coords,
                    radius=4,
                    tooltip=f"<b>{row['to_city']}</b>",
                    color='red',
                    fillColor='lightcoral',
                    fillOpacity=0.8
                ).add_to(m)
                added_cities.add(row['to_city'])
    
    return m

def main():
    st.set_page_config(page_title="Карта маршрутов России", layout="wide")
    st.title("Интерактивная карта маршрутов России")
    
    try:
        df = load_data()
    except FileNotFoundError:
        st.error("Файл unique_routes_avg_price.csv не найден")
        return
    
    st.sidebar.header("Фильтры")
    
    min_price = int(df['avg_price'].min())
    max_price = int(df['avg_price'].max())
    price_range = st.sidebar.slider(
        "Диапазон цен (руб.)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price)
    )
    
    cities = sorted(set(df['from_city'].tolist() + df['to_city'].tolist()))
    
    selected_from_cities = st.sidebar.multiselect(
        "Города отправления",
        options=cities,
        default=[]
    )
    
    selected_to_cities = st.sidebar.multiselect(
        "Города назначения",
        options=cities,
        default=[]
    )
    
    filtered_df = df[
        (df['avg_price'] >= price_range[0]) & 
        (df['avg_price'] <= price_range[1])
    ].copy()
    
    if selected_from_cities:
        filtered_df = filtered_df[filtered_df['from_city'].isin(selected_from_cities)]
    
    if selected_to_cities:
        filtered_df = filtered_df[filtered_df['to_city'].isin(selected_to_cities)]
    
    st.write(f"Найдено маршрутов: {len(filtered_df)}")
    
    if len(filtered_df) > 0:
        if 'map_built' not in st.session_state:
            st.session_state.map_built = False
            
        if st.button("Построить карту") or st.session_state.map_built:
            if not st.session_state.map_built:
                with st.spinner("Геокодирование городов..."):
                    coordinates = geocode_all_cities(filtered_df)
                st.session_state.coordinates = coordinates
                st.session_state.map_built = True
            
            with st.spinner("Создание карты..."):
                map_obj = create_map(filtered_df, st.session_state.coordinates)
                st_folium(map_obj, width=1200, height=600, key="route_map")
                
        if st.button("Сбросить карту"):
            st.session_state.map_built = False
            if 'coordinates' in st.session_state:
                del st.session_state.coordinates
            st.rerun()
    else:
        st.warning("Нет маршрутов, соответствующих выбранным фильтрам")

if __name__ == "__main__":
    main()